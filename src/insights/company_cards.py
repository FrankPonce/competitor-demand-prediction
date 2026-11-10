"""Sprint 9: one-page company cards (same layout for every focus company).

Usage:  python -m src.insights.company_cards
Output: reports/insights/figures/card_<company>.png

Layout: header (logo, name, tagline, chips) · KPI tiles · hiring trajectory + 8-week forecast ·
hubs & nearest competitors · role mix · distinctive skills. Everything comes from the outputs of
Sprints 5-8, so the cards refresh with each pipeline run.

Logos: Simple Icons (CC0), recoloured to the project palette; trademarks belong to their owners
(assets/logos/NOTICE.md).
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch, PathPatch  # noqa: E402
from svgpath2mpl import parse_path  # noqa: E402

from src.collect.peers import segment  # noqa: E402
from src.forecast.series import build  # noqa: E402
from src.style import COMPANIES, COMPANY_COLOR, THEME, apply_matplotlib  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
FIG = ROOT / "reports" / "insights" / "figures"
LOGOS = ROOT / "assets" / "logos"
apply_matplotlib()

SERIES = {"Anthropic": "anthropic_open", "OpenAI": "openai_open", "Google": "google_open", "NVIDIA": "nvidia_reqs"}
TAGLINE = {
    "Anthropic": "Safety-first frontier lab scaling go-to-market fast",
    "OpenAI": "Product & platform engineering at consumer scale",
    "NVIDIA": "The accelerated-computing stack, from silicon to robotics",
    "Google": "Cloud selling, GenAI and a deep management layer",
}
PANEL, EDGE, TEXT, TEXT2, MUTED = THEME["panel"], THEME["axis"], THEME["text"], THEME["text2"], THEME["muted"]
PEER_GREY = "#8b949e"


# ---------------------------------------------------------------- helpers


def panel(fig, x, y, w, h, title=None):
    fig.add_artist(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                                  transform=fig.transFigure, facecolor=PANEL, edgecolor=EDGE, linewidth=1,
                                  zorder=0))
    if title:
        fig.text(x + 0.012, y + h - 0.03, title, fontsize=11, fontweight="bold", color=TEXT, va="center")


def inner_axes(fig, x, y, w, h, pad=(0.045, 0.03, 0.015, 0.06)):
    left, bottom, right, top = pad
    ax = fig.add_axes((x + left, y + bottom, w - left - right, h - bottom - top))
    ax.set_facecolor("none")
    return ax


def draw_logo(fig, company, rect):
    svg = (LOGOS / f"{company.lower()}.svg").read_text(encoding="utf-8")
    path = parse_path(re.search(r'<path d="([^"]+)"', svg).group(1))
    ax = fig.add_axes(rect)
    ax.add_patch(PathPatch(path, facecolor=COMPANY_COLOR[company], edgecolor="none"))
    ax.set_xlim(0, 24)
    ax.set_ylim(24, 0)  # SVG y axis points down
    ax.set_aspect("equal")
    ax.axis("off")


def chip(fig, x, y, text, color):
    t = fig.text(x, y, f"  {text}  ", fontsize=9.5, color=TEXT, va="center",
                 bbox={"boxstyle": "round,pad=0.35,rounding_size=0.8", "facecolor": PANEL, "edgecolor": color,
                       "linewidth": 1.2})
    return t


def kpi(fig, x, y, w, h, label, value, sub, accent):
    panel(fig, x, y, w, h)
    fig.add_artist(Line2D([x + 0.012, x + 0.012], [y + 0.02, y + h - 0.02], transform=fig.transFigure,
                          color=accent, linewidth=3, solid_capstyle="round"))
    fig.text(x + 0.024, y + h - 0.028, label, fontsize=9, color=TEXT2, va="center")
    fig.text(x + 0.024, y + h * 0.42, value, fontsize=21, fontweight="bold", color=TEXT, va="center")
    fig.text(x + 0.024, y + 0.02, sub, fontsize=8.5, color=MUTED, va="bottom")


def parse_hubs(s: str) -> list[tuple[str, float]]:
    out = []
    for part in s.split(" · "):
        m = re.match(r"(.+?)\s+(\d+)%$", part.strip())
        if m:
            out.append((m.group(1), int(m.group(2)) / 100))
    return out


# ---------------------------------------------------------------- data


def load():
    prof = pd.read_csv(D / "comparison" / "company_profiles.csv", index_col=0)
    fam = pd.read_csv(D / "comparison" / "role_family_mix.csv", index_col=0)
    ds = pd.read_csv(D / "comparison" / "distinctive_skills.csv")
    hubs = pd.read_csv(D / "comparison" / "top_hubs.csv").set_index("company")["top hubs"]
    sim = pd.read_csv(D / "similarity" / "similarity_combined.csv", index_col=0)
    fc = pd.read_csv(D / "forecasts" / "latest_forecast.csv")
    series = {s.id: s for s in build()}
    return prof, fam, ds, hubs, sim, fc, series


# ---------------------------------------------------------------- card


def card(company, prof, fam, ds, hubs, sim, fc, series) -> None:
    col = COMPANY_COLOR[company]
    fig = plt.figure(figsize=(16, 9.6))
    fig.patch.set_facecolor(THEME["surface"])
    s = series[SERIES[company]]
    f = fc[fc.series == SERIES[company]]
    p = prof[company]

    # ---- header
    draw_logo(fig, company, (0.022, 0.885, 0.055, 0.09))
    fig.text(0.088, 0.945, company, fontsize=30, fontweight="bold", color=col, va="center")
    fig.text(0.088, 0.898, TAGLINE[company], fontsize=13, color=TEXT2, va="center")
    back = s.y.iloc[-27] if len(s.y) > 27 else s.y.iloc[0]
    mom = s.y.iloc[-1] / back - 1
    unit = "open roles" if "open" in s.id else "requisitions/day"
    # chips right-aligned as a pair: momentum at the edge, segment to its left
    right = chip(fig, 0.975, 0.945, f"{'+' if mom >= 0 else ''}{mom:.0%} {unit} vs 6 months ago", col)
    right.set_ha("right")
    fig.canvas.draw()
    bb = right.get_window_extent().transformed(fig.transFigure.inverted())
    left = chip(fig, bb.x0 - 0.012, 0.945, segment(company), EDGE)
    left.set_ha("right")
    fig.text(0.975, 0.898, "Snapshot 2026-11-10", fontsize=9, color=MUTED, ha="right", va="center")
    fig.add_artist(Line2D([0.022, 0.978], [0.865, 0.865], transform=fig.transFigure, color=col, linewidth=2.2,
                          alpha=0.9))

    # ---- KPI tiles
    last = f.iloc[-1]
    out_chg = last.point / last.last_actual - 1
    out_txt = "≈ flat" if abs(out_chg) < 0.005 else f"{'+' if out_chg >= 0 else ''}{out_chg:.0%}"
    pay = p.get("median pay midpoint, USD (tech)")
    tiles = [
        ("Open postings", f"{int(p['open postings (all roles)']):,}", "full board" if company != "Google" else "unbiased sample"),
        ("Technical share", f"{p['technical share of postings']:.0%}", "of open postings"),
        ("Median tech pay", f"${pay / 1000:.0f}k" if pd.notna(pay) else "n/a", "disclosed base midpoint" if pd.notna(pay) else "not disclosed"),
        ("PhD mentioned", f"{p['PhD mentioned (tech)']:.0%}", f"{p['median min. years (tech)']:.0f} yrs min. experience (median)"),
        ("8-week outlook", out_txt, f"{last.point:,.0f} {unit} ({last.lo80:,.0f}–{last.hi80:,.0f})"),
    ]
    gap = 0.0105
    tw = (0.956 - 4 * gap) / 5
    for i, (lab, val, sub) in enumerate(tiles):
        kpi(fig, 0.022 + i * (tw + gap), 0.72, tw, 0.125, lab, val, sub, col)

    # ---- trajectory
    x, y0, w, h = 0.022, 0.37, 0.6, 0.33
    panel(fig, x, y0, w, h, f"{s.label}: history and 8-week forecast")
    ax = inner_axes(fig, x, y0, w, h, pad=(0.05, 0.045, 0.03, 0.065))
    yy = s.y.iloc[-104:] if company == "Google" else s.y.iloc[-60:]
    ax.plot(yy.index, yy.values, color=col, linewidth=2.6)
    ax.fill_between(yy.index, 0, yy.values, color=col, alpha=0.10, linewidth=0)
    xs = [yy.index[-1]] + list(pd.to_datetime(f.target_week))
    ax.fill_between(xs, [yy.iloc[-1]] + list(f.lo80), [yy.iloc[-1]] + list(f.hi80), color=col, alpha=0.22,
                    linewidth=0)
    ax.plot(xs, [yy.iloc[-1]] + list(f.point), color=col, linestyle=(0, (3, 2)), linewidth=2.2)
    ax.scatter([xs[-1]], [f.point.iloc[-1]], s=46, color=col, edgecolor=PANEL, linewidth=2, zorder=3)
    ax.annotate(f"{f.point.iloc[-1]:,.0f}", (xs[-1], f.point.iloc[-1]), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=10, fontweight="bold", color=TEXT)
    ax.set_ylim(0, max(yy.max(), f.hi80.max()) * 1.08)
    ax.margins(x=0.06)
    ax.grid(axis="x", visible=False)
    ax.tick_params(labelsize=8.5)

    # ---- hubs & competitors (mini bars)
    x, w = 0.635, 0.343
    panel(fig, x, y0, w, h, "Where they hire · who they hire like")
    hub = parse_hubs(hubs[company])[:4]
    fig.text(x + 0.014, y0 + h - 0.065, "TOP HUBS", fontsize=8, color=MUTED, fontweight="bold")
    for i, (name, v) in enumerate(hub):
        yy_ = y0 + h - 0.095 - i * 0.03
        fig.text(x + 0.014, yy_, name, fontsize=9.5, color=TEXT, va="center")
        bx = x + 0.12
        fig.add_artist(FancyBboxPatch((bx, yy_ - 0.006), 0.15, 0.012, boxstyle="round,pad=0,rounding_size=0.005",
                                      transform=fig.transFigure, facecolor=THEME["grid"], edgecolor="none"))
        fig.add_artist(FancyBboxPatch((bx, yy_ - 0.006), max(0.15 * v / max(hub[0][1], 0.01), 0.004), 0.012,
                                      boxstyle="round,pad=0,rounding_size=0.005", transform=fig.transFigure,
                                      facecolor=col, edgecolor="none"))
        fig.text(bx + 0.158, yy_, f"{v:.0%}", fontsize=9, color=TEXT2, va="center")
    nn = sim[company].drop(company).nlargest(3)
    fig.text(x + 0.014, y0 + 0.115, "NEAREST COMPETITORS (SIMILARITY 0-1)", fontsize=8, color=MUTED,
             fontweight="bold")
    for i, (o, v) in enumerate(nn.items()):
        yy_ = y0 + 0.085 - i * 0.027
        oc = COMPANY_COLOR.get(o, PEER_GREY)
        fig.text(x + 0.014, yy_, o, fontsize=9.5, color=oc, va="center",
                 fontweight="bold" if o in COMPANY_COLOR else "normal")
        bx = x + 0.12
        fig.add_artist(FancyBboxPatch((bx, yy_ - 0.006), 0.15, 0.012, boxstyle="round,pad=0,rounding_size=0.005",
                                      transform=fig.transFigure, facecolor=THEME["grid"], edgecolor="none"))
        fig.add_artist(FancyBboxPatch((bx, yy_ - 0.006), 0.15 * v, 0.012, boxstyle="round,pad=0,rounding_size=0.005",
                                      transform=fig.transFigure, facecolor=oc, edgecolor="none"))
        fig.text(bx + 0.158, yy_, f"{v:.2f}", fontsize=9, color=TEXT2, va="center")

    # ---- role mix
    x, y0, w, h = 0.022, 0.055, 0.471, 0.295
    panel(fig, x, y0, w, h, "Role mix of open postings")
    ax = inner_axes(fig, x, y0, w, h, pad=(0.15, 0.015, 0.05, 0.06))
    m = fam[company].sort_values(ascending=False).head(6).iloc[::-1]
    ax.barh(m.index, m.values, color=col, height=0.58)
    for i, v in enumerate(m.values):
        ax.annotate(f"{v:.0%}", (v, i), xytext=(5, 0), textcoords="offset points", va="center", fontsize=9,
                    color=TEXT, fontweight="bold")
    ax.xaxis.set_visible(False)
    ax.grid(False)
    ax.tick_params(axis="y", labelsize=9, length=0)
    ax.margins(x=0.18)

    # ---- distinctive skills
    x = 0.507
    panel(fig, x, y0, w, h, "Distinctive skills in technical roles  (bar = share · tick = peers' average)")
    ax = inner_axes(fig, x, y0, w, h, pad=(0.15, 0.015, 0.05, 0.06))
    d = ds[(ds.company == company) & ds.distinctive].head(6).iloc[::-1]
    labels = d.skill.str.split(" (", regex=False).str[0]
    ax.barh(labels, d.share, color=col, height=0.58)
    ax.scatter(d.others_avg, range(len(d)), marker="|", s=170, linewidth=2.2, color=TEXT, zorder=3)
    for i, (sv, lift) in enumerate(zip(d.share, d.lift)):
        ax.annotate(f"{sv:.0%}  ×{lift:.1f}", (sv, i), xytext=(5, 0), textcoords="offset points", va="center",
                    fontsize=9, color=TEXT, fontweight="bold")
    ax.xaxis.set_visible(False)
    ax.grid(False)
    ax.tick_params(axis="y", labelsize=9, length=0)
    ax.margins(x=0.25)

    fig.text(0.022, 0.018, "Sources: Greenhouse/Ashby public APIs · NVIDIA Workday board · Google Careers sample · "
             "Epoch AI (CC BY) · Internet Archive · competitor-demand-prediction pipeline (Sprints 2-8)",
             fontsize=7.5, color=MUTED)
    fig.text(0.978, 0.018, "Logo: Simple Icons (CC0) · trademark of its owner · project not affiliated",
             fontsize=7.5, color=MUTED, ha="right")
    fig.savefig(FIG / f"card_{company.lower()}.png", dpi=150)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    data = load()
    for c in COMPANIES:
        card(c, *data)
    print("cards:", ", ".join(f"card_{c.lower()}.png" for c in COMPANIES))


if __name__ == "__main__":
    main()
