"""Sprint 6: competitor comparison within one shared framework.

Usage (repo root):
    python -m src.compare.build_comparison

Framework
    Population   postings open in the latest snapshot (in_live & active), so all four companies are
                 compared at the same point in time.
    Lens A       All roles. Fair for Anthropic vs OpenAI (full boards). Google is an AI/ML-focused
                 sample and NVIDIA its newest ~100 postings, so their role mix is indicative only.
    Lens B       Technical roles only (ML/AI, research, software, infra, hardware, data, security).
                 Like-for-like across all four; used for skills, seniority, education, pay.
    Metrics      shares of each company's postings, never raw counts, because the samples differ.

Outputs  data/comparison/*.csv, reports/comparison/figures/*.png, reports/comparison/summary.md
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from src.style import COMPANIES, COMPANY_COLOR, THEME, apply_matplotlib, colorize_markdown, footnote  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FEAT = ROOT / "data" / "features"
OUT = ROOT / "data" / "comparison"
REP = ROOT / "reports" / "comparison"
FIG = REP / "figures"
apply_matplotlib()
SRC = "Source: project snapshots (open postings on 2026-11-09)"

TECH_FAMILIES = ["ML / AI Engineering", "Research", "Software Engineering", "Infrastructure & SRE",
                 "Hardware & Silicon", "Data & Analytics", "Security & Privacy"]
SENIORITY_ORDER = ["Intern", "Junior", "Mid", "Senior", "Lead", "Principal", "Manager", "Director+", "Unspecified"]

# ---------------------------------------------------------------- locations

_US_STATES = ("AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|"
              "NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC")
REGIONS = {
    "US": re.compile(rf"\bUSA?\b|United States|U\.S\.|, (?:{_US_STATES})\b|\b(?:{_US_STATES}), |San Francisco|"
                     r"New York|Seattle|Mountain View|Sunnyvale|Santa Clara|Austin|Boston|Chicago|Los Angeles|"
                     r"Washington|Atlanta|Denver|Kirkland|Cambridge, MA|Pittsburgh|Durham|Hillsboro|Redmond"),
    "Europe": re.compile(r"London|\bUK\b|United Kingdom|England|Dublin|Ireland|Paris|France|Zurich|Zürich|"
                         r"Switzerland|Munich|München|Berlin|Germany|Amsterdam|Netherlands|Madrid|Spain|Milan|"
                         r"Italy|Warsaw|Poland|Stockholm|Sweden|Copenhagen|Denmark|Brussels|Belgium|Lisbon|"
                         r"Portugal|Oslo|Norway|Helsinki|Finland|Prague|Czech|Vienna|Austria|Europe|EMEA", re.I),
    "Asia-Pacific": re.compile(r"Tokyo|Japan|Seoul|Korea|Singapore|Bengaluru|Bangalore|India|Hyderabad|Pune|"
                               r"Gurugram|Gurgaon|Mumbai|Sydney|Melbourne|Australia|Taipei|Taiwan|Shanghai|"
                               r"Beijing|China|Hong Kong|Jakarta|Indonesia|Manila|APAC|New Zealand", re.I),
    "Other": re.compile(r"Toronto|Montreal|Vancouver|Canada|Ontario|bCANb|Tel Aviv|Israel|Dubai|UAE|Abu Dhabi|Riyadh|"
                        r"S[aã]o Paulo|Brazil|Mexico|Buenos Aires|Bogot[aá]|Johannesburg|Nairobi|Lagos", re.I),
}
REMOTE = re.compile(r"remote", re.I)


def regions(loc: str) -> set[str]:
    return {r for r, rx in REGIONS.items() if rx.search(loc or "")}


def primary_hub(loc: str) -> str:
    first = (loc or "").split(";")[0].strip()
    first = re.sub(r"^US, [A-Z]{2}, ", "", first)                 # NVIDIA: "US, CA, Santa Clara, ..."
    first = re.sub(r"^(?:Remote-Friendly[^;]*|US - Remote|Remote)$", "Remote", first, flags=re.I)
    city = first.split(",")[0].strip()
    return {"New York City": "New York", "Bengaluru": "Bangalore", "Zürich": "Zurich"}.get(city, city) or "—"


# ---------------------------------------------------------------- data


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    f = pd.read_parquet(FEAT / "posting_features.parquet")
    cur = f[f.in_live & (f.job_status == "active")].copy()
    cur["regions"] = cur.location.map(regions)
    cur["is_remote"] = cur.location.str.contains(REMOTE) | cur.remote_type.eq("remote")
    cur["multi_location"] = cur.location.str.contains(";")
    cur["hub"] = cur.location.map(primary_hub)
    cur["salary_mid"] = (cur.salary_min + cur.salary_max) / 2
    long = pd.read_csv(FEAT / "skills_long.csv")
    long = long[long.job_id.isin(cur.job_id)]
    return cur, long


def share(df: pd.DataFrame, col: str, order: list[str] | None = None) -> pd.DataFrame:
    t = pd.crosstab(df[col], df.company_name, normalize="columns").reindex(columns=COMPANIES)
    return t.reindex(order).fillna(0) if order else t.fillna(0)


def profile(cur: pd.DataFrame, tech: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for c in COMPANIES:
        a, b = cur[cur.company_name == c], tech[tech.company_name == c]
        sal = b[b.salary_mid.notna()]
        rows[c] = {
            "open postings (all roles)": len(a),
            "technical roles": len(b),
            "technical share of postings": len(b) / max(len(a), 1),
            "median skills / tech posting": b.n_skills.median(),
            "median tech skills / tech posting": b.n_tech_skills.median(),
            "median min. years (tech)": b.min_years_experience.median(),
            "years stated (tech)": b.min_years_experience.notna().mean(),
            "PhD mentioned (tech)": b.mentions_phd.mean(),
            "PhD required (tech)": b.phd_in_requirements.mean(),
            "'or equivalent experience' (tech)": b.degree_equivalent_ok.mean(),
            "people managers (all roles)": a.is_people_manager.mean(),
            "remote-friendly (all roles)": a.is_remote.mean(),
            "multi-location postings": a.multi_location.mean(),
            "offers a US location": a.regions.map(lambda s: "US" in s).mean(),
            "offers Europe": a.regions.map(lambda s: "Europe" in s).mean(),
            "offers Asia-Pacific": a.regions.map(lambda s: "Asia-Pacific" in s).mean(),
            "pay disclosed (tech)": b.salary_mid.notna().mean(),
            "median pay midpoint, USD (tech)": sal.salary_mid.median() if len(sal) >= 10 else np.nan,
        }
    return pd.DataFrame(rows)


def distinctive_skills(tech: pd.DataFrame, long: pd.DataFrame, min_share=0.08, min_n=8) -> pd.DataFrame:
    """Lift = company share / mean share of the other three (each company weighted equally)."""
    lt = long[long.job_id.isin(tech.job_id)]
    n = tech.groupby("company_name").size()
    sh = (lt.groupby(["skill", "company_name"]).job_id.nunique().unstack().reindex(columns=COMPANIES).fillna(0) / n)
    cnt = lt.groupby(["skill", "company_name"]).job_id.nunique().unstack().reindex(columns=COMPANIES).fillna(0)
    out = []
    for c in COMPANIES:
        others = sh.drop(columns=c).mean(axis=1)
        d = pd.DataFrame({"company": c, "share": sh[c], "others_avg": others, "postings": cnt[c]})
        d["lift"] = (d.share + 0.01) / (d.others_avg + 0.01)
        d["gap_pp"] = (d.share - d.others_avg) * 100
        out.append(d.reset_index())
    res = pd.concat(out, ignore_index=True)
    res["category"] = res.skill.map(long.drop_duplicates("skill").set_index("skill").category)
    res["distinctive"] = (res.share >= min_share) & (res.postings >= min_n) & (res.lift >= 1.5)
    res["under_indexed"] = (res.others_avg >= 0.15) & (res.share <= res.others_avg / 2)
    return res.sort_values(["company", "lift"], ascending=[True, False])


def emphasis(long: pd.DataFrame, tech: pd.DataFrame) -> pd.DataFrame:
    """How companies phrase skills: required vs preferred share of skill mentions (tech roles)."""
    lt = long[long.job_id.isin(tech.job_id)]
    g = lt.groupby("company_name")
    return pd.DataFrame({
        "in requirements": g.in_requirements.mean(), "in preferred": g.in_preferred.mean(),
        "in responsibilities": g.in_responsibilities.mean(), "context only": g.apply(
            lambda d: (~d.in_requirements & ~d.in_preferred & ~d.in_responsibilities).mean()),
    }).T.reindex(columns=COMPANIES)


def hubs(cur: pd.DataFrame, k=6) -> pd.DataFrame:
    rows = []
    for c in COMPANIES:
        d = cur[cur.company_name == c].hub.value_counts(normalize=True).head(k)
        rows.append({"company": c, "top hubs": " · ".join(f"{h} {v:.0%}" for h, v in d.items())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- charts

def _seq_cmap():
    return LinearSegmentedColormap.from_list("seq", [THEME["panel"], "#1f3b57", "#2f6a9e", "#58a6ff", "#cae8ff"])


def fig_heatmap(t: pd.DataFrame, name: str, title: str, note: str) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 0.42 * len(t) + 1.6))
    ax.imshow(t.values, cmap=_seq_cmap(), aspect="auto", vmin=0, vmax=max(t.values.max(), 0.01))
    ax.set_xticks(range(len(t.columns)), [str(c) for c in t.columns])
    ax.set_yticks(range(len(t.index)), t.index)
    ax.tick_params(length=0)
    ax.xaxis.tick_top()
    for xt, c in zip(ax.get_xticklabels(), t.columns):
        xt.set_color(COMPANY_COLOR.get(c, THEME["text"]))
        xt.set_fontweight("bold")
    ax.grid(False)
    vmax = t.values.max()
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = t.values[i, j]
            ax.text(j, i, f"{v:.0%}" if v >= 0.005 else "·", ha="center", va="center", fontsize=9,
                    color=THEME["surface"] if v > 0.6 * vmax else THEME["text"])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, pad=28)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, note)
    fig.savefig(FIG / name)
    plt.close(fig)


def fig_dots(t: pd.DataFrame, name: str, title: str, note: str) -> None:
    t = t.loc[t.max(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(9.5, 0.42 * len(t) + 1.6))
    for i, row in enumerate(t.itertuples(index=False)):
        ax.plot([min(row), max(row)], [i, i], color=THEME["axis"], linewidth=2, zorder=1)
    for c in COMPANIES:
        ax.scatter(t[c], range(len(t)), s=70, color=COMPANY_COLOR[c], edgecolor=THEME["surface"], linewidth=1.5,
                   zorder=3, label=c)
    ax.set_yticks(range(len(t)), t.index)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", ncol=4, fontsize=9, handletextpad=0.3, columnspacing=1.2)
    ax.set_title(title)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, note)
    fig.savefig(FIG / name)
    plt.close(fig)


def fig_distinctive(ds: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.6))
    for ax, c in zip(axes.flat, COMPANIES):
        d = ds[(ds.company == c) & ds.distinctive].head(8).iloc[::-1]
        ax.barh(d.skill, d.share, color=COMPANY_COLOR[c], height=0.62)
        ax.scatter(d.others_avg, range(len(d)), marker="|", s=160, color=THEME["text"], zorder=3,
                   label="avg of other three")
        for y, (s, l) in enumerate(zip(d.share, d.lift)):
            ax.annotate(f"{s:.0%}  ×{l:.1f}", (s, y), xytext=(5, 0), textcoords="offset points", va="center",
                        fontsize=8.5, color=THEME["text"])
        ax.set_title(c, color=COMPANY_COLOR[c])
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        ax.grid(axis="y", visible=False)
        ax.margins(x=0.3)
        ax.tick_params(axis="y", labelsize=8.5)
    # the title explains the tick marks; a legend here collides with bars
    fig.suptitle("Most distinctive skills in technical roles  (bar = company share, tick = other three's average)",
                 x=0.01, ha="left", fontweight="bold", color=THEME["text"])
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    footnote(fig, SRC + " · lift = share ÷ average share of the other three")
    fig.savefig(FIG / "distinctive_skills.png")
    plt.close(fig)


def fig_seniority(sen: pd.DataFrame) -> None:
    order = ["Junior", "Mid", "Senior", "Lead", "Principal", "Manager", "Director+"]
    t = sen.reindex(order).fillna(0)
    t = t / t.sum()  # share of postings with a known level
    ramp = ["#1f3b57", "#26507a", "#2f6a9e", "#3f86c4", "#58a6ff", "#8cc4ff", "#cae8ff"]  # ordinal, one hue
    fig, ax = plt.subplots(figsize=(10, 3.4))
    left = np.zeros(len(COMPANIES))
    for lvl, col in zip(order, ramp):
        vals = t.loc[lvl, COMPANIES].values
        ax.barh(COMPANIES, vals, left=left, color=col, edgecolor=THEME["surface"], linewidth=2, label=lvl)
        for i, (l, v) in enumerate(zip(left, vals)):
            if v >= 0.07:
                ax.text(l + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=8.5,
                        color=THEME["surface"] if col in ramp[4:] else THEME["text"])
        left += vals
    for yt, c in zip(ax.get_yticklabels(), COMPANIES):
        yt.set_color(COMPANY_COLOR[c])
        yt.set_fontweight("bold")
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(False)
    ax.legend(ncol=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=8.5, handlelength=1.2)
    ax.set_title("Seniority mix of technical roles (postings with a known level)")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    footnote(fig, SRC)
    fig.savefig(FIG / "seniority_mix.png")
    plt.close(fig)


def fig_pay(tech: pd.DataFrame) -> None:
    d = tech[tech.salary_mid.notna()]
    cs = [c for c in COMPANIES if (d.company_name == c).sum() >= 10]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    data = [d[d.company_name == c].salary_mid / 1000 for c in cs]
    bp = ax.boxplot(data, vert=False, widths=0.5, patch_artist=True, showfliers=False,
                    medianprops={"color": THEME["text"], "linewidth": 2},
                    whiskerprops={"color": THEME["text2"]}, capprops={"color": THEME["text2"]})
    for patch, c in zip(bp["boxes"], cs):
        patch.set_facecolor(COMPANY_COLOR[c])
        patch.set_edgecolor(THEME["surface"])
    ax.set_yticks(range(1, len(cs) + 1), cs)
    for yt, c in zip(ax.get_yticklabels(), cs):
        yt.set_color(COMPANY_COLOR[c])
        yt.set_fontweight("bold")
    for i, s in enumerate(data, start=1):
        ax.annotate(f"median ${s.median():.0f}k · n={len(s)}", (s.quantile(0.75), i), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color=THEME["text"])
    ax.invert_yaxis()
    ax.set_xlabel("disclosed base pay midpoint, thousand USD (technical roles)")
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.25)
    ax.set_title("Disclosed pay for technical roles")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    footnote(fig, SRC + " · Google's results pages don't expose pay")
    fig.savefig(FIG / "pay.png")
    plt.close(fig)


def fig_regions(cur: pd.DataFrame) -> None:
    regs = ["US", "Europe", "Asia-Pacific", "Other"]
    t = pd.DataFrame({c: [cur[cur.company_name == c].regions.map(lambda s, r=r: r in s).mean() for r in regs]
                      for c in COMPANIES}, index=regs)
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    w = 0.2
    for k, c in enumerate(COMPANIES):
        xs = np.arange(len(regs)) + (k - 1.5) * w
        ax.bar(xs, t[c], width=w - 0.03, color=COMPANY_COLOR[c], label=c)
        for x, v in zip(xs, t[c]):
            if v >= 0.02:
                ax.text(x, v + 0.015, f"{v:.0%}", ha="center", fontsize=7.5, color=THEME["text"])
    ax.set_xticks(range(len(regs)), regs)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=4, loc="upper right", fontsize=9)
    ax.set_title("Where postings are located (share offering ≥1 location in region)")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    footnote(fig, SRC + " · Google sample was drawn from 8 hubs incl. London, Zurich, Bangalore, Tokyo")
    fig.savefig(FIG / "regions.png")
    plt.close(fig)


# ---------------------------------------------------------------- report

def pct_table(t: pd.DataFrame) -> str:
    return t.map(lambda v: f"{v:.0%}" if isinstance(v, (float, np.floating)) and not np.isnan(v) else "—").to_markdown()


def fmt_profile(p: pd.DataFrame) -> str:
    out = p.copy().astype(object)
    for idx in out.index:
        for c in out.columns:
            v = p.loc[idx, c]
            if pd.isna(v):
                out.loc[idx, c] = "—"
            elif "USD" in idx:
                out.loc[idx, c] = f"${v / 1000:.0f}k"
            elif idx.startswith(("open postings", "technical roles")):
                out.loc[idx, c] = f"{int(v):,}"
            elif idx.startswith("median"):
                out.loc[idx, c] = f"{v:.0f}"
            else:
                out.loc[idx, c] = f"{v:.0%}"
    return out.to_markdown()


def write_summary(prof, fam, cat, ds, emph, hub_t, sen) -> None:
    lines = [
        "# Competitor Comparison Summary (generated)", "",
        "Generated by `python -m src.compare.build_comparison` · population: postings open in the latest snapshot · "
        "see [Sprint 6](../../docs/sprints/sprint-06-competitor-comparison.md)", "",
        "> **Lens A (all roles)** is like-for-like only for Anthropic vs OpenAI (full boards). Google is an AI/ML-focused "
        "sample and NVIDIA its newest ~100 postings. **Lens B (technical roles)** is like-for-like across all four.", "",
        "## Company profiles", "", fmt_profile(prof), "",
        "## Role-family mix (lens A, all roles)", "", "![Role family mix](figures/role_family_mix.png)", "",
        pct_table(fam), "",
        "## Skill-category profile (lens B, technical roles)", "", "![Skill categories](figures/skill_categories.png)", "",
        pct_table(cat), "",
        "## Distinctive skills (lens B)", "", "![Distinctive skills](figures/distinctive_skills.png)", "",
    ]
    for c in COMPANIES:
        d = ds[(ds.company == c) & ds.distinctive].head(10)
        u = ds[(ds.company == c) & ds.under_indexed].sort_values("gap_pp").head(6)
        lines += [f"**{c}**",
                  "- over-indexes on: " + (" · ".join(f"{r.skill} ({r.share:.0%} vs {r.others_avg:.0%})"
                                                      for r in d.itertuples()) or "—"),
                  "- under-indexes on: " + (" · ".join(f"{r.skill} ({r.share:.0%} vs {r.others_avg:.0%})"
                                                       for r in u.itertuples()) or "—"), ""]
    lines += [
        "## Seniority (lens B)", "", "![Seniority mix](figures/seniority_mix.png)", "",
        pct_table(sen), "",
        "## Pay (lens B, where disclosed)", "", "![Pay](figures/pay.png)", "",
        "## Locations (lens A)", "", "![Regions](figures/regions.png)", "", hub_t.to_markdown(index=False), "",
        "## How skills are framed (lens B)", "",
        "Share of skill mentions by section. Higher *in preferred* means more nice-to-haves.", "", pct_table(emph), "",
    ]
    (REP / "summary.md").write_text(colorize_markdown("\n".join(lines)), encoding="utf-8")


def main() -> None:
    for p in (OUT, REP, FIG):
        p.mkdir(parents=True, exist_ok=True)
    cur, long = load()
    tech = cur[cur.role_family.isin(TECH_FAMILIES)]

    prof = profile(cur, tech)
    fam = share(cur, "role_family").sort_values("Anthropic", ascending=False)
    lt = long[long.job_id.isin(tech.job_id)]
    cat = (lt.drop_duplicates(["job_id", "category"]).groupby(["category", "company_name"]).size().unstack()
           .reindex(columns=COMPANIES).fillna(0) / tech.groupby("company_name").size()[COMPANIES])
    ds = distinctive_skills(tech, long)
    emph = emphasis(long, tech)
    sen = share(tech, "seniority_level", SENIORITY_ORDER)
    hub_t = hubs(cur)

    prof.to_csv(OUT / "company_profiles.csv")
    fam.to_csv(OUT / "role_family_mix.csv")
    cat.to_csv(OUT / "skill_category_share_tech.csv")
    ds.to_csv(OUT / "distinctive_skills.csv", index=False)
    emph.to_csv(OUT / "skill_emphasis.csv")
    sen.to_csv(OUT / "seniority_mix_tech.csv")
    hub_t.to_csv(OUT / "top_hubs.csv", index=False)

    fig_heatmap(fam, "role_family_mix.png", "Role-family mix of open postings (all roles)",
                SRC + " · Google = AI/ML sample, NVIDIA = newest ~100 postings")
    fig_dots(cat.drop(index=["Spoken Languages"], errors="ignore"), "skill_categories.png",
             "Share of technical postings mentioning each skill category", SRC)
    fig_distinctive(ds)
    fig_seniority(sen)
    fig_pay(tech)
    fig_regions(cur)
    write_summary(prof, fam, cat, ds, emph, hub_t, sen)
    print("comparison written:", ", ".join(sorted(p.name for p in OUT.glob("*.csv"))))


if __name__ == "__main__":
    main()
