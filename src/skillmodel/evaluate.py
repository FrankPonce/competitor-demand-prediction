"""Span-level evaluation for skill extraction (Sprint 11).

Two matching modes:
- exact:   a predicted span counts only with the same start and end as a gold span
- overlap: a predicted span counts if it overlaps a gold span (one-to-one, greedy), forgiving boundary choices
           such as "Python" vs "Python programming"

Two gold views:
- verified: the gold set exactly as verified by the project owner (primary)
- strict:   the same, minus owner-added spans that the written guidelines exclude (listed below with reasons),
            to show that conclusions do not hinge on that labelling choice
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "skillmodel"

# (span text, sentence fragment, reason): owner additions that docs/skill-labelling-guidelines.md excludes
STRICT_EXCLUDE = [
    ("fleet", "infrastructure, fleet, compute", "team name"),
    ("Claude", "whether Claude sits inside", "product as context"),
    ("life sciences", "life sciences and biotech startups", "customer segment"),
    ("biotech", "life sciences and biotech startups", "customer segment"),
    ("Web Ranking", "Partner closely with Web Ranking", "team name"),
    ("Serving Infrastructure", "Serving Infrastructure, and Large", "team name"),
    ("Large Language Model", "Large Language Model (LLM) Modeling teams", "team name"),
    ("API discovery", "developer journey, including API discovery", "product feature"),
    ("SDK onboarding", "SDK onboarding, credential setup", "product feature"),
    ("credential setup", "SDK onboarding, credential setup", "product feature"),
    ("usage guidance", "and usage guidance", "product feature"),
    ("Computer Science", "BS/MS/PhD in Computer Science", "degree"),
    ("Electrical Engineering", "BS/MS/PhD in Computer Science", "degree"),
    ("Applied Mathematics", "BS/MS/PhD in Computer Science", "degree"),
    ("analytics", "team of analytics engineer", "job title"),
    ("analytics", "first analytics engineers", "job title"),
    ("Agent Development", "customers, Sales, and Agent Development", "team name"),
    ("crawling", "crawling, data quality, and acquisition teams", "team name"),
    ("data quality", "crawling, data quality, and acquisition teams", "team name"),
]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open(encoding="utf-8")]


def gold(view: str = "verified") -> dict[str, dict]:
    rows = {r["id"]: r for r in load_jsonl(D / "gold.jsonl")}
    if view == "strict":
        for r in rows.values():
            keep = []
            for s in r["spans"]:
                drop = any(s["text"] == t and frag in r["text"] for t, frag, _ in STRICT_EXCLUDE)
                if not drop:
                    keep.append(s)
            r["spans"] = keep
    return rows


def _pairs(spans: list[dict]) -> list[tuple[int, int]]:
    return sorted({(int(s["start"]), int(s["end"])) for s in spans})


def score(gold_rows: dict[str, dict], pred: dict[str, list[dict]], mode: str = "exact") -> dict:
    tp = fp = fn = 0
    for sid, g in gold_rows.items():
        gs, ps = _pairs(g["spans"]), _pairs(pred.get(sid, []))
        if mode == "exact":
            hit = len(set(gs) & set(ps))
        else:
            used, hit = set(), 0
            for p in ps:
                for k, q in enumerate(gs):
                    if k not in used and p[0] < q[1] and q[0] < p[1]:
                        used.add(k)
                        hit += 1
                        break
        tp += hit
        fp += len(ps) - hit
        fn += len(gs) - hit
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3), "tp": tp, "fp": fp, "fn": fn}


def rule_predictions() -> dict[str, list[dict]]:
    return {r["id"]: r["rule_spans"] for r in load_jsonl(D / "gold_candidates.jsonl")}


def llm_predictions(model: str = "gpt-oss-120b") -> dict[str, list[dict]]:
    return {r["id"]: r["spans"] for r in load_jsonl(D / f"gold_candidates.llm.{model}.jsonl")}
