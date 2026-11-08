"""OpenAI via the Ashby Public Job Posting API (documented, no auth)."""

from __future__ import annotations

from .common import PoliteSession, scrub_contacts

SOURCE = "ashby_posting_api"


def fetch(session: PoliteSession, board: str) -> dict:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
    return session.get(url, params={"includeCompensation": "true"}).json()


def _locations(j: dict) -> str:
    locs = [j.get("location") or ""]
    for s in j.get("secondaryLocations") or []:
        locs.append(s.get("location") or "")
    return "; ".join(dict.fromkeys(l for l in locs if l))


def normalize(raw: dict, company: str, scraped_at: str) -> list[dict]:
    rows = []
    for j in raw.get("jobs", []):
        if j.get("isListed") is False:
            continue  # unlisted = direct-link only; respect the board's intent
        comp = j.get("compensation") or {}
        workplace = (j.get("workplaceType") or "").lower()
        rows.append(
            {
                "job_id": f"{company.lower()}-{j['id']}",
                "company_name": company,
                "job_title": j.get("title", ""),
                "job_description": scrub_contacts(j.get("descriptionPlain") or ""),
                "posting_date": (j.get("publishedAt") or "")[:10],
                "location": _locations(j),
                "job_url": j.get("jobUrl", ""),
                "employment_type": j.get("employmentType", ""),
                "department": j.get("department") or j.get("team") or "",
                "remote_type": {"onsite": "onsite", "remote": "remote", "hybrid": "hybrid"}.get(
                    workplace, "remote" if j.get("isRemote") else ""
                ),
                "salary_range": comp.get("compensationTierSummary") or comp.get("scrapeableCompensationSalarySummary") or "",
                "updated_at": j.get("publishedAt", ""),
                "scraped_date": scraped_at,
                "source_name": SOURCE,
            }
        )
    return rows
