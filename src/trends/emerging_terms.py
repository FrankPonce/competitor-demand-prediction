"""Data-driven emerging terms: what's rising in job postings, including things the taxonomy doesn't know.

Method
    Documents   role text (responsibilities + requirements + preferred) of NEW postings at
                Anthropic and OpenAI (the companies with weekly history)
    Periods     early = first 13 weeks after Epoch start; recent = last 13 complete weeks
    Features    1-3 word phrases (binary per posting), min document frequency 8
    Statistic   weighted log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi & Quinn
                2008, "Fightin' Words"). It reports a z-score that is robust for rare terms, unlike raw
                % change.
    Novelty     each term is checked against the Sprint 4 taxonomy; `in_taxonomy = False` means the
                rule-based extractor could never have found it.

Usage:  python -m src.trends.emerging_terms
Output: data/trends/emerging_terms.csv, reports/trends/figures/emerging_terms.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer  # noqa: E402

from src.features.extract import match_skills  # noqa: E402
from src.preprocess.corpus_io import load_corpus  # noqa: E402
from src.style import THEME, apply_matplotlib, footnote  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "trends" / "emerging_terms.csv"
FIG = ROOT / "reports" / "trends" / "figures" / "emerging_terms.png"
EPOCH_START = pd.Timestamp("2026-03-18")
apply_matplotlib()

# Generic job-ad vocabulary that rises and falls with writing style, not with demand.
GENERIC = set(ENGLISH_STOP_WORDS) | {
    "team", "teams", "work", "working", "role", "experience", "ability", "strong", "help", "build", "building",
    "including", "new", "across", "ensure", "drive", "support", "years", "skills", "using", "deep", "high",
    "like", "make", "ll", "ve", "re", "able", "time", "best", "great", "well", "way", "ways", "need", "want",
    "join", "looking", "company", "companies", "openai", "anthropic", "claude", "chatgpt", "people", "partner",
    "partners", "closely", "complex", "clear", "key", "level", "related", "relevant", "similar", "things",
}
TOKEN = r"(?u)\b[A-Za-z][A-Za-z0-9+#./-]*[A-Za-z0-9+#]\b"


def periods(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = df[df.company_name.isin(["Anthropic", "OpenAI"])].copy()
    d["first_seen"] = pd.to_datetime(d.first_seen_date)
    d = d[d.first_seen > EPOCH_START]
    latest = d.first_seen.max()
    early = d[d.first_seen < EPOCH_START + pd.Timedelta(weeks=13)]
    recent = d[d.first_seen >= latest - pd.Timedelta(weeks=13)]
    return early, recent


def role_text(d: pd.DataFrame) -> pd.Series:
    return (d.section_responsibilities.fillna("") + "\n" + d.section_requirements.fillna("") + "\n"
            + d.section_preferred.fillna(""))


def fightin_words(ya, yb, na, nb, alpha0=500.0) -> np.ndarray:
    pooled = (ya + yb) / (na + nb)
    a = alpha0 * pooled + 0.01
    la = np.log((ya + a) / (na + alpha0 - ya - a))
    lb = np.log((yb + a) / (nb + alpha0 - yb - a))
    return (la - lb) / np.sqrt(1 / (ya + a) + 1 / (yb + a))


def informative(term: str) -> bool:
    words = term.split()
    return not all(w in GENERIC for w in words) and words[0] not in GENERIC and words[-1] not in GENERIC


def term_matrix(texts: pd.Series) -> tuple[list[str], "np.ndarray"]:
    """Phrases (2-3 words, lower-cased) + name-like single tokens (case-preserved)."""
    from scipy.sparse import hstack

    phr = CountVectorizer(ngram_range=(2, 3), min_df=8, binary=True, token_pattern=TOKEN, lowercase=True)
    Xp = phr.fit_transform(texts)
    uni = CountVectorizer(ngram_range=(1, 1), min_df=8, binary=True, token_pattern=TOKEN, lowercase=False)
    Xu = uni.fit_transform(texts)
    words = uni.get_feature_names_out()
    totals = np.asarray(Xu.sum(axis=0)).ravel()
    by_lower: dict[str, float] = {}
    for w, n in zip(words, totals):
        by_lower[w.lower()] = by_lower.get(w.lower(), 0) + n
    name_like = [i for i, w in enumerate(words)
                 if (any(ch.isdigit() or ch in "+#./" for ch in w) and any(ch.isalpha() for ch in w))
                 or (w[0].isupper() and w.lower() not in GENERIC and totals[i] / by_lower[w.lower()] >= 0.8)]
    X = hstack([Xp, Xu[:, name_like]]).tocsr()
    return list(phr.get_feature_names_out()) + [words[i] for i in name_like], X


# Analyst curation (2026-11-09): rising terms from the top of the ranked list (z ≥ 2, ≥ 10 recent postings)
# that are NOT in the taxonomy, grouped into themes. Style phrases ("exercise sound judgment") are excluded.
# The full ranking is in emerging_terms.csv.
THEMES = {
    "Government & national security": ["TS/SCI", "CISA", "research security"],
    "Deploying AI at customers": ["customer sites", "sustained adoption", "relationships with customers",
                                  "critical escalation", "production incidents", "api failures"],
    "New segments & regions": ["SMB", "DACH", "LLB", "local needs", "enterprise deals"],
    "AI fluency in every role": ["ai tools", "common llm frameworks", "applied ai"],
    "Physical build-out": ["electrical mechanical"],
}


def plot_themes(t: pd.DataFrame, ne: int, nr: int) -> None:
    rows = []
    for theme, terms in THEMES.items():
        for term in terms:
            m = t[t.term == term]
            if len(m):
                rows.append((theme, term, float(m.early_share.iloc[0]), float(m.recent_share.iloc[0]),
                             int(m.early_postings.iloc[0]), int(m.recent_postings.iloc[0])))
    fig, ax = plt.subplots(figsize=(10, 0.36 * (len(rows) + 2 * len(THEMES)) + 1.2))
    y, yticks, ylabels, last = 0, [], [], None
    for theme, term, e, r, ne_, nr_ in rows:
        if theme != last:
            y += 0.6
            ax.text(0, y, theme.upper(), fontsize=8.5, fontweight="bold", color=THEME["text2"], va="center",
                    transform=ax.get_yaxis_transform())
            y += 0.9
            last = theme
        ax.plot([e, r], [y, y], color=THEME["axis"], linewidth=2.5, zorder=1)
        ax.scatter([e], [y], s=40, color=THEME["muted"], zorder=2)
        ax.scatter([r], [y], s=70, color=THEME["text"], zorder=3)
        ax.annotate(f"{ne_} → {nr_} postings", (r, y), xytext=(8, 0), textcoords="offset points", va="center",
                    fontsize=8, color=THEME["text2"])
        yticks.append(y)
        ylabels.append(term)
        y += 1
    ax.set_yticks(yticks, ylabels)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("share of new postings mentioning the term  (grey = first 13 weeks, white = last 13 weeks)")
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.22)
    ax.set_title("Emerging signals the skill taxonomy missed (Anthropic + OpenAI)")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, f"Early n={ne:,} · recent n={nr:,} new postings · ranked with Fightin' Words log-odds "
                  "(Monroe et al. 2008), themes curated")
    fig.savefig(FIG)
    plt.close(fig)


def main() -> None:
    df = load_corpus()
    early, recent = periods(df)
    terms, X = term_matrix(pd.concat([role_text(early), role_text(recent)]))
    ne, nr = len(early), len(recent)
    ye = np.asarray(X[:ne].sum(axis=0)).ravel()
    yr = np.asarray(X[ne:].sum(axis=0)).ravel()
    z = fightin_words(yr, ye, nr, ne)
    t = pd.DataFrame({"term": terms, "early_postings": ye, "recent_postings": yr,
                      "early_share": ye / ne, "recent_share": yr / nr, "z": z})
    t = t[t.term.map(informative)]
    # drop sub-phrases that are just part of a stronger longer phrase with similar support
    t = t.sort_values("z", ascending=False)
    keep, seen = [], []
    for r in t.itertuples():
        if any(r.term in s and abs(r.recent_postings - rp) <= 0.25 * rp for s, rp in seen):
            continue
        keep.append(r.Index)
        seen.append((r.term, r.recent_postings))
    t = t.loc[keep]
    t["in_taxonomy"] = t.term.map(lambda s: bool(match_skills({"x": s})))
    t["direction"] = np.where(t.z > 0, "rising", "falling")
    t["change_pp"] = ((t.recent_share - t.early_share) * 100).round(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.round(4).to_csv(OUT, index=False)

    top = t[(t.z >= 3) & (t.recent_postings >= 15)].head(60)
    plot_themes(t, ne, nr)
    print(f"early {ne} / recent {nr} postings, {len(t):,} terms")
    print("rising, not in taxonomy:", ", ".join(top[~top.in_taxonomy].head(15).term))
    print("rising, in taxonomy:", ", ".join(top[top.in_taxonomy].head(10).term))
    print("falling:", ", ".join(t.sort_values("z").head(12).term))


if __name__ == "__main__":
    main()
