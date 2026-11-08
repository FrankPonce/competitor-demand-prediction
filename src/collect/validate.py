"""Data-quality checks run on every snapshot (Data Quality Lead duties)."""

from __future__ import annotations

import re

from .common import EMAIL

REQUIRED = ["job_id", "company_name", "job_title", "job_description", "posting_date", "location", "job_url"]
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_rows(rows: list[dict]) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    for r in rows:
        jid = r.get("job_id", "?")
        for f in REQUIRED:
            if not (r.get(f) or "").strip():
                # location / posting_date can legitimately be missing at source; still flag
                issues.append(f"{jid}: missing {f}")
        if jid in seen:
            issues.append(f"{jid}: duplicate job_id")
        seen.add(jid)
        if r.get("posting_date") and not DATE.match(r["posting_date"]):
            issues.append(f"{jid}: bad posting_date {r['posting_date']!r}")
        if EMAIL.search(r.get("job_description", "")):
            issues.append(f"{jid}: email address left in description")
        if not (r.get("job_url") or "").startswith("https://"):
            issues.append(f"{jid}: job_url not https")
    return issues
