"""Anthropic via the Greenhouse public Job Board API (documented, no auth)."""

from __future__ import annotations

import re

from .common import PoliteSession, html_to_text, remote_type_from, scrub_contacts

SOURCE = "greenhouse_job_board_api"


def fetch(session: PoliteSession, board: str) -> dict:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    return session.get(url, params={"content": "true"}).json()


def normalize(raw: dict, company: str, scraped_at: str) -> list[dict]:
    rows = []
    for j in raw.get("jobs", []):
        meta = {m.get("name"): m.get("value") for m in j.get("metadata") or []}
        location = (j.get("location") or {}).get("name", "")
        loc_type = meta.get("Location Type") or ""
        rows.append(
            {
                "job_id": f"{re.sub(r'\W+', '', company.lower())}-{j['id']}",
                "company_name": company,
                "job_title": j.get("title", ""),
                "job_description": scrub_contacts(html_to_text(j.get("content"))),
                "posting_date": (j.get("first_published") or j.get("updated_at") or "")[:10],
                "location": location.replace(" | ", "; "),
                "job_url": j.get("absolute_url", ""),
                "employment_type": "",
                "department": "; ".join(d["name"] for d in j.get("departments") or []),
                "remote_type": remote_type_from(f"{loc_type} {location}"),
                "salary_range": "",
                "updated_at": j.get("updated_at", ""),
                "scraped_date": scraped_at,
                "source_name": SOURCE,
            }
        )
    return rows
