"""Print dataset stats as Markdown (for Data Collection Reports and weekly notes).

Usage:
    python -m src.collect.report_stats            # all processed datasets
    python -m src.collect.report_stats nvidia
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
csv.field_size_limit(2**31 - 1)

CHECK = ["job_title", "job_description", "posting_date", "location", "job_url",
         "employment_type", "department", "remote_type", "salary_range"]


def stats(path: Path) -> str:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    if not rows:
        return f"### {path.stem}\n\n_No rows._\n"
    n = len(rows)
    dates = sorted(r["posting_date"] for r in rows if r.get("posting_date"))
    lines = [f"### {path.stem}", "", f"- Postings: **{n}**"]
    if dates:
        lines.append(f"- Posting dates: {dates[0]} → {dates[-1]}")
    if "job_status" in rows[0]:
        st = Counter(r["job_status"] for r in rows)
        lines.append(f"- Status: " + ", ".join(f"{k} {v}" for k, v in st.most_common()))
    lens = sorted(len(r.get("job_description", "")) for r in rows)
    lines.append(f"- Description length (chars): median {lens[n // 2]:,}, min {lens[0]:,}, max {lens[-1]:,}")
    lines += ["", "| Field | Filled |", "|---|---:|"]
    for f in CHECK:
        if f in rows[0]:
            filled = sum(1 for r in rows if (r.get(f) or "").strip())
            lines.append(f"| `{f}` | {filled / n:.0%} |")
    dept_field = "department" if "department" in rows[0] else None
    if dept_field:
        top = Counter(r[dept_field] for r in rows if r.get(dept_field)).most_common(8)
        if top:
            lines += ["", "Top departments: " + ", ".join(f"{k} ({v})" for k, v in top)]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> None:
    paths = [PROCESSED / f"{a}.csv" for a in argv] if argv else sorted(PROCESSED.glob("*.csv"))
    for p in paths:
        if p.exists():
            print(stats(p))


if __name__ == "__main__":
    main(sys.argv[1:])
