"""Download Epoch AI 'Data on Frontier Lab Hiring' (CC BY) for Anthropic + OpenAI history.

Attribution: Epoch AI, "Data on Frontier Lab Hiring", epoch.ai — https://epoch.ai/data/frontier-lab-hiring

Usage:
    python -m src.collect.epoch_history

Writes data/external/epoch/<YYYY-MM-DD>/ (the zip's CSVs + README) and
data/processed/epoch_history.csv mapped to the project schema.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from .common import PoliteSession, scrub_contacts, today

ROOT = Path(__file__).resolve().parents[2]
ZIP_URL = "https://epoch.ai/data/frontier_lab_hiring.zip"
OUT = ROOT / "data" / "external" / "epoch"
FIELDS = [
    "job_id", "company_name", "job_title", "job_description", "posting_date", "location", "job_url",
    "department", "job_category", "first_seen_date", "last_seen_date", "job_status", "source_name",
]

csv.field_size_limit(2**31 - 1)


def main() -> None:
    s = PoliteSession(delay_seconds=1.0, timeout=120)
    data = s.get(ZIP_URL).content
    dest = OUT / today()
    dest.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(data)).extractall(dest)

    texts: dict[str, dict] = {}  # one row per posting: advert text as last observed
    tpath = dest / "frontier_lab_hiring_posting_texts.csv"
    if tpath.exists():
        with tpath.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                texts[row["posting"]] = row

    rows = []
    with (dest / "frontier_lab_hiring_postings.csv").open(encoding="utf-8") as f:
        for p in csv.DictReader(f):
            t = texts.get(p["posting"], {})
            rows.append({
                "job_id": p["posting"].replace(":", "-"),
                "company_name": p["lab"],
                "job_title": p["title"],
                "job_description": scrub_contacts(t.get("description", "")),
                "posting_date": p["first_seen"],
                "location": p.get("cities") or p.get("countries") or "",
                "job_url": "",
                "department": t.get("department") or p.get("category", ""),
                "job_category": f"{p.get('category', '')} / {p.get('subcategory', '')}".strip(" /"),
                "first_seen_date": p["first_seen"],
                "last_seen_date": p["last_seen"],
                "job_status": "active" if p.get("open_at_latest_scrape") == "true" else "closed",
                "source_name": "epoch_ai_frontier_lab_hiring",
            })
    out = ROOT / "data" / "processed" / "epoch_history.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    with_text = sum(1 for r in rows if r["job_description"])
    print(f"Epoch: {len(rows)} postings ({with_text} with text) -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
