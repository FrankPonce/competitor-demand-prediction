"""NVIDIA via job pages listed in the Workday board's published sitemap.

Conditions (see docs/sprints/sprint-01-data-sources-legal.md):
- only sitemap-listed URLs under /NVIDIAExternalCareerSite/, checked against the board's robots.txt
- slow (default 1 request / 3 s), weekly
- every row keeps its source job URL
"""

from __future__ import annotations

import json
import re

from .common import PoliteSession, Robots, assert_allowed, html_to_text, scrub_contacts

SOURCE = "nvidia_workday_sitemap"
BASE = "https://nvidia.wd5.myworkdayjobs.com"
SITE_PATH = "/NVIDIAExternalCareerSite/"
SITEMAP = f"{BASE}/NVIDIAExternalCareerSite/siteMap.xml"

_LOC = re.compile(r"<loc>([^<]+)</loc>")
_LDJSON = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)


def fetch(session: PoliteSession, limit: int | None = None) -> dict:
    robots = Robots.fetch(session, f"{BASE}/robots.txt")
    assert_allowed(robots, SITEMAP)
    urls = [u for u in _LOC.findall(session.get(SITEMAP).text) if SITE_PATH + "job/" in u]
    if limit:
        urls = urls[:limit]
    pages, errors = [], []
    for url in urls:
        assert_allowed(robots, url)
        try:
            h = session.get(url).text
        except Exception as e:  # keep going; report at the end
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
        pages.append({"url": url, "jsonld": ld})
    return {"sitemap": SITEMAP, "sitemap_url_count": len(urls), "pages": pages, "errors": errors}


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
    rows = []
    for p in raw.get("pages", []):
        ld = p.get("jsonld")
        if not ld:
            continue
        req = p["url"].rsplit("_", 1)[-1]  # requisition id, e.g. JR2028682
        ident = ld.get("identifier") or {}
        req = ident.get("value") or req
        rows.append(
            {
                "job_id": f"{company.lower()}-{req}",
                "company_name": company,
                "job_title": ld.get("title", ""),
                "job_description": scrub_contacts(html_to_text(ld.get("description"))),
                "posting_date": (ld.get("datePosted") or "")[:10],
                "location": _location(ld),
                "job_url": p["url"],
                "employment_type": ld.get("employmentType", ""),
                "department": "",
                "remote_type": "remote" if "remote" in p["url"].lower() else "",
                "salary_range": "",
                "updated_at": "",
                "scraped_date": scraped_at,
                "source_name": SOURCE,
            }
        )
    return rows
