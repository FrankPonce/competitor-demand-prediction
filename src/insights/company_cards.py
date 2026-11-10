"""Sprint 9: one-page company cards (same layout for every focus company).

Usage:  python -m src.insights.company_cards
Output: reports/insights/figures/card_<company>.png

Panels: hiring trajectory + 8-week forecast · role mix · distinctive skills · key figures.
Inputs are the outputs of Sprints 5-8, so the cards always reflect the latest pipeline run.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.forecast.series import build  # noqa: E402
from src.style import COMPANIES, COMPANY_COLOR, THEME, apply_matplotlib, footnote  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
FIG = ROOT / "reports" / "insights" / "figures"
apply_matplotlib()

SERIES = {"Anthropic": "anthropic_open", "OpenAI": "openai_open", "Google": "google_open", "NVIDIA": "nvidia_reqs"}
TAGLINE = {
    "Anthropic": "Safety-first frontier lab scaling go-to-market fast",
    "OpenAI": "Product & platform engineering at consumer scale",
    "NVIDIA": "The accelerated-computing stack, from silicon to robotics",
    "Google": "Cloud selling, GenAI and a deep management layer",
}


def load():
    prof = pd.read_csv(D / "comparison" / "company_profiles.csv", index_col=0)
    fam = pd.read_csv(D / "comparison" / "role_family_mix.csv", index_col=0)
    ds = pd.read_csv(D / "comparison" / "distinctive_skills.csv")
    hubs = pd.read_csv(D / "comparison" / "top_hubs.csv").set_index("company")["top hubs"]
    sim = pd.read_csv(D / "similarity" / "similarity_combined.csv", index_col=0)
    fc = pd.read_csv(D / "forecasts" / "latest_forecast.csv")
    series = {s.id: s for s in build()}
    return prof, fam, ds, hubs, sim, fc, series


def card(company, prof, fam, ds, hubs, sim, fc, series) -> None:
    col = COMPANY_COLOR[company]
    fig = plt.figure(figsize=(14, 8.2))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.05], width_ratios=[1.25, 1, 1], hspace=0.42, wspace=0.32,
                          left=0.14, right=0.98, top=0.86, bottom=0.1)
    fig.text(0.02, 0.955, company, fontsize=24, fontweight="bold", color=col)
    fig.text(0.02, 0.905, TAGLINE[company], fontsize=12.5, color=THEME["text2"])

    # A. trajectory + forecast
    ax = fig.add_subplot(gs[0, :2])
    s = series[SERIES[company]]
    y = s.y.iloc[-104:] if company == "Google" else s.y.iloc[-60:]
    f = fc[fc.series == SERIES[company]]
    ax.plot(y.index, y.values, color=col, linewidth=2.4)
    xs = [y.index[-1]] + list(pd.to_datetime(f.target_week))
    ax.fill_between(xs, [y.iloc[-1]] + list(f.lo80), [y.iloc[-1]] + list(f.hi80), color=col, alpha=0.18, linewidth=0)
    ax.plot(xs, [y.iloc[-1]] + list(f.point), color=col, linestyle="--", linewidth=2)
    last = f.iloc[-1]
    ax.annotate(f"8 wks: {last.point:,.0f}", (pd.to_datetime(last.target_week), last.point), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=9, color=THEME["text"])
    ax.set_title(f"{s.label} · history + 8-week forecast (80% band)", fontsize=11)
    ax.set_ylim(bottom=0)
    ax.margins(x=0.08)

    # B. key figures
    ax = fig.add_subplot(gs[0, 2])
    ax.axis("off")
    p = prof[company]
    nn = sim[company].drop(company).nlargest(3)
    pay = p.get("median pay midpoint, USD (tech)")
    rows = [
        ("Open postings", f"{int(p['open postings (all roles)']):,}"),
        ("Technical share", f"{p['technical share of postings']:.0%}"),
        ("Median min. years (tech)", f"{p['median min. years (tech)']:.0f}"),
        ("PhD mentioned (tech)", f"{p['PhD mentioned (tech)']:.0%}"),
        ("Median tech pay midpoint", f"${pay / 1000:.0f}k" if pd.notna(pay) else "not disclosed"),
        ("Most similar", ", ".join(nn.index[:2])),
    ]
    ax.set_title("Key figures", fontsize=11, loc="left")
    for i, (k, v) in enumerate(rows):
        yy = 0.92 - i * 0.16
        ax.text(0.0, yy, k, fontsize=9.5, color=THEME["text2"], transform=ax.transAxes)
        ax.text(1.0, yy, v, fontsize=11, fontweight="bold", color=THEME["text"], ha="right", transform=ax.transAxes)
        ax.plot([0, 1], [yy - 0.05, yy - 0.05], color=THEME["grid"], linewidth=0.8, transform=ax.transAxes)

    # C. role mix
    ax = fig.add_subplot(gs[1, 0])
    m = fam[company].sort_values(ascending=False).head(7).iloc[::-1]
    ax.barh(m.index, m.values, color=col, height=0.62)
    for i, v in enumerate(m.values):
        ax.annotate(f"{v:.0%}", (v, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8.5,
                    color=THEME["text"])
    ax.set_title("Role mix (open postings)", fontsize=11)
    ax.xaxis.set_visible(False)
    ax.grid(False)
    ax.margins(x=0.25)
    ax.tick_params(axis="y", labelsize=8.5)

    # D. distinctive skills
    ax = fig.add_subplot(gs[1, 1])
    d = ds[(ds.company == company) & ds.distinctive].head(7).iloc[::-1]
    ax.barh(d.skill.str.split(" (", regex=False).str[0], d.share, color=col, height=0.62)  # short labels
    ax.scatter(d.others_avg, range(len(d)), marker="|", s=140, color=THEME["text"], zorder=3)
    for i, (sv, lift) in enumerate(zip(d.share, d.lift)):
        ax.annotate(f"{sv:.0%} ×{lift:.1f}", (sv, i), xytext=(4, 0), textcoords="offset points", va="center",
                    fontsize=8.5, color=THEME["text"])
    ax.set_title("Distinctive skills (tech roles; tick = peers' avg)", fontsize=11)
    ax.xaxis.set_visible(False)
    ax.grid(False)
    ax.margins(x=0.3)
    ax.tick_params(axis="y", labelsize=8.5)

    # E. hubs + similarity text
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    ax.set_title("Where & against whom", fontsize=11, loc="left")
    hub_lines = hubs[company].split(" · ")[:5]
    for i, h in enumerate(hub_lines):
        ax.text(0.0, 0.92 - i * 0.1, h, fontsize=10, color=THEME["text"], transform=ax.transAxes)
    ax.text(0.0, 0.36, "Nearest competitors (similarity)", fontsize=9, color=THEME["text2"], transform=ax.transAxes)
    for i, (o, v) in enumerate(nn.items()):
        ax.text(0.0, 0.25 - i * 0.1, f"{o}  {v:.2f}", fontsize=10, color=COMPANY_COLOR.get(o, THEME["text"]),
                fontweight="bold" if o in COMPANY_COLOR else "normal", transform=ax.transAxes)
    footnote(fig, "Sources: Greenhouse/Ashby APIs, NVIDIA Workday board, Google Careers sample, Epoch AI (CC BY), "
                  "Internet Archive · open postings 2026-11-10 · project pipeline Sprints 2-8")
    fig.savefig(FIG / f"card_{company.lower()}.png")
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    data = load()
    for c in COMPANIES:
        card(c, *data)
    print("cards:", ", ".join(f"card_{c.lower()}.png" for c in COMPANIES))


if __name__ == "__main__":
    main()
