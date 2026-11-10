"""Regression tests for the rules and fixes made in Sprints 1–5.

Run: python -m pytest -q
"""

import pandas as pd
import pytest

from src.collect.common import Robots, html_to_text, scrub_contacts
from src.collect.google_careers import build_url
from src.features.extract import match_skills, role_family, seniority
from src.preprocess.clean import drop_boilerplate, extract_salary, frequent_sentences, normalize
from src.preprocess.sections import split_sections
from src.style import COMPANY_COLOR, colorize_markdown

# ---------------------------------------------------------------- Sprint 1–2: compliance & collection

GOOGLE_ROBOTS = """
User-agent: *
Disallow: /about/careers/applications/candidate-prep
Disallow: /about/careers/applications/jobs/results?page=
Disallow: /about/careers/applications/jobs/results/?page=
Disallow: /about/careers/applications/jobs/results?*&page=
"""
BASE = "https://www.google.com/about/careers/applications/jobs/results"


@pytest.mark.parametrize("url,allowed", [
    (BASE + "?q=ml&location=Zurich", True),
    (BASE + "/123-ml-engineer", True),
    (BASE + "?page=2", False),
    (BASE + "?q=ml&page=2", False),
    ("https://www.google.com/about/careers/applications/candidate-prep/x", False),
])
def test_robots_wildcards(url, allowed):
    assert Robots(GOOGLE_ROBOTS).allowed(url) is allowed


def test_google_urls_never_paginate():
    url = build_url("London, UK", ["MID"])
    assert "page=" not in url and "sort_by=date" in url


def test_contacts_scrubbed():
    out = scrub_contacts("Email jane.doe@example.com or call +1 (415) 555-0100.")
    assert "@" not in out and "555" not in out


def test_greenhouse_double_escaped_html():
    assert html_to_text("&lt;p&gt;Build &amp;amp; ship&lt;/p&gt;") == "Build & ship"


# ---------------------------------------------------------------- Sprint 3: preprocessing

def test_nvidia_inline_headings_without_full_stop():
    text = ("Intro. What you'll be doing: Build things (thousands of GPUs) What we need to see: "
            "5+ years of C++. Ways to stand out from the crowd: CUDA experience.")
    s = split_sections(normalize(text))
    assert "Build things" in s["responsibilities"]
    assert "C++" in s["requirements"]
    assert "CUDA" in s["preferred"]


def test_line_headings():
    s = split_sections("About the role\nGreat team.\nResponsibilities:\nShip models\nYou may be a good fit if you have:\nPython")
    assert s["about"] == "Great team." and s["responsibilities"] == "Ship models" and s["requirements"] == "Python"


@pytest.mark.parametrize("text,expected", [
    ("$185K – $325K • Offers Equity", (185_000, 325_000)),           # en dash (Ashby)
    ("The US base salary range is $141,000-$202,000 + bonus", (141_000, 202_000)),
    ("136,000 USD - 212,750 USD for Level 3; 184,000 USD - 356,500 USD for Level 4", (136_000, 356_500)),
    ("No pay info", (None, None)),
])
def test_salary(text, expected):
    assert extract_salary(text) == expected


def test_boilerplate_keeps_common_requirements():
    blurb = "Google is proud to be an equal opportunity workplace for everyone."
    req = "Bachelor's degree or equivalent practical experience."
    freq = frequent_sentences([f"{blurb} {req}"] * 10)
    kept = drop_boilerplate(f"{req}\n{blurb}", freq, "Google", strict=False)
    assert "Bachelor" in kept and "equal opportunity" not in kept


# ---------------------------------------------------------------- Sprint 4: skills & features

def skills(text):
    return set(match_skills({"requirements": text}))


def test_skill_true_positives():
    s = skills("Python, Go, Rust or C, C++. Transformer models. LLM inference. Lead the procurement function. "
               "Build and scale strategic partnerships with GSIs. Fluent in Japanese.")
    assert {"Python", "Go", "Rust", "C", "C++", "Transformers", "Inference & Serving",
            "Procurement & Vendor Management", "Business Development & Partnerships", "Japanese"} <= s


@pytest.mark.parametrize("text,not_expected", [
    ("Detection & Response (D&R) team", "R"),
    ("keep I&C, Legal informed", "C"),
    ("MV distribution, transformers, switchgear", "Transformers"),
    ("deep grounding in causal inference", "Inference & Serving"),
    ("navigate enterprise procurement cycles", "Procurement & Vendor Management"),
    ("partner closely with Sales, Partnerships, Product", "Business Development & Partnerships"),
    ("trademark clearance and prosecution", "Government & Public Sector"),
    ("Go deep on customer problems", "Go"),
    ("excel at building relationships", "Excel / Spreadsheets"),
    ("knowledge of the French market", "French"),
    ("degree in Electrical Engineering", "Electrical Engineering"),
])
def test_skill_false_positives(text, not_expected):
    assert not_expected not in skills(text)


@pytest.mark.parametrize("title,family", [
    ("Data Scientist, Growth", "Data & Analytics"),
    ("Research Scientist, Interpretability", "Research"),
    ("Account Executive, Security", "Sales & Go-to-Market"),
    ("Senior Firmware Engineer", "Hardware & Silicon"),
    ("Software Engineer, Inference", "ML / AI Engineering"),
])
def test_role_family(title, family):
    assert role_family(title) == family


@pytest.mark.parametrize("title,years,level,mgr", [
    ("Product Manager, API", None, "Unspecified", False),       # PMs are not people managers
    ("Engineering Manager, Inference", None, "Manager", True),
    ("Software Engineer III", None, "Mid", False),
    ("Software Engineer II", None, "Junior", False),
    ("Member of Technical Staff", 12, "Principal", False),
])
def test_seniority(title, years, level, mgr):
    assert seniority(title, years) == (level, mgr)


# ---------------------------------------------------------------- style

def test_company_colours_fixed():
    assert list(COMPANY_COLOR) == ["Anthropic", "OpenAI", "NVIDIA", "Google"]


def test_colorize_is_idempotent():
    once = colorize_markdown("| company | x |\n| Anthropic | 1 |\nplain Anthropic text")
    assert once == colorize_markdown(once)
    assert "🟠 Anthropic | 1" in once and "plain Anthropic text" in once


# ---------------------------------------------------------------- Sprint 5: data invariants

def test_corpus_roundtrip_if_built():
    from src.preprocess.corpus_io import CSV_DIR, load_corpus
    if not any(CSV_DIR.glob("*.csv")):
        pytest.skip("corpus not built")
    d = load_corpus()
    assert d.job_id.is_unique
    assert (d.job_description.str.len() == d.n_chars_raw).all()


def test_weekly_trends_only_complete_weeks():
    from pathlib import Path
    f = Path("data/trends/weekly_company.csv")
    if not f.exists():
        pytest.skip("trends not built")
    t = pd.read_csv(f, parse_dates=["week"])
    assert (t.week.dt.day_of_week == 0).all()  # Mondays


# ---------------------------------------------------------------- Sprint 6: comparison

@pytest.mark.parametrize("loc,expected", [
    ("San Francisco, CA; New York City, NY; London, UK", {"US", "Europe"}),
    ("US, CA, Santa Clara, United States of America", {"US"}),
    ("Bengaluru, Karnataka, India", {"Asia-Pacific"}),
    ("Israel, Yokneam", {"Other"}),
    ("Ontario, CAN", {"Other"}),
    ("London, UK", {"Europe"}),
])
def test_region_parsing(loc, expected):
    from src.compare.build_comparison import regions
    assert regions(loc) == expected


def test_primary_hub_normalises_formats():
    from src.compare.build_comparison import primary_hub
    assert primary_hub("US, CA, Santa Clara, United States of America") == "Santa Clara"
    assert primary_hub("New York City, NY; Seattle, WA") == "New York"
    assert primary_hub("Remote-Friendly (Travel-Required)") == "Remote"


# ---------------------------------------------------------------- Review additions (2026-11-09)

@pytest.mark.parametrize("loc,expected", [
    ("San Francisco, CA; New York City, NY", [("San Francisco", "US"), ("New York", "US")]),
    ("United States: Seattle", [("Seattle", "US")]),                       # Epoch format
    ("US, CA, Santa Clara, United States of America", [("Santa Clara", "US")]),  # NVIDIA format
    ("Remote-Friendly (Travel-Required); London, UK", [("London", "GB")]),
])
def test_parse_locations(loc, expected):
    from src.trends.geo_pay import parse_locations
    assert parse_locations(loc) == expected


def test_geocode_province_falls_back_to_capital():
    from src.trends.geo_pay import geocode
    lat, lon, name, cc = geocode("Ontario", "CA")
    assert cc == "CA"  # not Ontario, California


def test_fightin_words_direction():
    import numpy as np
    from src.trends.emerging_terms import fightin_words
    z = fightin_words(np.array([50.0, 5.0]), np.array([5.0, 50.0]), 500, 500)
    assert z[0] > 3 and z[1] < -3


def test_wayback_parsers():
    from src.collect.wayback_history import google_count, greenhouse_count
    assert greenhouse_count('{"jobPosts":{"count":50,"page":1,"total":146}}') == 146
    links = "".join(f'<a href="/anthropic/jobs/{4000000 + i}">' for i in range(12))
    assert greenhouse_count(links) == 12
    assert greenhouse_count("<html>redirect</html>") is None
    page = "AF_initDataCallback({key: 'ds:1', hash: 'x', data:[[],null,2807,20], sideChannel: {}});</script>"
    assert google_count(page) == 2807


# ---------------------------------------------------------------- Sprint 7: forecasting

def test_baseline_models_shapes_and_values():
    import numpy as np
    from src.forecast.models import drift, ma4, naive, predict
    y = pd.Series([10.0, 12, 14, 16, 18, 20], index=pd.date_range("2026-01-05", periods=6, freq="7D"))
    assert list(naive(y, 3)) == [20, 20, 20]
    assert np.allclose(drift(y, 2), [22, 24])
    assert np.allclose(ma4(y, 1), [17])
    falling = pd.Series([5.0, 3, 1, 0.5], index=y.index[:4])
    assert (predict("drift", falling, 6, seasonal=False) >= 0).all()  # never negative


def test_seasonal_naive_replays_last_years_pattern():
    import numpy as np
    from src.forecast.models import snaive
    idx = pd.date_range("2024-01-01", periods=60, freq="7D")
    pattern = 100 + 10 * np.sin(2 * np.pi * np.arange(60) / 52)
    y = pd.Series(pattern, index=idx)
    f = snaive(y, 4)
    # next weeks = today's level + last year's week-over-week movement at the same point in the cycle
    expected = y.iloc[-1] + (y.iloc[-52:-48].to_numpy() - y.iloc[-53])
    assert np.allclose(f, expected)


def test_frozen_forecasts_are_never_overwritten():
    from pathlib import Path
    frozen = sorted(Path("data/forecasts/frozen").glob("*.csv"))
    if not frozen:
        pytest.skip("no frozen forecasts")
    f = pd.read_csv(frozen[0])
    assert {"series", "target_week", "point", "lo80", "hi80", "last_actual"} <= set(f.columns)
    assert (f.lo80 <= f.point).all() and (f.point <= f.hi80).all()
