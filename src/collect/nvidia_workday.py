"""NVIDIA via its public Workday careers board (full board, incremental details).

How (updated 2026-11-09; see docs/sprints/sprint-01-data-sources-legal.md)
    1. Listing: the board's own JSON listing endpoint, i.e. the request the public careers page makes
       in every visitor's browser (`/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs`). It has a
       2,000-results-per-query cap, so it is queried once per job-family facet, each below the cap.
       That gives the **full open stock** (title, location, posted bucket, requisition id, family).
    2. Details: each job page's JSON-LD `JobPosting` (full description, exact date posted), fetched
       **only for requisitions not seen before**; known ones are carried forward from the merged dataset.

Conditions: robots.txt is checked for every URL (the listing path is not disallowed), ≤1 request / 2.5 s,
no application flow, no nvidia.com pages; stop if the board starts linking the nvidia.com Terms.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .common import PoliteSession, Robots, assert_allowed, html_to_text, scrub_contacts

SOURCE = "nvidia_workday_board"
BASE = "https://nvidia.wd5.myworkdayjobs.com"
SITE = "NVIDIAExternalCareerSite"
LIST_URL = f"{BASE}/wday/cxs/nvidia/{SITE}/jobs"
PAGE = 20
ROOT = Path(__file__).resolve().parents[2]
MERGED = ROOT / "data" / "processed" / "nvidia.csv"

_LDJSON = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
csv.field_size_limit(2**31 - 1)


def _list(session: PoliteSession, robots: Robots, facets: dict,
          max_pages: int | None = None) -> tuple[int, list, dict]:
    """Page through the listing for one facet filter. Returns (total, postings, first response)."""
    assert_allowed(robots, LIST_URL)
    out, offset, total, first = [], 0, None, {}
    while total is None or offset < total:
        body = {"appliedFacets": facets, "limit": PAGE, "offset": offset, "searchText": ""}
        d = session.post(LIST_URL, json=body, headers={"Accept": "application/json"}).json()
        if total is None:
            total, first = d.get("total", 0), d
        out += d.get("jobPostings", [])
        offset += PAGE
        if max_pages and offset >= max_pages * PAGE:
            break
    return total, out, first


def _known_rows() -> dict[str, dict]:
    if not MERGED.exists():
        return {}
    with MERGED.open(encoding="utf-8") as f:
        return {r["job_id"]: r for r in csv.DictReader(f) if r.get("job_description")}


def fetch(session: PoliteSession, limit: int | None = None) -> dict:
    robots = Robots.fetch(session, f"{BASE}/robots.txt")
    total, _, first = _list(session, robots, {}, max_pages=1)
    families = [v for f in first.get("facets", []) if f.get("facetParameter") == "jobFamilyGroup"
                for v in f.get("values", [])]
    listing: dict[str, dict] = {}
    for fam in families[: (1 if limit else None)]:
        _, posts, _ = _list(session, robots, {"jobFamilyGroup": [fam["id"]]}, max_pages=1 if limit else None)
        for p in posts:
            if not p.get("externalPath"):
                continue  # occasional placeholder entries without a job page
            req = (p.get("bulletFields") or [p["externalPath"].rsplit("_", 1)[-1]])[0]
            listing[req] = {**p, "job_family": fam.get("descriptor", ""), "requisition": req}

    known = _known_rows()
    todo = [r for r in listing if f"nvidia-{r}" not in known]
    if limit:
        todo = todo[:limit]
    pages, errors = [], []
    for req in todo:
        url = f"{BASE}/{SITE}{listing[req]['externalPath']}"
        assert_allowed(robots, url)
        try:
            h = session.get(url).text
        except Exception as e:  # keep going; the snapshot guard decides
            errors.append({"url": url, "error": str(e)})
            continue
        ld = None
        for block in _LDJSON.findall(h):
            try:
                d = json.loads(block)
            except json.JSONDecodeError:
                continue
            if d.get("@type") == "JobPosting":
                ld = d
                break
        pages.append({"requisition": req, "url": url, "jsonld": ld})
    return {
        "board_total": sum(f.get("count", 0) for f in families),
        "listing_count": len(listing),
        "listing": list(listing.values()),
        "details_attempted": len(todo),
        "pages": pages,
        "errors": errors,
        "carried_forward": len(listing) - len(todo),
    }


def _location(ld: dict) -> str:
    places = ld.get("jobLocation") or []
    if isinstance(places, dict):
        places = [places]
    out = []
    for p in places:
        a = p.get("address") or {}
        parts = [a.get("addressLocality"), a.get("addressRegion"), a.get("addressCountry")]
        out.append(", ".join(x for x in parts if x))
    return "; ".join(x for x in out if x)


def normalize(raw: dict, company: str, scraped_at: str) -> list[dict]:
    known = _known_rows()
    details = {p["requisition"]: p for p in raw.get("pages", []) if p.get("jsonld")}
    rows = []
    for item in raw.get("listing", []):
        req = item["requisition"]
        job_id = f"{company.lower()}-{req}"
        url = f"{BASE}/{SITE}{item.get('externalPath', '')}"
        if req in details:
            ld = details[req]["jsonld"]
            desc = scrub_contacts(html_to_text(ld.get("description")))
            posted = (ld.get("datePosted") or "")[:10]
            location = _location(ld) or item.get("locationsText", "")
            emp = ld.get("employmentType", "")
        elif job_id in known:
            k = known[job_id]
            desc, posted, location, emp = k["job_description"], k["posting_date"], k["location"], k["employment_type"]
        else:
            continue  # no description yet (detail fetch failed or test mode): skip, next run retries
        rows.append({
            "job_id": job_id,
            "company_name": company,
            "job_title": item.get("title", ""),
            "job_description": desc,
            "posting_date": posted,
            "location": location,
            "job_url": url,
            "employment_type": emp,
            "department": item.get("job_family", ""),
            "remote_type": "remote" if "remote" in (location + url).lower() else "",
            "salary_range": "",
            "updated_at": "",
            "scraped_date": scraped_at,
            "source_name": SOURCE,
        })
    return rows
