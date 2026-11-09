"""Load / save the cleaned corpus.

Storage split (keeps the git history small):
    data/processed/corpus/<company>.csv   committed. Cleaned fields only (sections, lemmas, metadata).
                                          Text CSVs delta-compress well in git (~1 MB per weekly change).
    data/processed/corpus.parquet         local cache (gitignored). Full corpus incl. raw text and
                                          clean_text, rebuilt from the CSVs + raw sources if missing.

Downstream code calls `load_corpus()` and never cares which one exists.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
CACHE = PROC / "corpus.parquet"
CSV_DIR = PROC / "corpus"
KEPT_SECTIONS = ["intro", "about", "responsibilities", "requirements", "preferred"]
# Derivable columns that are not stored in the committed CSVs.
NOT_IN_CSV = ["clean_text", "job_description"]


def clean_text_from_sections(df: pd.DataFrame) -> pd.Series:
    cols = [f"section_{s}" for s in KEPT_SECTIONS]
    return df[cols].fillna("").apply(lambda r: "\n\n".join(x for x in r if x), axis=1)


def save_corpus(df: pd.DataFrame) -> None:
    df.to_parquet(CACHE, index=False)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    for company, sub in df.groupby("company_name"):
        sub.drop(columns=NOT_IN_CSV).to_csv(CSV_DIR / f"{company.lower()}.csv", index=False)


def _raw_descriptions() -> pd.Series:
    """job_id -> original description, from the committed per-company and Epoch files."""
    parts = []
    # live per-company files first (they win on duplicates, as in build_corpus), Epoch history last
    files = sorted(f for f in PROC.glob("*.csv") if f.name not in ("corpus_sample.csv", "epoch_history.csv"))
    for f in files + [PROC / "epoch_history.csv"]:
        d = pd.read_csv(f, usecols=["job_id", "job_description"], dtype=str, keep_default_na=False)
        parts.append(d)
    s = pd.concat(parts).drop_duplicates("job_id", keep="first").set_index("job_id")["job_description"]
    return s


def load_corpus() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    files = sorted(CSV_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError("No corpus found: run `python -m src.preprocess.build_corpus` first.")
    df = pd.concat([pd.read_csv(f, keep_default_na=False, low_memory=False) for f in files], ignore_index=True)
    for col in ["salary_min", "salary_max"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["in_live", "in_epoch", "has_responsibilities", "has_requirements"]:
        df[col] = df[col].astype(str).str.lower().eq("true")
    for col in ["n_chars_raw", "n_chars_clean", "n_tokens"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["clean_text"] = clean_text_from_sections(df)
    df["job_description"] = df["job_id"].map(_raw_descriptions()).fillna("")
    df.to_parquet(CACHE, index=False)  # warm the cache
    return df
