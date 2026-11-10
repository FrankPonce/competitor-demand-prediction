"""Sprint 10 tests: external-source parsing, news matching and the dashboard JSON contract.

Run: python -m pytest -q
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.dashboard.export import _clean, news_matches
from src.external.sources import _quarterly, _topics

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "data"


# ---------------------------------------------------------------- SEC EDGAR quarterly values

def fact(start, end, val, form="10-Q"):
    return {"start": start, "end": end, "val": val, "form": form}


def test_quarterly_uses_three_month_facts_directly():
    q = _quarterly([fact("2026-01-01", "2026-03-31", 100), fact("2026-04-01", "2026-06-30", 120)])
    assert q == {"2026-03-31": 100, "2026-06-30": 120}


def test_quarterly_differences_year_to_date_chain():
    # Q1 reported as 3 months, then 6- and 9-month year-to-date totals from the same fiscal-year start
    q = _quarterly([fact("2026-01-01", "2026-03-31", 100),
                    fact("2026-01-01", "2026-06-30", 250),
                    fact("2026-01-01", "2026-09-30", 420)])
    assert q["2026-06-30"] == 150 and q["2026-09-30"] == 170


def test_quarterly_never_reports_a_ytd_total_as_a_quarter():
    # chain without a genuine first quarter (only 6- and 9-month totals): nothing can be derived
    q = _quarterly([fact("2026-01-01", "2026-06-30", 250), fact("2026-01-01", "2026-09-30", 420)])
    assert q == {}


def test_quarterly_prefers_reported_quarter_over_difference_and_ignores_other_forms():
    q = _quarterly([fact("2026-04-01", "2026-06-30", 151),
                    fact("2026-01-01", "2026-03-31", 100),
                    fact("2026-01-01", "2026-06-30", 250),
                    fact("2026-01-01", "2026-03-31", 999, form="8-K")])
    assert q["2026-06-30"] == 151 and q["2026-03-31"] == 100


# ---------------------------------------------------------------- news topics and watchlist matching

@pytest.mark.parametrize("title,expected", [
    ("OpenAI opens new office in Amsterdam", {"expansion"}),
    ("Anthropic raises $30B at $380B valuation", {"funding"}),
    ("NVIDIA unveils new supercomputer for data centers", {"launch", "infrastructure"}),
    ("Quarterly earnings call transcript", set()),
])
def test_news_topic_tagging(title, expected):
    got = set(filter(None, _topics(title).split(";")))
    assert expected <= got
    if not expected:
        assert got == set()


def test_news_watchlist_matcher():
    watch = pd.DataFrame([{"company": "OpenAI", "city": "Amsterdam", "first_seen": "2026-11-08"}])
    news = pd.DataFrame([
        {"company": "OpenAI", "date": "2026-12-01", "title": "OpenAI to open Amsterdam office", "url": "u1", "source": "s"},
        {"company": "OpenAI", "date": "2026-12-02", "title": "OpenAI CEO visits Amsterdam", "url": "u2", "source": "s"},
        {"company": "Anthropic", "date": "2026-12-03", "title": "Anthropic opens Amsterdam office", "url": "u3", "source": "s"},
        {"company": "OpenAI", "date": "2026-12-04", "title": "OpenAI expands in Amsterdamse", "url": "u4", "source": "s"},
    ])
    hits = news_matches(news, watch)
    assert [h["url"] for h in hits] == ["u1"]  # needs same company, whole-word city, office wording
    assert hits[0]["lead_days"] == 23


def test_clean_makes_json_safe():
    out = _clean({"a": np.float64("nan"), "b": np.int64(3), "c": [np.float32(0.123456)], "d": pd.Timestamp("2026-11-10")})
    assert out == {"a": None, "b": 3, "c": [0.1235], "d": "2026-11-10"}
    json.dumps(out, allow_nan=False)


# ---------------------------------------------------------------- dashboard JSON contract (what app.js reads)

FOCUS = ["Anthropic", "OpenAI", "NVIDIA", "Google"]
need_data = pytest.mark.skipif(not (DASH / "meta.json").exists(), reason="run src.dashboard.export first")


def load(name):
    return json.loads((DASH / name).read_text(encoding="utf-8"))


@need_data
def test_all_dashboard_files_are_small_strict_json():
    for name in ["meta", "companies", "globe", "signals", "news", "tracker", "market", "context"]:
        p = DASH / f"{name}.json"
        assert p.stat().st_size < 200_000, f"{name}.json too large for a fast page"
        json.loads(p.read_text(encoding="utf-8"), parse_constant=lambda c: pytest.fail(f"{name}: {c}"))


@need_data
def test_companies_contract():
    co = load("companies.json")
    assert set(FOCUS) <= set(co)
    for name in FOCUS:
        d = co[name]
        assert {"color", "logo", "tagline", "unit", "kpi", "history", "forecast", "role_mix", "skills", "hubs", "peers"} <= set(d)
        assert (ROOT / "dashboard" / d["logo"]).exists()
        dates = [r[0] for r in d["history"]]
        assert dates == sorted(dates) and len(dates) > 8
        for date, point, lo, hi in d["forecast"]:
            assert lo <= point <= hi and date > dates[-1] or date >= dates[-1]
        assert all(len(s) == 4 for s in d["skills"])  # skill, share, share_others, lift


@need_data
def test_globe_signals_tracker_market_contract():
    g = load("globe.json")
    assert all(-90 <= p["lat"] <= 90 and -180 <= p["lon"] <= 180 for p in g["points"])
    assert {a["status"] for a in g["arcs"]} <= {"hiring led", "hiring lagged", "simultaneous", "watch"}
    assert all(len(a["start"]) == 2 and len(a["end"]) == 2 for a in g["arcs"])

    for s in load("signals.json"):
        assert {"date", "company", "type", "confidence", "title"} <= set(s)
        assert s["confidence"] in {"confirmed", "likely", "watch", "context"}

    t = load("tracker.json")
    assert t["frozen_on"] and t["targets"] >= len(t["forecasts"]) > 0
    assert t["coverage80"] is None or 0 <= t["coverage80"] <= 1

    m = load("market.json")
    names = {n["name"] for n in m["nodes"]}
    assert all(e["source"] in names and e["target"] in names for e in m["edges"])
    pools = m["pools"]
    assert len(pools["values"]) == len(pools["names"])
    assert all(len(row) == len(pools["companies"]) and all(not math.isnan(v) for v in row) for row in pools["values"])
