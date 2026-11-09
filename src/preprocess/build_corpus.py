"""Sprint 3: build the cleaned, preprocessed corpus for all four companies.

Usage (repo root):
    python -m src.preprocess.build_corpus

Inputs   data/processed/{anthropic,openai,nvidia,google}.csv  (live snapshots, merged)
         data/processed/epoch_history.csv                      (Anthropic + OpenAI history)
Outputs  data/processed/corpus/<company>.csv  cleaned corpus, committed (see corpus_io.py)
         data/processed/corpus.parquet        same + raw text, local cache (gitignored)
         data/processed/corpus_sample.csv     50 rows per company, for browsing on GitHub
         reports/preprocessing/summary.md     generated stats + before/after examples

Pipeline per posting:
    1. merge live + Epoch history (dedupe on job_id, keep earliest first_seen)
    2. normalise unicode / quotes / bullets / whitespace, strip URLs
    3. split into sections via company heading styles (sections.py)
    4. drop boilerplate: the company/legal/pay sections, plus sentences templated across
       many postings of the same company (data-driven, per company)
    5. extract salary min/max (USD) from text where no structured field exists
    6. tokenise + lemmatise with spaCy, removing stop words, punctuation, numbers;
       tech terms like C++, C#, CI/CD are protected
    7. flag non-English postings by English stop-word share
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from .clean import (
    doc_tokens,
    drop_boilerplate,
    extract_salary,
    frequent_sentences,
    language_label,
    load_nlp,
    normalize,
)
from .sections import split_sections
from .corpus_io import save_corpus
from src.style import colorize_markdown

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "preprocessing" / "summary.md"
LIVE = ["anthropic", "openai", "nvidia", "google"]
KEPT_SECTIONS = ["intro", "about", "responsibilities", "requirements", "preferred"]
URL_TEMPLATE = {
    "Anthropic": "https://job-boards.greenhouse.io/anthropic/jobs/{}",
    "OpenAI": "https://jobs.ashbyhq.com/openai/{}",
}


def load_merged() -> pd.DataFrame:
    live = pd.concat([pd.read_csv(PROC / f"{c}.csv", dtype=str, keep_default_na=False) for c in LIVE],
                     ignore_index=True)
    live["in_live"] = True
    epoch = pd.read_csv(PROC / "epoch_history.csv", dtype=str, keep_default_na=False)
    epoch["in_epoch"] = True

    e = epoch.set_index("job_id")
    live["in_epoch"] = live["job_id"].isin(e.index)
    overlap = live["in_epoch"]
    ids = live.loc[overlap, "job_id"]
    live.loc[overlap, "first_seen_date"] = [
        min(a, b) for a, b in zip(live.loc[overlap, "first_seen_date"], e.loc[ids, "first_seen_date"])
    ]
    live["job_category"] = live["job_id"].map(e["job_category"]).fillna("")

    only = epoch[~epoch["job_id"].isin(live["job_id"])].copy()
    only["in_live"] = False
    # Anthropic/OpenAI live snapshots are full boards: anything not in them has closed.
    only["job_status"] = "closed"
    only["job_url"] = [
        URL_TEMPLATE[c].format(j.split("-", 1)[1]) for c, j in zip(only["company_name"], only["job_id"])
    ]
    df = pd.concat([live, only], ignore_index=True).fillna("")
    for col in ["in_live", "in_epoch"]:
        df[col] = df[col].astype(bool)
    return df


def process(df: pd.DataFrame) -> pd.DataFrame:
    df["text_norm"] = df["job_description"].map(normalize)
    secs = df["text_norm"].map(split_sections).apply(pd.Series)
    df = pd.concat([df, secs.add_prefix("section_")], axis=1)

    for company, idx in df.groupby("company_name").groups.items():
        freq = frequent_sentences(df.loc[idx, "text_norm"].tolist())
        for sec in KEPT_SECTIONS:
            col = f"section_{sec}"
            strict = sec in ("intro", "about")
            df.loc[idx, col] = [drop_boilerplate(t, freq, company, strict) for t in df.loc[idx, col]]

    sal = [extract_salary(r, t) for r, t in zip(df["salary_range"], df["text_norm"])]
    df["salary_min"] = [a for a, _ in sal]
    df["salary_max"] = [b for _, b in sal]

    df["clean_text"] = df[[f"section_{s}" for s in KEPT_SECTIONS]].apply(
        lambda r: "\n\n".join(x for x in r if x), axis=1
    )

    nlp = load_nlp()
    toks, langs = [], []
    texts = df["clean_text"].tolist()
    for text, doc in zip(texts, nlp.pipe(texts, batch_size=64)):
        t, en_share, foreign_share = doc_tokens(doc)
        toks.append(t)
        langs.append(language_label(text, en_share, foreign_share))
    df["cleaned_description"] = toks
    df["language"] = langs

    df["n_chars_raw"] = df["job_description"].str.len()
    df["n_chars_clean"] = df["clean_text"].str.len()
    df["n_tokens"] = df["cleaned_description"].str.split().str.len().fillna(0).astype(int)
    df["has_responsibilities"] = df["section_responsibilities"].str.len() > 0
    df["has_requirements"] = df["section_requirements"].str.len() > 0
    return df.drop(columns=["text_norm", "section_boilerplate"])


COLUMNS = [
    "job_id", "company_name", "job_title", "posting_date", "first_seen_date", "last_seen_date",
    "job_status", "location", "job_url", "employment_type", "department", "job_category", "remote_type",
    "salary_range", "salary_min", "salary_max", "source_name", "in_live", "in_epoch", "language",
    "section_intro", "section_about", "section_responsibilities", "section_requirements",
    "section_preferred", "clean_text", "cleaned_description", "n_chars_raw", "n_chars_clean",
    "n_tokens", "has_responsibilities", "has_requirements", "job_description",
]


def write_report(df: pd.DataFrame, seconds: float) -> None:
    g = df.groupby("company_name")
    t = pd.DataFrame({
        "postings": g.size(),
        "live": g["in_live"].sum(),
        "history only": (~df["in_live"]).groupby(df["company_name"]).sum(),
        "median chars raw": g["n_chars_raw"].median().astype(int),
        "median chars clean": g["n_chars_clean"].median().astype(int),
        "text removed": (1 - g["n_chars_clean"].sum() / g["n_chars_raw"].sum()).map("{:.0%}".format),
        "median tokens": g["n_tokens"].median().astype(int),
        "has responsibilities": g["has_responsibilities"].mean().map("{:.0%}".format),
        "has requirements": g["has_requirements"].mean().map("{:.0%}".format),
        "has salary": g["salary_min"].apply(lambda s: s.notna().mean()).map("{:.0%}".format),
        "mixed language": (df["language"] == "mixed").groupby(df["company_name"]).sum(),
        "non-English": (df["language"] == "other").groupby(df["company_name"]).sum(),
    })
    lines = [
        "# Preprocessing Summary (generated)",
        "",
        f"Generated by `python -m src.preprocess.build_corpus` in {seconds:.0f}s · "
        f"**{len(df):,} unique postings** · see [Sprint 3](../../docs/sprints/sprint-03-nlp-preprocessing.md)",
        "",
        "## Per company",
        "",
        t.reset_index().rename(columns={"company_name": "company"}).to_markdown(index=False),
        "",
        "*text removed* = share of raw characters dropped as boilerplate (company blurbs, legal, pay, logistics).",
        "",
        "## Before / after examples",
        "",
    ]
    for company, sub in g:
        row = sub[sub["in_live"]].iloc[0] if sub["in_live"].any() else sub.iloc[0]
        lines += [
            f"### {company}: {row['job_title']}",
            "",
            f"Raw: {row['n_chars_raw']:,} chars → clean: {row['n_chars_clean']:,} chars → "
            f"{row['n_tokens']:,} tokens",
            "",
            "**Requirements section (clean):**",
            "",
            "> " + (row["section_requirements"][:500] or "_none detected_").replace("\n", "\n> "),
            "",
            "**`cleaned_description` (first 40 tokens):**",
            "",
            "`" + " ".join(row["cleaned_description"].split()[:40]) + "`",
            "",
        ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(colorize_markdown("\n".join(lines)), encoding="utf-8")


def main() -> None:
    t0 = time.time()
    df = process(load_merged())[COLUMNS]
    save_corpus(df)
    sample = df.groupby("company_name", group_keys=False).apply(lambda s: s.head(50))
    sample.drop(columns=["job_description"]).to_csv(PROC / "corpus_sample.csv", index=False)
    write_report(df, time.time() - t0)
    print(f"corpus: {len(df):,} postings -> data/processed/corpus/ + corpus.parquet cache ({time.time() - t0:.0f}s)")
    print(df.groupby("company_name").size().to_string())


if __name__ == "__main__":
    main()
