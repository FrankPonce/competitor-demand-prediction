"""Sentence dataset for skill-span extraction, with rule-based (Sprint 4) spans.

Postings are split 90/10 by a stable hash of job_id, so no posting contributes to both training and the gold test
set. Sentences come from the requirements, preferred and responsibilities sections.

Run: python -m src.skillmodel.data
Out: data/skillmodel/gold_candidates.jsonl  (200 held-out sentences, rule spans attached, to be pre-labelled + verified)
     data/skillmodel/train_pool.jsonl       (training sentences with rule spans)
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from src.features.extract import SKILLS
from src.preprocess.corpus_io import load_corpus

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "skillmodel"
SECTIONS = {"requirements": "section_requirements", "preferred": "section_preferred",
            "responsibilities": "section_responsibilities"}
FOCUS = ["Anthropic", "OpenAI", "NVIDIA", "Google"]
GOLD_PER_GROUP = 40          # Anthropic, OpenAI, NVIDIA, Google, peers -> 200 gold sentences
TRAIN_SIZE = 3000
SEED = 11


def is_test(job_id: str) -> bool:
    return int(hashlib.sha1(str(job_id).encode()).hexdigest(), 16) % 10 == 0


def split_sentences(text: str) -> list[str]:
    out = []
    for line in str(text).split("\n"):
        line = re.sub(r"^[\s•\-–*·▪●◦]+", "", line).strip()
        for s in re.split(r"(?<=[.;!?])\s+(?=[A-Z(])", line):
            s = s.strip()
            if 6 <= len(s.split()) <= 50:
                out.append(s)
    return out


def rule_spans(text: str) -> list[dict]:
    """Sprint 4 taxonomy matches as character spans; overlaps resolved in favour of the longer span."""
    cands = []
    for sk in SKILLS:
        for p in sk.patterns:
            for m in p.finditer(text):
                if m.end() > m.start():
                    cands.append((m.start(), m.end(), sk.name))
    cands.sort(key=lambda x: (-(x[1] - x[0]), x[0]))
    chosen = []
    for s, e, name in cands:
        if all(e <= cs or s >= ce for cs, ce, _ in chosen):
            chosen.append((s, e, name))
    return [{"start": s, "end": e, "text": text[s:e], "skill": name} for s, e, name in sorted(chosen)]


def sentences() -> pd.DataFrame:
    c = load_corpus()
    feats = pd.read_parquet(ROOT / "data" / "features" / "posting_features.parquet",
                            columns=["job_id", "company_name", "role_family"])
    c = c.merge(feats, on=["job_id", "company_name"], how="left")
    rows = []
    for r in c.itertuples():
        for sec, col in SECTIONS.items():
            for s in split_sentences(getattr(r, col) or ""):
                rows.append({"job_id": r.job_id, "company": r.company_name, "role_family": r.role_family,
                             "section": sec, "text": s})
    df = pd.DataFrame(rows)
    df["norm"] = df.text.str.lower().str.replace(r"\W+", " ", regex=True).str.strip()
    df = df.drop_duplicates("norm")  # boilerplate repeated across postings counts once
    df["test"] = df.job_id.map(is_test)
    df["group"] = df.company.where(df.company.isin(FOCUS), "Peers")
    return df


def sample_gold(df: pd.DataFrame) -> pd.DataFrame:
    pool = df[df.test].sample(frac=1, random_state=SEED).drop_duplicates("job_id")  # one sentence per posting
    parts = []
    for g, gdf in pool.groupby("group"):
        # spread over role families: round-robin through families in random order
        gdf = gdf.assign(rank=gdf.groupby("role_family").cumcount()).sort_values(["rank", "role_family"])
        parts.append(gdf.head(GOLD_PER_GROUP))
    return pd.concat(parts).drop(columns="rank")


def sample_train(df: pd.DataFrame) -> pd.DataFrame:
    pool = df[~df.test]
    w = pool.group.map({"Peers": 1.0}).fillna(1.0)
    per_group = TRAIN_SIZE // pool.group.nunique()
    return pd.concat(g.sample(min(len(g), per_group), random_state=SEED) for _, g in pool.groupby("group"))


def write(df: pd.DataFrame, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(df.itertuples()):
            f.write(json.dumps({"id": f"{path.stem}-{i:04d}", "job_id": r.job_id, "company": r.company,
                                "role_family": r.role_family, "section": r.section, "text": r.text,
                                "rule_spans": rule_spans(r.text)}, ensure_ascii=False) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = sentences()
    gold, train = sample_gold(df), sample_train(df)
    assert not set(gold.job_id) & set(train.job_id), "gold and train must not share postings"
    write(gold, OUT / "gold_candidates.jsonl")
    write(train, OUT / "train_pool.jsonl")
    print(f"sentences: {len(df):,} unique ({df.test.sum():,} in held-out postings)")
    print(f"gold: {len(gold)} · {gold.group.value_counts().to_dict()} · {gold.role_family.nunique()} role families")
    print(f"train: {len(train)} · {train.group.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
