"""Charts + generated summary for Sprint 7.  Usage: python -m src.forecast.report"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from src.style import COMPANY_COLOR, THEME, apply_matplotlib, colorize_markdown, footnote  # noqa: E402

from .series import build  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FC = ROOT / "data" / "forecasts"
REP = ROOT / "reports" / "forecast"
FIG = REP / "figures"
apply_matplotlib()

HEADLINE = [("anthropic_open", 60), ("openai_open", 30), ("google_open", 130), ("nvidia_reqs", 30),
            ("anthropic_open_gtm", 30), ("openai_open_product", 30)]
CATS = ["gtm", "research", "product", "compute", "corporate"]
CAT_LABEL = {"gtm": "Go-to-market", "research": "Research", "product": "Product", "compute": "Compute",
             "corporate": "Corporate"}


def fig_fans(series: dict, fc: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.2))
    for ax, (sid, window) in zip(axes.flat, HEADLINE):
        s, f = series[sid], fc[fc.series == sid]
        col = COMPANY_COLOR[s.company]
        hist = s.y.iloc[-window:]
        ax.plot(hist.index, hist.values, color=col, linewidth=2)
        x = pd.to_datetime(f.target_week)
        xs = [hist.index[-1]] + list(x)
        ax.fill_between(xs, [hist.iloc[-1]] + list(f.lo80), [hist.iloc[-1]] + list(f.hi80), color=col, alpha=0.18,
                        linewidth=0)
        ax.plot(xs, [hist.iloc[-1]] + list(f.point), color=col, linestyle="--", linewidth=2)
        last = f.iloc[-1]
        ax.annotate(f"{last.point:,.0f}\n({last.lo80:,.0f}–{last.hi80:,.0f})", (x.iloc[-1], last.point),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=THEME["text"])
        ax.set_title(f"{s.label}  ·  {f.model.iloc[0]}", fontsize=10.5)
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
        ax.margins(x=0.16)
        ax.set_ylim(bottom=0)
    fig.suptitle("8-week forecasts with 80% intervals (dashed = forecast, band = interval from backtest errors)",
                 x=0.01, ha="left", fontweight="bold", color=THEME["text"])
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    footnote(fig, "Frozen 2026-11-10 · intervals = ±80th percentile of the model's own backtest |error| per horizon")
    fig.savefig(FIG / "fan_charts.png")
    plt.close(fig)


def outlook_table(fc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lab in ["Anthropic", "OpenAI"]:
        for c in CATS:
            f = fc[(fc.series == f"{lab.lower()}_open_{c}") & (fc.h == 8)]
            if f.empty:
                continue
            r = f.iloc[0]
            rows.append({"company": lab, "function": CAT_LABEL[c], "now": r.last_actual, "in_8_weeks": r.point,
                         "change": r.point / r.last_actual - 1, "lo": r.lo80 / r.last_actual - 1,
                         "hi": r.hi80 / r.last_actual - 1, "model": r.model})
    return pd.DataFrame(rows)


def fig_outlook(o: pd.DataFrame) -> None:
    o = o.copy()
    o["row"] = o.company + " · " + o.function
    o = o.iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, r in enumerate(o.itertuples()):
        col = COMPANY_COLOR[r.company]
        ax.plot([r.lo, r.hi], [i, i], color=col, alpha=0.45, linewidth=6, solid_capstyle="round")
        ax.scatter([r.change], [i], s=70, color=col, edgecolor=THEME["surface"], linewidth=1.5, zorder=3)
        ax.annotate(f"{r.now:.0f} → {r.in_8_weeks:.0f}", (max(r.hi, r.change), i), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color=THEME["text"])
    ax.axvline(0, color=THEME["muted"], linewidth=1)
    ax.set_yticks(range(len(o)), o.row)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.2)
    ax.set_title("Where demand is heading: open roles by function, forecast change over 8 weeks")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, "Dot = point forecast, bar = 80% interval · Epoch AI function categories (CC BY)")
    fig.savefig(FIG / "function_outlook.png")
    plt.close(fig)


def fig_skill(sc: pd.DataFrame) -> None:
    t = sc.pivot_table(index="series", columns="model", values="skill_vs_naive")
    order = ["naive", "drift", "ma4", "ets", "arima", "ensemble", "snaive", "dhr"]
    t = t.reindex(columns=[c for c in order if c in t.columns])
    cmap = LinearSegmentedColormap.from_list("div", ["#d55181", THEME["panel"], "#199e70"])
    fig, ax = plt.subplots(figsize=(10, 0.4 * len(t) + 1.6))
    ax.imshow(t.values, cmap=cmap, vmin=-0.4, vmax=0.4, aspect="auto")
    ax.set_xticks(range(len(t.columns)), t.columns)
    ax.set_yticks(range(len(t.index)), t.index)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    ax.grid(False)
    for i in range(t.shape[0]):
        best = np.nanargmax(t.values[i])
        for j in range(t.shape[1]):
            v = t.values[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, f"{v:+.0%}", ha="center", va="center", fontsize=8,
                    color=THEME["text"], fontweight="bold" if j == best else "normal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Backtest skill vs naive (green = better than 'no change', magenta = worse; bold = selected)",
                 pad=26)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    footnote(fig, "Rolling-origin backtest, horizons 1-8 weeks · skill = 1 − MASE(model) / MASE(naive)")
    fig.savefig(FIG / "backtest_skill.png")
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    series = {s.id: s for s in build()}
    fc = pd.read_csv(FC / "latest_forecast.csv")
    sc = pd.read_csv(FC / "backtest_scores.csv")
    meta = json.loads((FC / "model_selection.json").read_text(encoding="utf-8"))
    fig_fans(series, fc)
    o = outlook_table(fc)
    fig_outlook(o)
    fig_skill(sc)
    o.to_csv(FC / "function_outlook.csv", index=False)

    h8 = fc[fc.h == 8].set_index("series")
    tab = pd.DataFrame({
        "company": h8.company, "model": h8.model,
        "skill vs naive": [f"{meta[s]['skill_vs_naive']:+.0%}" for s in h8.index],
        "history (weeks)": [meta[s]["n_weeks"] for s in h8.index],
        "last": h8.last_actual.map("{:,.0f}".format), "in 8 weeks": h8.point.map("{:,.0f}".format),
        "80% interval": [f"{a:,.0f}–{b:,.0f}" for a, b in zip(h8.lo80, h8.hi80)],
        "backtest bias": h8.backtest_bias.map("{:+.0f}".format),
    })
    lines = ["# Demand Forecast Summary (generated)", "",
             "Generated by `python -m src.forecast.report` · forecasts frozen 2026-11-10 · see "
             "[Sprint 7](../../docs/sprints/sprint-07-demand-forecasting.md) · live scoring: "
             "[scorecard](scorecard.md)", "",
             "![Fan charts](figures/fan_charts.png)", "", "## All series (8-week horizon)", "",
             tab.to_markdown(), "",
             "*backtest bias* > 0 means the model under-forecast during the backtest (common during growth).", "",
             "## Function outlook", "", "![Function outlook](figures/function_outlook.png)", "",
             o.assign(change=o.change.map("{:+.0%}".format),
                      interval=[f"{a:+.0%} to {b:+.0%}" for a, b in zip(o.lo, o.hi)])
              .drop(columns=["lo", "hi"]).to_markdown(index=False), "",
             "## Model selection", "", "![Backtest skill](figures/backtest_skill.png)", ""]
    (REP / "summary.md").write_text(colorize_markdown("\n".join(lines)), encoding="utf-8")
    print(o.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
