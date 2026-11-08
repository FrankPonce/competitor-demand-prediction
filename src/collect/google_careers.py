"""Google via unpaginated Google Careers results pages.

robots.txt (User-agent: *) disallows careers results URLs carrying `page=`, so this
collector NEVER paginates. Instead each query is a narrow slice
(keyword x location x seniority) sorted newest-first, so the first page (20 jobs) holds
that slice's most recent postings. Run weekly, this captures most *new* postings per
slice over time. The page embeds full job data, so no job detail pages are fetched.
Coverage per query (returned vs. total) is recorded in the run log.
"""

from __future__ import annotations

import json
import re
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

# AI/ML + infrastructure focus, across major hubs. Edit freely, but keep queries narrow.
KEYWORDS = [
    "machine learning",
    "large language model",
    "generative AI",
    "deep learning",
    "TPU",
    "data scientist",
    "AI research",
    "ML infrastructure",
]
LOCATIONS = [
    "Mountain View, CA, USA",
    "San Francisco, CA, USA",
    "New York, NY, USA",
    "Seattle, WA, USA",
    "London, UK",
    "Zurich, Switzerland",
    "Bangalore, India",
    "Tokyo, Japan",
]

LEVELS = [["EARLY"], ["MID"], ["ADVANCED"], ["LEAD", "DIRECTOR"]]

_DS1 = re.compile(r"AF_initDataCallback\(\{key: 'ds:1'.*?data:(.*?), sideChannel: \{\}\}\);</script>", re.S)


def build_url(keyword: str, location: str, levels: list[str]) -> str:
    params = [("q", keyword), ("location", location)]
    params += [("target_level", lv) for lv in levels]
    params.append(("sort_by", "date"))
    url = f"{RESULTS}?{urlencode(params)}"
    if "page=" in url:
        raise DisallowedURL(url)
    return url


def fetch(session: PoliteSession, keywords=None, locations=None, levels=None) -> dict:
    robots = Robots.fetch(session, "https://www.google.com/robots.txt")
    queries = []
    for kw in keywords or KEYWORDS:
        for loc in locations or LOCATIONS:
            for lv in levels or LEVELS:
                url = build_url(kw, loc, lv)
                assert_allowed(robots, url)
                entry = {"keyword": kw, "location": loc, "levels": lv, "url": url}
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
                entry["jobs"] = jobs
                queries.append(entry)
    return {"queries": queries}


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
