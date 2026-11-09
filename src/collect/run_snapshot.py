"""Take one weekly snapshot for one or more companies.

Usage (from the repo root):
    python -m src.collect.run_snapshot                 # all four companies
    python -m src.collect.run_snapshot anthropic openai
    python -m src.collect.run_snapshot nvidia --limit 5    # quick test

Writes:
    data/raw/<company>/<YYYY-MM-DD>.json   raw source response        (kept local)
    data/raw/<company>/<YYYY-MM-DD>.csv    normalized snapshot        (committed)
    data/processed/<company>.csv           all snapshots merged with
                                           first/last seen + status   (committed)
    reports/collection-log.csv             counts per run, no text    (committed)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import ashby, google_careers, greenhouse, nvidia_workday
from .common import FIELDS, PoliteSession, today, utc_now_iso
from .validate import validate_rows

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
LOG = ROOT / "reports" / "collection-log.csv"

csv.field_size_limit(2**31 - 1)

COMPANIES = {
    "anthropic": ("Anthropic", lambda s, a: greenhouse.fetch(s, "anthropic"), greenhouse.normalize, 1.0),
    "openai": ("OpenAI", lambda s, a: ashby.fetch(s, "openai"), ashby.normalize, 1.0),
    "nvidia": ("NVIDIA", lambda s, a: nvidia_workday.fetch(s, limit=a.limit), nvidia_workday.normalize, 2.5),
    "google": (
        "Google",
        lambda s, a: google_careers.fetch(
            s,
            locations=google_careers.LOCATIONS[: a.limit] if a.limit else None,
            levels=google_careers.LEVELS[: a.limit] if a.limit else None,
        ),
        google_careers.normalize,
        3.0,
    ),
}

MERGED_FIELDS = FIELDS + ["first_seen_date", "last_seen_date", "job_status"]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def merge_snapshots(key: str) -> list[dict]:
    """Rebuild the per-company dataset from every snapshot CSV (idempotent)."""
    snaps = sorted((RAW / key).glob("????-??-??.csv"))
    if not snaps:
        return []
    latest_date = snaps[-1].stem
    merged: dict[str, dict] = {}
    for snap in snaps:
        date = snap.stem
        with snap.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                prev = merged.get(row["job_id"])
                row["first_seen_date"] = prev["first_seen_date"] if prev else date
                row["last_seen_date"] = date
                if prev and not row.get("posting_date"):
                    row["posting_date"] = prev.get("posting_date", "")
                merged[row["job_id"]] = row
    for row in merged.values():
        if row["last_seen_date"] == latest_date:
            row["job_status"] = "active"
        else:
            # Google is a newest-first sample: dropping out of the top 20 doesn't mean the job closed.
            row["job_status"] = "unknown" if key == "google" else "closed"
        if not row.get("posting_date"):
            row["posting_date"] = row["first_seen_date"]
    return sorted(merged.values(), key=lambda r: r["job_id"])


def append_log(entry: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(entry))
        if new:
            w.writeheader()
        w.writerow(entry)


def run(key: str, args) -> dict:
    company, fetch, normalize, delay = COMPANIES[key]
    session = PoliteSession(delay_seconds=delay)
    started = utc_now_iso()
    date = today()
    raw = fetch(session, args)
    out_dir = RAW / key
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{date}.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    rows = normalize(raw, company, started)
    issues = validate_rows(rows)
    # An incomplete snapshot would make missing postings look "closed": refuse to save it.
    attempted = raw.get("details_attempted") or len(raw.get("queries", [])) or 0
    failed = len(raw.get("errors", [])) + sum(1 for q in raw.get("queries", []) if "error" in q)
    if attempted and failed / attempted > 0.05:
        raise RuntimeError(f"{failed}/{attempted} fetches failed; snapshot not saved (re-run later)")
    board, listed = raw.get("board_total"), raw.get("listing_count")
    if board and not args.limit and listed < 0.95 * board:
        raise RuntimeError(f"listing covered {listed}/{board} postings; snapshot not saved (re-run later)")
    if not args.limit:  # test runs don't pollute the time series
        write_csv(out_dir / f"{date}.csv", rows, FIELDS)
        merged = merge_snapshots(key)
        write_csv(PROCESSED / f"{key}.csv", merged, MERGED_FIELDS)
    else:
        merged = []

    note = ""
    if key == "google":
        qs = raw.get("queries", [])
        ok = [q for q in qs if "error" not in q]
        weekly = sum(1 for q in ok if q.get("covered_days", 0) >= 7)
        half = sum(1 for q in ok if q.get("covered_days", 0) >= 3.5)
        note = (f"v{raw.get('sampling_version', 1)}: {len(qs)} slices; full-flow coverage "
                f"weekly {weekly}/{len(ok)}, twice-weekly {half}/{len(ok)}")
    if key == "nvidia":
        note = (f"board={raw.get('board_total')}; listed={raw.get('listing_count')}; new details="
                f"{raw.get('details_attempted')}; carried={raw.get('carried_forward')}; errors={len(raw.get('errors', []))}")

    entry = {
        "run_started_utc": started,
        "company": company,
        "source": rows[0]["source_name"] if rows else "",
        "requests": session.request_count,
        "postings_in_snapshot": len(rows),
        "postings_total_merged": len(merged),
        "active": sum(1 for r in merged if r["job_status"] == "active"),
        "validation_issues": len(issues),
        "test_run": bool(args.limit),
        "notes": note,
    }
    if not args.limit:
        append_log(entry)
    for msg in issues[:10]:
        print(f"  [{company}] {msg}")
    return entry


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("companies", nargs="*", choices=list(COMPANIES), help="default: all four")
    p.add_argument("--limit", type=int, default=None, help="test mode: fetch only a few items, don't save CSVs")
    args = p.parse_args(argv)
    args.companies = args.companies or list(COMPANIES)
    ok = True
    for key in args.companies:
        try:
            e = run(key, args)
            print(f"{e['company']}: {e['postings_in_snapshot']} postings "
                  f"({e['requests']} requests, {e['validation_issues']} issues) {e['notes']}")
        except Exception as ex:
            ok = False
            print(f"{key}: FAILED: {ex}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
