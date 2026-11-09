"""Sprint 5: hiring trend analysis.

Usage (repo root):
    python -m src.trends.build_trends

Inputs   data/features/posting_features.parquet, data/features/skills_long.csv   (Sprint 4)
         data/external/epoch/latest/frontier_lab_hiring_open_roles_by_category.csv (Epoch daily open roles)
Outputs  data/trends/*.csv                 trend tables (shared weekly structure)
         data/trends/posting_trend_fields.csv  per-posting posting_week, posting_month,
                                           hiring_velocity_bucket, emerging_skill_flag
         reports/trends/figures/*.png      charts
         reports/trends/summary.md         generated tables + charts

Shared time-series structure (all companies)
    week           Monday of the ISO week
    new_postings   postings first seen that week (the hiring "flow")
    closed         postings last seen that week and no longer open
    active         postings open at any point that week (the "stock")

What history exists
    Anthropic, OpenAI  Epoch AI daily scrapes from 2026-03-18 plus our snapshots, so real weekly flows.
                       The first Epoch week is excluded from flows (every open posting is "first
                       seen" there, i.e. left-censored stock, not new hiring).
    NVIDIA, Google     only our snapshots since 2026-11-08. Until more weeks accumulate, recent
                       velocity comes from each posting's published date (survivorship-biased:
                       older postings that already closed are invisible).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FEAT = ROOT / "data" / "features"
OUT = ROOT / "data" / "trends"
REP = ROOT / "reports" / "trends"
FIG = REP / "figures"
EPOCH_OPEN = ROOT / "data" / "external" / "epoch" / "latest" / "frontier_lab_hiring_open_roles_by_category.csv"

EPOCH_START = pd.Timestamp("2026-03-18")
HISTORY = ["Anthropic", "OpenAI"]
COMPANIES = ["Anthropic", "OpenAI", "NVIDIA", "Google"]

from src.style import COMPANY_COLOR as COLOR, THEME, apply_matplotlib, colorize_markdown, footnote, label  # noqa: E402

INK, INK2, GRID, SURFACE = THEME["text"], THEME["text2"], THEME["grid"], THEME["surface"]
apply_matplotlib()
SOURCE = "Source: Epoch AI 'Data on Frontier Lab Hiring' (CC BY) + project snapshots"


def monday(s: pd.Series) -> pd.Series:
    return s.dt.to_period("W-SUN").dt.start_time


# ---------------------------------------------------------------- tables


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    f = pd.read_parquet(FEAT / "posting_features.parquet")
    for c in ["first_seen_date", "last_seen_date", "posting_date"]:
        f[c] = pd.to_datetime(f[c], errors="coerce")
    f["posting_week"] = monday(f["first_seen_date"])
    f["posting_month"] = f["first_seen_date"].dt.to_period("M").astype(str)
    long = pd.read_csv(FEAT / "skills_long.csv")
    return f, long


def weekly_flows(f: pd.DataFrame) -> pd.DataFrame:
    """new / closed / active per company-week for companies with real history."""
    latest = f["last_seen_date"].max()
    # Only complete weeks (Mon-Sun) count; a week still in progress would understate flows.
    last_week = monday(pd.Series([latest]))[0]
    if latest.weekday() != 6:
        last_week -= pd.Timedelta(weeks=1)
    rows = []
    for c in HISTORY:
        d = f[f.company_name == c]
        weeks = pd.date_range(monday(pd.Series([EPOCH_START]))[0], last_week, freq="W-MON")
        for w in weeks:
            end = w + pd.Timedelta(days=6)
            new = ((d.posting_week == w) & (d.first_seen_date > EPOCH_START)).sum()
            closed = ((d.job_status == "closed") & (monday(d.last_seen_date) == w)).sum()
            active = ((d.first_seen_date <= end) & (d.last_seen_date >= w)).sum()
            rows.append({"week": w.date(), "company": c, "new_postings": new, "closed": closed, "active": active})
    t = pd.DataFrame(rows)
    # Epoch scrape coverage: gaps push "first seen" to the next scrape, making weekly flows lumpy.
    dates = pd.Series(pd.to_datetime(pd.read_csv(EPOCH_OPEN, usecols=["date"]).date.unique()))
    cov = monday(dates).dt.date.value_counts()
    t["scrape_days"] = t.week.map(cov).fillna(0).astype(int)
    t["low_coverage"] = t.scrape_days < 4
    t.loc[t.week >= monday(pd.Series([dates.max()]))[0].date(), "low_coverage"] = False  # our snapshot weeks
    first_week = monday(pd.Series([EPOCH_START]))[0].date()
    t.loc[t.week == first_week, "new_postings"] = pd.NA  # left-censored stock
    t["new_4wk_avg"] = t.groupby("company")["new_postings"].transform(lambda s: s.astype(float).rolling(4, 1).mean()).round(1)
    t["net_change"] = t["new_postings"] - t["closed"]
    return t


def velocity_buckets(t: pd.DataFrame) -> pd.DataFrame:
    """low / medium / high relative to each company's own weekly distribution (terciles)."""
    t = t.copy()
    t["hiring_velocity_bucket"] = ""
    for c, g in t.dropna(subset=["new_postings"]).groupby("company"):
        q = g["new_postings"].astype(float).quantile([1 / 3, 2 / 3]).values
        t.loc[g.index, "hiring_velocity_bucket"] = [
            "low" if v <= q[0] else "high" if v > q[1] else "medium" for v in g["new_postings"].astype(float)
        ]
    return t


def epoch_open_roles() -> pd.DataFrame:
    d = pd.read_csv(EPOCH_OPEN, parse_dates=["date"])
    t = d.groupby(["date", "lab", "category"]).open_postings.sum().reset_index()
    return t


def recent_published(f: pd.DataFrame, weeks: int = 8) -> pd.DataFrame:
    """Postings per week by published date for currently open roles (NVIDIA, Google)."""
    d = f[f.company_name.isin(["NVIDIA", "Google"]) & f.in_live & (f.job_status == "active")].copy()
    d["pub_week"] = monday(d["posting_date"])
    latest = monday(pd.Series([f["last_seen_date"].max()]))[0]
    d = d[d.pub_week > latest - pd.Timedelta(weeks=weeks)]
    return d.groupby(["company_name", "pub_week"]).size().unstack(0).fillna(0).astype(int)


def monthly_role_family(f: pd.DataFrame) -> pd.DataFrame:
    d = f[f.company_name.isin(HISTORY) & (f.first_seen_date > EPOCH_START)]
    t = d.groupby(["company_name", "posting_month", "role_family"]).size().rename("new_postings").reset_index()
    t["share"] = (t.new_postings / t.groupby(["company_name", "posting_month"]).new_postings.transform("sum")).round(4)
    return t


def period_split(f: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Early (first ~13 weeks after Epoch start) vs recent (last ~13 weeks) new postings."""
    d = f[f.company_name.isin(HISTORY) & (f.first_seen_date > EPOCH_START)]
    latest = d.first_seen_date.max()
    early = d.first_seen_date < EPOCH_START + pd.Timedelta(weeks=13)
    recent = d.first_seen_date >= latest - pd.Timedelta(weeks=13)
    return d[early].job_id, d[recent].job_id


def role_family_shift(f: pd.DataFrame) -> pd.DataFrame:
    e_ids, r_ids = period_split(f)
    rows = []
    for c in HISTORY:
        d = f[f.company_name == c]
        e = d[d.job_id.isin(e_ids)].role_family.value_counts(normalize=True)
        r = d[d.job_id.isin(r_ids)].role_family.value_counts(normalize=True)
        both = pd.concat([e.rename("early_share"), r.rename("recent_share")], axis=1).fillna(0)
        both["change_pp"] = ((both.recent_share - both.early_share) * 100).round(1)
        both["company"] = c
        rows.append(both.reset_index(names="role_family"))
    return pd.concat(rows, ignore_index=True)


def emerging_skills(f: pd.DataFrame, long: pd.DataFrame, min_recent: int = 15) -> pd.DataFrame:
    """Skills whose share of new postings grew most between the early and recent periods."""
    e_ids, r_ids = period_split(f)
    out = []
    for scope, ids_e, ids_r in [("Anthropic + OpenAI", e_ids, r_ids)] + [
        (c, e_ids[e_ids.isin(f[f.company_name == c].job_id)], r_ids[r_ids.isin(f[f.company_name == c].job_id)])
        for c in HISTORY
    ]:
        le = long[long.job_id.isin(ids_e)].groupby("skill").job_id.nunique() / max(len(ids_e), 1)
        lr_counts = long[long.job_id.isin(ids_r)].groupby("skill").job_id.nunique()
        lr = lr_counts / max(len(ids_r), 1)
        t = pd.concat([le.rename("early_share"), lr.rename("recent_share"), lr_counts.rename("recent_postings")],
                      axis=1).fillna(0)
        t = t[t.recent_postings >= min_recent]
        t["change_pp"] = ((t.recent_share - t.early_share) * 100).round(1)
        t["ratio"] = (t.recent_share / t.early_share.where(t.early_share > 0)).round(2)
        t["scope"] = scope
        t["emerging_skill_flag"] = (t.change_pp >= 2) & ((t.ratio >= 1.5) | t.ratio.isna())
        out.append(t.reset_index(names="skill"))
    res = pd.concat(out, ignore_index=True)
    res["category"] = res.skill.map(long.drop_duplicates("skill").set_index("skill").category)
    return res.sort_values(["scope", "change_pp"], ascending=[True, False])


def posting_lifetime(f: pd.DataFrame) -> pd.DataFrame:
    d = f[f.company_name.isin(HISTORY) & (f.job_status == "closed") & (f.first_seen_date > EPOCH_START)].copy()
    d["days_open"] = (d.last_seen_date - d.first_seen_date).dt.days
    by = d.groupby(["company_name", "role_family"]).days_open.agg(["median", "count"]).reset_index()
    tot = d.groupby("company_name").days_open.agg(["median", "count"]).reset_index().assign(role_family="All roles")
    return pd.concat([tot, by], ignore_index=True).rename(columns={"median": "median_days_open", "count": "closed_postings"})


# ---------------------------------------------------------------- charts


def _label_end(ax, x, y, text, color):
    ax.annotate(text, (x, y), xytext=(6, 0), textcoords="offset points", va="center", color=INK, fontsize=9,
                fontweight="bold")
    ax.plot([x], [y], "o", color=color, markersize=6, markeredgecolor=SURFACE, markeredgewidth=2)


def fig_weekly_new(t: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for c in HISTORY:
        d = t[t.company == c].dropna(subset=["new_postings"])
        x = pd.to_datetime(d.week)
        ax.plot(x, d.new_postings.astype(float), color=COLOR[c], alpha=0.55, linewidth=1.1)
        ax.plot(x, d.new_4wk_avg, color=COLOR[c], linewidth=2.2)
        _label_end(ax, x.iloc[-1], d.new_4wk_avg.iloc[-1], f"{c} {d.new_4wk_avg.iloc[-1]:.0f}/wk", COLOR[c])
    ax.set_title("New postings per week (thin) and 4-week average (bold)")
    ax.set_ylabel("postings first seen")
    ax.set_ylim(bottom=0)
    ax.margins(x=0.12)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, SOURCE)
    fig.savefig(FIG / "weekly_new_postings.png", dpi=150)
    plt.close(fig)


def fig_open_roles(eo: pd.DataFrame) -> None:
    tot = eo.groupby(["date", "lab"]).open_postings.sum().unstack()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for c in HISTORY:
        ax.plot(tot.index, tot[c], color=COLOR[c])
        _label_end(ax, tot.index[-1], tot[c].iloc[-1], f"{c} {tot[c].iloc[-1]:.0f}", COLOR[c])
    ax.set_title("Open roles per day (Epoch AI daily scrapes)")
    ax.set_ylabel("open postings")
    ax.set_ylim(bottom=0)
    ax.margins(x=0.1)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, "Source: Epoch AI daily open-role counts (CC BY)")
    fig.savefig(FIG / "open_roles.png", dpi=150)
    plt.close(fig)


def fig_open_by_category(eo: pd.DataFrame) -> None:
    cats = [c for c in ["Go-to-market", "Research", "Product", "Compute", "Corporate", "Other"]
            if eo[eo.category == c].open_postings.sum() > 0]
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.4), sharex=True)
    for ax in list(axes.flat)[len(cats):]:
        ax.set_visible(False)
    for ax, cat in zip(axes.flat, cats):
        d = eo[eo.category == cat].pivot_table(index="date", columns="lab", values="open_postings", aggfunc="sum")
        for c in HISTORY:
            if c in d:
                ax.plot(d.index, d[c], color=COLOR[c], linewidth=1.8, label=c)
        ax.set_title(cat, fontsize=10)
        ax.set_ylim(bottom=0)
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    axes.flat[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Open roles by Epoch category", x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, "Source: Epoch AI daily open-role counts (CC BY)")
    fig.savefig(FIG / "open_roles_by_category.png", dpi=150)
    plt.close(fig)


def fig_role_shift(rs: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharex=True)
    for ax, c in zip(axes, HISTORY):
        d = rs[rs.company == c].sort_values("change_pp")
        d = pd.concat([d.head(5), d.tail(5)]).drop_duplicates("role_family")
        ax.barh(d.role_family, d.change_pp, color=COLOR[c], height=0.6)
        for y, v in enumerate(d.change_pp):
            ax.annotate(f"{v:+.1f}", (v, y), xytext=(4 if v >= 0 else -4, 0), textcoords="offset points",
                        ha="left" if v >= 0 else "right", va="center", fontsize=8, color=INK)
        ax.axvline(0, color=INK2, linewidth=0.8)
        ax.set_title(c)
        ax.grid(axis="y", visible=False)
        ax.margins(x=0.25)
    axes[0].set_xlabel("change in share of new postings (pp), early vs recent 13 weeks")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, SOURCE)
    fig.savefig(FIG / "role_family_shift.png", dpi=150)
    plt.close(fig)


def fig_emerging(em: pd.DataFrame) -> None:
    d = em[em.scope == "Anthropic + OpenAI"].head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(d.skill, d.change_pp, color=THEME["text2"], height=0.6)
    for y, (v, e, r) in enumerate(zip(d.change_pp, d.early_share, d.recent_share)):
        ax.annotate(f"+{v:.1f} pp  ({e:.0%} → {r:.0%})", (v, y), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK)
    ax.set_title("Fastest-rising skills in new postings: Anthropic + OpenAI")
    ax.set_xlabel("change in share of new postings (pp), early vs recent 13 weeks")
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.35)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, SOURCE)
    fig.savefig(FIG / "emerging_skills.png", dpi=150)
    plt.close(fig)


def fig_recent_published(rp: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, c in zip(axes, ["NVIDIA", "Google"]):
        if c in rp:
            ax.bar(rp.index, rp[c], width=5, color=COLOR[c])
            for x, v in zip(rp.index, rp[c]):
                if v:
                    ax.annotate(str(v), (x, v), xytext=(0, 3), textcoords="offset points", ha="center",
                                fontsize=8, color=INK)
        ax.set_title(f"{c}: open postings by week published")
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
        ax.grid(axis="x", visible=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, "Source: project snapshots (published date of currently open roles)")
    fig.savefig(FIG / "nvidia_google_recent.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- report


def write_summary(t, eo, rp, rs, em, life, f) -> None:
    tot = eo.groupby(["date", "lab"]).open_postings.sum().unstack()
    first, last = tot.iloc[0], tot.iloc[-1]
    flows = t.dropna(subset=["new_postings"])
    agg = flows.groupby("company").agg(weeks=("week", "size"), total_new=("new_postings", "sum"),
                                       mean_new_per_week=("new_postings", "mean"),
                                       total_closed=("closed", "sum"))
    agg["mean_new_per_week"] = agg.mean_new_per_week.astype(float).round(1)
    agg["open_roles_start"] = [int(first[c]) for c in agg.index]
    agg["open_roles_latest"] = [int(last[c]) for c in agg.index]
    agg["open_roles_change"] = [f"{(last[c] / first[c] - 1):+.0%}" for c in agg.index]
    recent4 = flows.groupby("company").tail(4).groupby("company").new_postings.mean().astype(float).round(1)
    prior4 = flows.groupby("company").apply(lambda g: g.iloc[-8:-4].new_postings.mean()).astype(float).round(1)
    agg["last_4wk_avg"], agg["prior_4wk_avg"] = recent4, prior4

    life_all = life[life.role_family == "All roles"].set_index("company_name")
    em_top = em[(em.scope == "Anthropic + OpenAI")].head(12)
    lines = [
        "# Hiring Trends Summary (generated)", "",
        f"Generated by `python -m src.trends.build_trends` · data through {f.last_seen_date.max().date()} · "
        "see [Sprint 5](../../docs/sprints/sprint-05-hiring-trends.md)", "",
        "## Anthropic & OpenAI: weekly flows (Epoch history + our snapshots)", "",
        agg.rename(index=label).reset_index().to_markdown(index=False), "",
        "![Weekly new postings](figures/weekly_new_postings.png)", "",
        f"> Epoch's daily scrapes have gaps (up to 8 days). Postings published during a gap are first seen "
        f"on the next scrape, so single weeks are lumpy. {int(t[t.company == 'Anthropic'].low_coverage.sum())} "
        "weeks had fewer than 4 scrape days (`low_coverage` in the weekly table). Read the 4-week average.", "",
        "![Open roles](figures/open_roles.png)", "",
        "![Open roles by category](figures/open_roles_by_category.png)", "",
        "## Role mix shift (early vs recent 13 weeks)", "",
        "![Role family shift](figures/role_family_shift.png)", "",
        rs.pivot_table(index="role_family", columns="company", values="change_pp").fillna(0)
          .sort_values("Anthropic", ascending=False).to_markdown(), "",
        "## Emerging skills", "",
        "![Emerging skills](figures/emerging_skills.png)", "",
        em_top[["skill", "category", "early_share", "recent_share", "change_pp", "ratio", "recent_postings"]]
          .assign(early_share=lambda d: d.early_share.map("{:.1%}".format),
                  recent_share=lambda d: d.recent_share.map("{:.1%}".format)).to_markdown(index=False), "",
        "## Posting lifetime (closed postings)", "",
        f"Median days a posting stays up before closing: Anthropic **{life_all.loc['Anthropic', 'median_days_open']:.0f}**, "
        f"OpenAI **{life_all.loc['OpenAI', 'median_days_open']:.0f}**. "
        "Lifetime here is first seen → last seen, i.e. how long a role stays open.", "",
        life[life.closed_postings >= 15].pivot_table(index="role_family", columns="company_name",
                                                     values="median_days_open").round(0).to_markdown(), "",
        "## NVIDIA & Google: recent posting velocity (published date, open roles only)", "",
        "![NVIDIA and Google](figures/nvidia_google_recent.png)", "",
        rp.assign(week=rp.index.date).set_index("week").to_markdown(), "",
        "> Survivorship-biased: only roles still open are visible, so older weeks are under-counted. "
        "Real flows for NVIDIA and Google come from our weekly snapshots, which accumulate from 2026-11-08.", "",
        "## Weekly table", "",
        t.to_markdown(index=False), "",
    ]
    (REP / "summary.md").write_text(colorize_markdown("\n".join(lines)), encoding="utf-8")


def main() -> None:
    for p in (OUT, REP, FIG):
        p.mkdir(parents=True, exist_ok=True)
    f, long = load()
    t = velocity_buckets(weekly_flows(f))
    eo = epoch_open_roles()
    rp = recent_published(f)
    rs = role_family_shift(f)
    em = emerging_skills(f, long)
    life = posting_lifetime(f)
    mrf = monthly_role_family(f)

    # per-posting trend fields (brief: posting_week/month, hiring_velocity_bucket, emerging_skill_flag)
    vb = t[["week", "company", "hiring_velocity_bucket"]].rename(columns={"company": "company_name"})
    vb["week"] = pd.to_datetime(vb.week)
    emerging = set(em[(em.scope == "Anthropic + OpenAI") & em.emerging_skill_flag].skill)
    has_em = long[long.skill.isin(emerging)].job_id.unique()
    fields = f[["job_id", "company_name", "posting_week", "posting_month"]].merge(
        vb, left_on=["company_name", "posting_week"], right_on=["company_name", "week"], how="left").drop(columns="week")
    fields["hiring_velocity_bucket"] = fields.hiring_velocity_bucket.fillna("")
    fields["emerging_skill_flag"] = fields.job_id.isin(has_em)
    fields["posting_week"] = fields.posting_week.dt.date

    t.to_csv(OUT / "weekly_company.csv", index=False)
    eo.to_csv(OUT / "epoch_open_roles_daily.csv", index=False)
    rp.to_csv(OUT / "nvidia_google_recent_published.csv")
    rs.to_csv(OUT / "role_family_shift.csv", index=False)
    mrf.to_csv(OUT / "monthly_role_family.csv", index=False)
    em.to_csv(OUT / "emerging_skills.csv", index=False)
    life.to_csv(OUT / "posting_lifetime.csv", index=False)
    fields.to_csv(OUT / "posting_trend_fields.csv", index=False)

    fig_weekly_new(t)
    fig_open_roles(eo)
    fig_open_by_category(eo)
    fig_role_shift(rs)
    fig_emerging(em)
    fig_recent_published(rp)
    write_summary(t, eo, rp, rs, em, life, f)
    print("trends written:", ", ".join(sorted(p.name for p in OUT.glob("*.csv"))))
    print("emerging skills:", sorted(emerging))


if __name__ == "__main__":
    main()
