"""Sprint 8: company similarity scoring across the AI market (4 focus companies + 13 peers).

Usage:  python -m src.similarity.build_similarity

Population: postings open in the latest snapshot. Technical roles (ML/AI, research, software, infra,
hardware, data, security) for content measures; all roles for role mix and talent pools.

Measures (each in [0, 1], higher = more similar)
    skills      cosine of skill-share vectors (share of technical postings mentioning each taxonomy skill)
    role_mix    1 - Jensen-Shannon distance between role-family distributions (all roles)
    tfidf       cosine of TF-IDF centroids of technical postings (lemmatised text, 1-2 grams)
    embedding   cosine of Sentence-BERT (all-MiniLM-L6-v2) centroids of technical postings
    talent      overlap of talent pools: k-means clusters over embeddings of ALL postings;
                overlap = sum over clusters of min(share_a, share_b) (histogram intersection)
    combined    mean of the five after min-max scaling each across company pairs

Outputs: data/similarity/*.csv, reports/similarity/figures/*.png, reports/similarity/summary.md
         data/similarity/embeddings.parquet (cache, gitignored)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from scipy.cluster.hierarchy import leaves_list, linkage  # noqa: E402
from scipy.spatial.distance import jensenshannon, squareform  # noqa: E402
from sklearn.cluster import KMeans  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.preprocessing import normalize  # noqa: E402

from src.collect.peers import segment  # noqa: E402
from src.preprocess.corpus_io import load_corpus  # noqa: E402
from src.style import COMPANIES, COMPANY_COLOR, THEME, apply_matplotlib, colorize_markdown, footnote  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "similarity"
REP = ROOT / "reports" / "similarity"
FIG = REP / "figures"
EMB_CACHE = OUT / "embeddings.parquet"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TECH = {"ML / AI Engineering", "Research", "Software Engineering", "Infrastructure & SRE", "Hardware & Silicon",
        "Data & Analytics", "Security & Privacy"}
K_POOLS = 24
apply_matplotlib()
PEER_GREY = "#8b949e"


def color(c: str) -> str:
    return COMPANY_COLOR.get(c, PEER_GREY)


# ---------------------------------------------------------------- data


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    corpus = load_corpus()
    feat = pd.read_parquet(ROOT / "data" / "features" / "posting_features.parquet")[
        ["job_id", "role_family", "seniority_level"]]
    d = corpus.merge(feat, on="job_id", how="left")
    d = d[d.in_live & (d.job_status == "active")].reset_index(drop=True)
    d["tech"] = d.role_family.isin(TECH)
    long = pd.read_csv(ROOT / "data" / "features" / "skills_long.csv")
    return d, long[long.job_id.isin(d.job_id)]


def embed(d: pd.DataFrame) -> np.ndarray:
    cache = pd.read_parquet(EMB_CACHE) if EMB_CACHE.exists() else pd.DataFrame(columns=["job_id"])
    have = set(cache.job_id)
    todo = d[~d.job_id.isin(have)]
    if len(todo):
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL, device="cpu")
        text = (todo.job_title.fillna("") + ". " + (todo.section_responsibilities.fillna("") + " "
                + todo.section_requirements.fillna("")).str.slice(0, 1500)).tolist()
        vecs = model.encode(text, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
        new = pd.DataFrame(vecs.astype("float16"), columns=[f"e{i}" for i in range(vecs.shape[1])])
        new.insert(0, "job_id", todo.job_id.values)
        cache = pd.concat([cache, new], ignore_index=True)
        OUT.mkdir(parents=True, exist_ok=True)
        cache.to_parquet(EMB_CACHE, index=False)
    m = cache.set_index("job_id").loc[d.job_id].to_numpy(dtype="float32")
    return normalize(m)


# ---------------------------------------------------------------- measures


def cosine_matrix(vectors: dict[str, np.ndarray]) -> pd.DataFrame:
    names = list(vectors)
    M = normalize(np.vstack([vectors[n] for n in names]))
    return pd.DataFrame(M @ M.T, index=names, columns=names)


def skills_measure(d, long, companies):
    t = d[d.tech]
    lt = long[long.job_id.isin(t.job_id)]
    n = t.groupby("company_name").size()
    sh = lt.groupby(["company_name", "skill"]).job_id.nunique().unstack(fill_value=0).div(n, axis=0).fillna(0)
    return cosine_matrix({c: sh.loc[c].to_numpy() for c in companies}), sh


def role_mix_measure(d, companies):
    mix = pd.crosstab(d.company_name, d.role_family, normalize="index")
    names = companies
    S = np.array([[1 - jensenshannon(mix.loc[a], mix.loc[b], base=2) for b in names] for a in names])
    return pd.DataFrame(S, index=names, columns=names)


def tfidf_measure(d, companies):
    t = d[d.tech]
    X = TfidfVectorizer(ngram_range=(1, 2), min_df=5, max_df=0.6, sublinear_tf=True).fit_transform(
        t.cleaned_description.fillna(""))
    X = normalize(X)
    cent = {c: np.asarray(X[(t.company_name == c).to_numpy()].mean(axis=0)).ravel() for c in companies}
    return cosine_matrix(cent)


def embedding_measure(d, E, companies):
    mask = d.tech.to_numpy()
    cent = {c: E[mask & (d.company_name == c).to_numpy()].mean(axis=0) for c in companies}
    return cosine_matrix(cent)


def talent_pools(d, E, companies, k=K_POOLS):
    km = KMeans(n_clusters=k, n_init=10, random_state=7).fit(E)
    d = d.assign(pool=km.labels_)
    # name each pool by its dominant role family + most frequent title words
    names = {}
    for p, g in d.groupby("pool"):
        fam = g.role_family.value_counts().index[0]
        words = (g.job_title.str.lower().str.replace(r"[^a-z ]", " ", regex=True).str.split().explode())
        words = words[~words.isin({"senior", "staff", "lead", "principal", "engineer", "manager", "and", "of",
                                   "the", "sr", "ii", "iii", "for", "to", "in", "a", "head", "director"})
                      & (words.str.len() > 2)]
        top = " / ".join(words.value_counts().head(2).index)
        names[p] = f"{fam}: {top}"
    share = pd.crosstab(d.pool, d.company_name, normalize="columns")[companies]
    share.index = [names[i] for i in share.index]
    S = np.array([[np.minimum(share[a], share[b]).sum() for b in companies] for a in companies])
    return pd.DataFrame(S, index=companies, columns=companies), share, d[["job_id", "company_name", "pool"]].assign(
        pool_name=d.pool.map(names))


def minmax_offdiag(S: pd.DataFrame) -> pd.DataFrame:
    v = S.to_numpy().copy()
    off = ~np.eye(len(v), dtype=bool)
    lo, hi = v[off].min(), v[off].max()
    out = (v - lo) / (hi - lo) if hi > lo else v * 0
    np.fill_diagonal(out, 1.0)
    return pd.DataFrame(out, index=S.index, columns=S.columns)


# ---------------------------------------------------------------- charts


def fig_heatmap(S: pd.DataFrame, sizes: pd.Series) -> list[str]:
    Z = linkage(squareform(1 - S.to_numpy(), checks=False), method="average")
    order = [S.index[i] for i in leaves_list(Z)]
    S = S.loc[order, order]
    cmap = LinearSegmentedColormap.from_list("seq", [THEME["panel"], "#1f3b57", "#2f6a9e", "#58a6ff", "#cae8ff"])
    fig, ax = plt.subplots(figsize=(11.5, 10))
    vals = S.to_numpy().copy()
    np.fill_diagonal(vals, np.nan)
    ax.imshow(vals, cmap=cmap, vmin=0, vmax=1)
    ax.set_xticks(range(len(order)), order, rotation=55, ha="right")
    ax.set_yticks(range(len(order)), [f"{c} ({sizes[c]:,})" for c in order])
    for lab, c in list(zip(ax.get_xticklabels(), order)) + list(zip(ax.get_yticklabels(), order)):
        lab.set_color(color(c))
        lab.set_fontweight("bold" if c in COMPANY_COLOR else "normal")
    for i in range(len(order)):
        for j in range(len(order)):
            if i != j:
                v = S.iat[i, j]
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                        color=THEME["surface"] if v > 0.62 else THEME["text2"])
    ax.grid(False)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Company similarity (combined score, clustered): who hires like whom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    footnote(fig, "Mean of 5 min-max-scaled measures: skills, role mix, TF-IDF, Sentence-BERT, talent-pool overlap · "
                  "open postings 2026-11-10 · (n) = open postings")
    fig.savefig(FIG / "similarity_heatmap.png")
    plt.close(fig)
    return order


def fig_network(S: pd.DataFrame, sizes: pd.Series, k=3) -> None:
    import networkx as nx

    G = nx.Graph()
    for c in S.index:
        G.add_node(c)
        nn = S.loc[c].drop(c).nlargest(k)
        for o, w in nn.items():
            G.add_edge(c, o, weight=float(w))
    pos = nx.spring_layout(G, weight="weight", seed=11, k=0.9, iterations=300)
    fig, ax = plt.subplots(figsize=(12, 8.5))
    for a, b, w in G.edges(data="weight"):
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color=THEME["axis"], linewidth=0.6 + 3.2 * w,
                alpha=0.35 + 0.5 * w, zorder=1)
    seg_marker = {"Frontier lab": "o", "Big tech": "o", "Semiconductors": "o", "Data & AI infrastructure": "s",
                  "AI application": "D", "Robotics": "^"}
    for c in G.nodes:
        x, y = pos[c]
        s = 80 + 30 * np.sqrt(sizes[c])
        ax.scatter([x], [y], s=s, color=color(c), marker=seg_marker.get(segment(c), "o"),
                   edgecolor=THEME["surface"], linewidth=2, zorder=3)
        ax.annotate(c, (x, y), xytext=(0, -(np.sqrt(s) / 2 + 10)), textcoords="offset points", ha="center",
                    va="top", fontsize=9.5,
                    fontweight="bold" if c in COMPANY_COLOR else "normal",
                    color=THEME["text"] if c in COMPANY_COLOR else THEME["text2"], zorder=4)
    for seg, mk in [("Frontier lab / big tech / chips", "o"), ("Data & AI infrastructure", "s"),
                    ("AI application", "D"), ("Robotics", "^")]:
        ax.scatter([], [], marker=mk, color=PEER_GREY, s=60, label=seg)
    ax.legend(loc="lower left", fontsize=8.5, frameon=False)
    ax.axis("off")
    ax.margins(0.08)
    ax.set_title("Similarity network: each company linked to its 3 most similar (thicker = more similar)")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    footnote(fig, "Combined similarity · node size ∝ √open postings · focus companies in colour, peers in grey".replace("∝", "~"))
    fig.savefig(FIG / "similarity_network.png")
    plt.close(fig)


def fig_pools(share: pd.DataFrame, focus_order: list[str]) -> None:
    t = share[focus_order]
    t = t.loc[t.max(axis=1).sort_values(ascending=False).index]  # every company's main pools, not just focus four
    t = t[t.max(axis=1) >= 0.05]
    cmap = LinearSegmentedColormap.from_list("seq", [THEME["panel"], "#1f3b57", "#2f6a9e", "#58a6ff", "#cae8ff"])
    vmax = min(0.6, t.to_numpy().max())
    fig, ax = plt.subplots(figsize=(13, 0.42 * len(t) + 2.6))
    ax.imshow(t.to_numpy(), cmap=cmap, aspect="auto", vmin=0, vmax=vmax)
    ax.set_xticks(range(len(t.columns)), t.columns, rotation=55, ha="right")
    ax.set_yticks(range(len(t.index)), t.index, fontsize=8.5)
    for lab, c in zip(ax.get_xticklabels(), t.columns):
        lab.set_color(color(c))
        lab.set_fontweight("bold" if c in COMPANY_COLOR else "normal")
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = t.iat[i, j]
            if v >= 0.05:
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=7,
                        color=THEME["surface"] if v > 0.55 * vmax else THEME["text"])
    ax.grid(False)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Talent pools: share of each company's open postings per embedding cluster")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    footnote(fig, f"k-means (k={K_POOLS}) on Sentence-BERT embeddings of all open postings · pools named by dominant "
                  "role family + frequent title words")
    fig.savefig(FIG / "talent_pools.png")
    plt.close(fig)


# ---------------------------------------------------------------- main


def drivers(sh: pd.DataFrame, a: str, b: str, n=5) -> tuple[str, str]:
    both = pd.concat([sh.loc[a], sh.loc[b]], axis=1, keys=[a, b]).fillna(0)
    shared = both.min(axis=1).sort_values(ascending=False).head(n)
    diff = (both[a] - both[b])
    lead_a = diff.sort_values(ascending=False).head(3)
    lead_b = diff.sort_values().head(3)
    s = " · ".join(f"{k} ({both.loc[k, a]:.0%}/{both.loc[k, b]:.0%})" for k in shared.index)
    d = (f"{a} more: " + ", ".join(lead_a.index) + f" — {b} more: " + ", ".join(lead_b.index))
    return s, d


def main() -> None:
    for p in (OUT, REP, FIG):
        p.mkdir(parents=True, exist_ok=True)
    d, long = load()
    tech_n = d[d.tech].company_name.value_counts()
    companies = [c for c in d.company_name.value_counts().index if tech_n.get(c, 0) >= 15]
    d = d[d.company_name.isin(companies)].reset_index(drop=True)
    E = embed(d)

    S_sk, sh = skills_measure(d, long, companies)
    S_rm = role_mix_measure(d, companies)
    S_tf = tfidf_measure(d, companies)
    S_em = embedding_measure(d, E, companies)
    S_tp, pools, assign = talent_pools(d, E, companies)
    measures = {"skills": S_sk, "role_mix": S_rm, "tfidf": S_tf, "embedding": S_em, "talent": S_tp}
    S = sum(minmax_offdiag(m) for m in measures.values()) / len(measures)

    # long table of pairs
    rows = []
    for i, a in enumerate(companies):
        for b in companies[i + 1:]:
            rows.append({"a": a, "b": b, **{k: round(float(m.loc[a, b]), 4) for k, m in measures.items()},
                         "combined": round(float(S.loc[a, b]), 4)})
    pairs = pd.DataFrame(rows).sort_values("combined", ascending=False)
    agree = pairs[list(measures)].corr(method="spearman").round(2)
    sizes = d.company_name.value_counts()

    S.round(4).to_csv(OUT / "similarity_combined.csv")
    for k, m in measures.items():
        m.round(4).to_csv(OUT / f"similarity_{k}.csv")
    pairs.to_csv(OUT / "pairs.csv", index=False)
    pools.round(4).to_csv(OUT / "talent_pool_shares.csv")
    assign.to_csv(OUT / "role_clusters.csv", index=False)  # role_cluster_id per posting (brief field)

    order = fig_heatmap(S, sizes)
    fig_network(S, sizes)
    fig_pools(pools, [c for c in order])

    nn = {c: S.loc[c].drop(c).nlargest(3) for c in companies}
    lines = ["# Company Similarity Summary (generated)", "",
             f"Generated by `python -m src.similarity.build_similarity` · {len(companies)} companies · "
             f"{len(d):,} open postings ({int(d.tech.sum()):,} technical) · see "
             "[Sprint 8](../../docs/sprints/sprint-08-similarity-scoring.md)", "",
             "![Heatmap](figures/similarity_heatmap.png)", "", "![Network](figures/similarity_network.png)", "",
             "## Nearest neighbours", "", "| Company | Segment | Open postings | Most similar (combined) |",
             "|---|---|---:|---|"]
    for c in companies:
        lines.append(f"| {c} | {segment(c)} | {sizes[c]:,} | "
                     + " · ".join(f"{o} {v:.2f}" for o, v in nn[c].items()) + " |")
    lines += ["", "## Focus-company pairs: what drives similarity", "",
              "| Pair | Combined | Shared skills (share a/b) | Biggest differences |", "|---|---:|---|---|"]
    for i, a in enumerate(COMPANIES):
        for b in COMPANIES[i + 1:]:
            s, dd = drivers(sh, a, b)
            lines.append(f"| {a} – {b} | {S.loc[a, b]:.2f} | {s} | {dd} |")
    lines += ["", "## Top 15 most similar pairs (all companies)", "", pairs.head(15).to_markdown(index=False), "",
              "## How much do the measures agree? (Spearman correlation across pairs)", "", agree.to_markdown(), "",
              "## Talent pools", "", "![Talent pools](figures/talent_pools.png)", ""]
    (REP / "summary.md").write_text(colorize_markdown("\n".join(lines)), encoding="utf-8")
    print(pairs.head(12).to_string(index=False))
    print(agree)
    for c in COMPANIES:
        print(c, "->", ", ".join(f"{o} {v:.2f}" for o, v in nn[c].items()))


if __name__ == "__main__":
    main()
