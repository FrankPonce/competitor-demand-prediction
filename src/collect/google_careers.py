"""Google via unpaginated Google Careers results pages.

robots.txt (User-agent: *) disallows careers results URLs carrying `page=`, so this collector
NEVER paginates. Each query is a narrow slice sorted newest-first, so the first page (20 jobs)
holds that slice's most recent postings. The page embeds full job data, so no job detail pages
are fetched.

Sampling design (v2, from 2026-11-09)
    Slices = 26 global hubs x 5 seniority levels, **no keywords**. v1 used AI/ML search terms,
    which biased skill shares toward those terms. Run twice a week, newest-first slices catch a
    slice's whole new-posting flow whenever its 20 newest postings reach back past the previous
    run; `covered_days` per query records exactly that, so coverage gaps are measured, not hidden.
    Absence from a later run does NOT mean a posting closed (it may just have fallen out of the
    top 20), so Google postings not seen in the latest run get status "unknown".
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from .common import (
    DisallowedURL,
    PoliteSession,
    Robots,
    assert_allowed,
    html_to_text,
    remote_type_from,
    scrub_contacts,
)

SOURCE = "google_careers_results_unpaginated"
RESULTS = "https://www.google.com/about/careers/applications/jobs/results"
JOB_URL = RESULTS + "/{id}"
SAMPLING_VERSION = 2

# Google's largest hiring hubs. The location filter is regional (Mountain View already covers the
# Bay Area, including Sunnyvale and San Francisco), so one entry per metro area.
LOCATIONS = [
    "Mountain View, CA, USA", "New York, NY, USA", "Seattle, WA, USA", "Austin, TX, USA",
    "Atlanta, GA, USA", "Cambridge, MA, USA", "Chicago, IL, USA", "Los Angeles, CA, USA",
    "Washington D.C., DC, USA", "Pittsburgh, PA, USA", "Boulder, CO, USA",
    "London, UK", "Dublin, Ireland", "Zurich, Switzerland", "Munich, Germany", "Paris, France",
    "Warsaw, Poland", "Bangalore, India", "Hyderabad, India", "Tokyo, Japan", "Singapore",
    "Sydney, NSW, Australia", "Tel Aviv, Israel", "Taipei, Taiwan", "Sao Paulo, Brazil",
    "Toronto, ON, Canada",
]
LEVELS = [["EARLY"], ["MID"], ["ADVANCED"], ["LEAD"], ["DIRECTOR"]]
# v1 keywords, kept only to document the earlier sample (no longer queried)
V1_KEYWORDS = ["machine learning", "large language model", "generative AI", "deep learning", "TPU",
               "data scientist", "AI research", "ML infrastructure"]

_DS1 = re.compile(r"AF_initDataCallback\(\{key: 'ds:1'.*?data:(.*?), sideChannel: \{\}\}\);</script>", re.S)


def build_url(location: str, levels: list[str], keyword: str | None = None) -> str:
    params = ([("q", keyword)] if keyword else []) + [("location", location)]
    params += [("target_level", lv) for lv in levels]
    params.append(("sort_by", "date"))
    url = f"{RESULTS}?{urlencode(params)}"
    if "page=" in url:
        raise DisallowedURL(url)
    return url


def fetch(session: PoliteSession, locations=None, levels=None) -> dict:
    robots = Robots.fetch(session, "https://www.google.com/robots.txt")
    now = time.time()
    queries = []
    for loc in locations or LOCATIONS:
        for lv in levels or LEVELS:
            url = build_url(loc, lv)
            assert_allowed(robots, url)
            entry = {"location": loc, "levels": lv, "url": url}
            try:
                m = _DS1.search(session.get(url).text)
                data = json.loads(m.group(1)) if m else None
            except Exception as e:
                entry["error"] = str(e)
                queries.append(entry)
                continue
            jobs = (data or [[]])[0] or []
            entry["total"] = data[2] if data and len(data) > 2 else None
            entry["returned"] = len(jobs)
            stamps = [j[12][0] for j in jobs if isinstance(j, list) and len(j) > 12
                      and isinstance(j[12], list) and j[12] and isinstance(j[12][0], int)]
            # how far back this slice's first page reaches; a full slice (total <= 20) covers everything
            entry["covered_days"] = (9999 if (entry["total"] or 0) <= len(jobs)
                                     else round((now - min(stamps)) / 86400, 1) if stamps else 0)
            entry["jobs"] = jobs
            queries.append(entry)
    # Board-wide total (one request to the unfiltered results page) for forecast scoring
    total = None
    try:
        assert_allowed(robots, RESULTS)
        m = _DS1.search(session.get(RESULTS).text)
        d = json.loads(m.group(1)) if m else None
        total = d[2] if d and len(d) > 2 and isinstance(d[2], int) else None
    except Exception:
        pass
    return {"sampling_version": SAMPLING_VERSION, "open_roles_total": total, "queries": queries}


def _text(field) -> str:
    if isinstance(field, list) and len(field) > 1:
        return html_to_text(field[1])
    return ""


def _epoch_date(field) -> str:
    if isinstance(field, list) and field and isinstance(field[0], int):
        return datetime.fromtimestamp(field[0], tz=timezone.utc).date().isoformat()
    return ""


def normalize(raw: dict, company: str, scraped_at: str) -> list[dict]:
    """Map the positional job array. Index meanings were inferred on 2026-11-08:
    0 id, 1 title, 3 responsibilities, 4 qualifications, 7 brand, 9 locations,
    10 about-the-job, 12/13/14 epoch timestamps (12 used as posting date).
    """
    rows, seen = [], set()
    for q in raw.get("queries", []):
        for j in q.get("jobs", []):
            if not isinstance(j, list) or len(j) < 13 or j[0] in seen:
                continue
            seen.add(j[0])
            locations = "; ".join(l[0] for l in (j[9] or []) if l and l[0])
            description = "\n\n".join(
                t for t in (_text(j[10]), "Responsibilities:\n" + _text(j[3]), _text(j[4])) if t.strip()
            )
            rows.append(
                {
                    "job_id": f"{company.lower()}-{j[0]}",
                    "company_name": company,
                    "job_title": j[1] or "",
                    "job_description": scrub_contacts(description),
                    "posting_date": _epoch_date(j[12]),
                    "location": locations,
                    "job_url": JOB_URL.format(id=j[0]),
                    "employment_type": "",
                    "department": j[7] or "",  # brand: Google, DeepMind, YouTube, ...
                    "remote_type": remote_type_from(locations),
                    "salary_range": "",
                    "updated_at": _epoch_date(j[14]) if len(j) > 14 else "",
                    "scraped_date": scraped_at,
                    "source_name": SOURCE,
                }
            )
    return rows
