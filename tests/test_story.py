"""Story layer tests: interpretation rules, the narrator's number check, LLM fallback and the story.json contract.

Run: python -m pytest -q
"""

import json
import re
from pathlib import Path

import pytest

from src import llm
from src.insights.story import THEMES, template_brief, template_company, unsupported_numbers

ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "dashboard" / "data" / "story.json"


def hits(theme, title):
    return bool(re.search(THEMES[theme]["title"], title.lower()))


# ---------------------------------------------------------------- interpretation rules

@pytest.mark.parametrize("theme,title,expected", [
    ("dc_build", "Senior Data Center Capacity Delivery Manager", True),
    ("dc_build", "Data Center Controls Engineer", True),
    ("dc_build", "White Space Manager, Network & Data Halls", True),
    ("dc_build", "Mechanical Engineer, Power Generation", True),
    ("dc_build", "Senior Software Architect - Data Center Systems", False),   # product work, not a build-out
    ("government", "Enterprise Account Executive, Federal Civilian Sales", True),
    ("government", "Customer Engineering Manager, SLED, Central, Google Public Sector", True),
    ("government", "Customer Engineering Manager, Google Cloud Fraud Defense", False),  # not defense customers
    ("government", "Cyber Defense Detection Engineer, Mandiant", False),
    ("chips", "Design Verification Engineer, TPU, Silicon", True),
    ("chips", "Software Engineer, Chip Design Tools", True),
    ("robotics", "Robotics Test Engineer", True),
    ("consumer_ads", "Software Engineer, Ad Formats", True),
    ("consumer_ads", "Software Engineer, Adversarial Robustness", False),
    ("networking", "Senior Software Engineer, NVLINK", True),
])
def test_theme_rules(theme, title, expected):
    assert hits(theme, title) is expected


def test_core_business_is_not_a_signal():
    assert "NVIDIA" in THEMES["dc_build"]["skip"] and "NVIDIA" in THEMES["chips"]["skip"]


# ---------------------------------------------------------------- narrator number check

FACTS = {"facts": {"size": {"value": 673.0}, "change_6m_pct": 56},
         "claims": [{"key_fact": "6 → 25 new roles per 13 weeks (4.2×)", "open_roles": 26, "new_13w": 25,
                     "prior_13w": 6, "lift_vs_peers": 3.7},
                    {"open_roles": 64, "new_13w": 69, "prior_13w": 41, "lift_vs_peers": 4.6}]}


def test_numbers_from_the_facts_pass():
    text = "Anthropic has 673 open roles, up 56% in six months; government roles went from 6 to 25 (4.2×)."
    assert unsupported_numbers(text, FACTS) == []


def test_invented_numbers_are_caught():
    assert unsupported_numbers("Anthropic plans 1,200 new hires and a $5 billion campus.", FACTS)


def test_rounding_is_tolerated():
    assert unsupported_numbers("about 670 open roles, a 3.7x lift", FACTS) == []


def test_multiples_in_words_must_match_growth_not_lift():
    only_safety = {"claims": [FACTS["claims"][1]]}  # 41 -> 69 (1.7x growth), lift 4.6
    assert unsupported_numbers("a four-fold jump in safety roles", only_safety) == ["four-fold"]
    assert unsupported_numbers("safety hiring nearly doubled", only_safety) == []


def test_llm_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("LLM_DISABLE", "1")
    assert llm.chat_json("s", "u") is None
    assert llm.available() == []


def test_llm_json_parsing_is_lenient():
    assert llm._parse_json('Sure! {"a": 1} done') == {"a": 1}
    assert llm._parse_json("no json here") is None


def test_rate_limit_wait_parsing():
    class R:
        def __init__(self, h):
            self.headers = h
    assert llm._wait(R({"retry-after": "7"})) == 8
    assert llm._wait(R({"x-ratelimit-reset-tokens": "1m26.4s"})) == pytest.approx(87.4)


# ---------------------------------------------------------------- templates and the story.json contract

def test_templates_work_without_llm():
    f = {"facts": {"size": {"value": 673.0}, "change_6m_pct": 56}, "expansions": [{"city": "Austin", "status": "watch"}],
         "claims": [{"id": "gov", "label": "Selling to government", "reading": "r", "key_fact": "6 → 25",
                     "concentrated_in": ["Washington"], "strength": 3}]}
    f["facts"]["unit"] = "open roles"
    t = template_company("Anthropic", f)
    assert "673" in t["lede"] and "Washington" in t["lede"] and "Austin" in t["watch"]
    assert template_brief({"Anthropic": f})["bullets"][0].startswith("Anthropic")


@pytest.mark.skipif(not STORY.exists(), reason="run src.insights.story first")
def test_story_json_contract():
    s = json.loads(STORY.read_text(encoding="utf-8"))
    assert s["brief"]["headline"] and s["brief"]["paragraph"]
    for co in ["Anthropic", "OpenAI", "NVIDIA", "Google"]:
        ch = s["chapters"][co]
        assert ch["text"]["headline"] and ch["text"]["lede"] and ch["written_by"]
        for c in ch["claims"]:
            assert c["confidence"] in {"confirmed", "likely", "watch"}
            assert c["id"] in ch["text"]["claims"] and c["key_fact"] and c["examples"]
            assert (c["confidence"] == "confirmed") == bool(c["corroboration"])
        if not ch["written_by"].startswith("template"):  # published LLM prose passed the number check
            facts = {"facts": ch["facts"], "claims": ch["claims"], "new_cities": [e["summary"] for e in ch["expansions"]]}
            text = " ".join([ch["text"]["headline"], ch["text"]["lede"], ch["text"]["watch"]]
                            + [v["title"] + " " + v["reading"] for v in ch["text"]["claims"].values()])
            assert unsupported_numbers(text, facts) == []
