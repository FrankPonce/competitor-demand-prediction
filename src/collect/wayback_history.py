"""Historical open-role counts from the Internet Archive's Wayback Machine.

Why: Google and NVIDIA have no Epoch history, and Anthropic's Epoch history only starts in March
2026. Archived copies of public careers pages record how many roles were open on past dates.

Legal/ethical basis: the Internet Archive grants access to its collections "for scholarship and
research purposes" (archive.org/about/terms), and the CDX API is its documented interface. We fetch
archived copies, never the companies' live sites, about 1 request / 4 s. Only a **count** per capture
is extracted and stored; no posting text is kept, locally or in git.

Sources (checked 2026-11-09)
    Google     www.google.com/about/careers/applications/jobs/results    916 captures 2023-2026
               -> total open jobs embedded in the page's data (ds:1)
    Anthropic  boards.greenhouse.io/anthropic (2024-25), job-boards.greenhouse.io/anthropic (2025-26)
               -> "jobPosts.total", or unique job links on the older board design
    OpenAI     not recoverable (careers pages render jobs client-side)
    NVIDIA     not in the archive (board appears excluded); see the requisition-ID estimate instead

Usage:  python -m src.collect.wayback_history
Output: data/history/wayback_open_roles.csv   (date, company, open_roles, capture, source)
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from .common import PoliteSession

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "history" / "wayback_open_roles.csv"
CDX = "https://web.archive.org/cdx/search/cdx"

_DS1 = re.compile(r"AF_initDataCallback\(\{key: 'ds:1'.*?data:(.*?), sideChannel: \{\}\}\);</script>", re.S)
_GH_TOTAL = re.compile(r'"jobPosts"\s*:\s*\{[^{}]*?"total"\s*:\s*(\d+)')
_GH_LINK = re.compile(r"/anthropic/jobs/(\d{6,})")


def google_count(html: str) -> int | None:
    m = _DS1.search(html)
    if not m:
        return None
    try:
        d = json.loads(m.group(1))
        return int(d[2]) if len(d) > 2 and isinstance(d[2], int) else None
    except (json.JSONDecodeError, ValueError):
        return None


def greenhouse_count(html: str) -> int | None:
    m = _GH_TOTAL.search(html)
    if m:
        return int(m.group(1))
    links = set(_GH_LINK.findall(html))
    return len(links) if len(links) >= 10 else None  # tiny pages are redirects / error shells


SOURCES = [
    ("Google", "www.google.com/about/careers/applications/jobs/results", google_count),
    ("Anthropic", "boards.greenhouse.io/anthropic", greenhouse_count),
    ("Anthropic", "job-boards.greenhouse.io/anthropic", greenhouse_count),
]


def captures(session: PoliteSession, url: str) -> list[tuple[str, str]]:
    r = session.get(CDX, params={"url": url, "output": "json", "fl": "timestamp,original",
                                 "filter": "statuscode:200", "limit": "20000"})
    rows = r.json()[1:] if r.text.strip() else []
    return [(ts, orig) for ts, orig in rows if "?" not in orig]


def weekly(caps: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """One capture per ISO week (the first one in that week)."""
    seen, out = set(), []
    for ts, orig in sorted(caps):
        wk = datetime.strptime(ts[:8], "%Y%m%d").isocalendar()[:2]
        if wk not in seen:
            seen.add(wk)
            out.append((ts, orig))
    return out


def main() -> None:
    s = PoliteSession(delay_seconds=4.0, timeout=120)
    rows = []
    for company, url, parse in SOURCES:
        caps = weekly(captures(s, url))
        ok = 0
        for ts, orig in caps:
            try:
                html = s.get(f"https://web.archive.org/web/{ts}id_/{orig}").text
            except Exception:
                continue
            n = parse(html)
            if n:
                ok += 1
                rows.append({"date": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", "company": company, "open_roles": n,
                             "capture": ts, "source": url})
        print(f"{company:9s} {url}: {ok}/{len(caps)} weekly captures parsed")
    # Drop implausible single-capture collapses (error pages that still parse): >60% below both neighbours
    rows.sort(key=lambda r: (r["company"], r["date"]))
    clean = []
    for i, r in enumerate(rows):
        nb = [x["open_roles"] for x in rows[max(0, i - 1): i + 2] if x["company"] == r["company"] and x is not r]
        if nb and all(r["open_roles"] < 0.4 * v for v in nb):
            continue
        clean.append(r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "company", "open_roles", "capture", "source"])
        w.writeheader()
        w.writerows(clean)
    print(f"{len(clean)} points ({len(rows) - len(clean)} outliers dropped) -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
