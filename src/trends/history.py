"""Long-run hiring history: archive counts + Epoch + NVIDIA requisition-rate estimate.

Usage:  python -m src.trends.history   (after src.collect.wayback_history and an NVIDIA full-board snapshot)

1. Open roles over time
   Google      Wayback captures of the careers results page (total open jobs), 2023-2026
   Anthropic   Wayback captures of the Greenhouse board (2024-2026) + Epoch daily counts (2026)
   OpenAI      Epoch daily counts (2026); earlier pages aren't recoverable
   Validation: where Wayback and Epoch overlap (Anthropic, 2026) we compare them on the same dates.

2. NVIDIA requisitions per day (sequence-number estimator)
   NVIDIA requisition IDs (JR2029366, ...) are issued in sequence. Among currently open postings,
   the highest JR number posted on or before each date tracks the requisition counter, so its slope
   is the number of requisitions *created* per day, including ones since filled. This is the
   "German tank" idea, applied to hiring.

Outputs: data/history/open_roles_long.csv, data/history/nvidia_requisition_rate.csv
         reports/trends/figures/history_open_roles.png, nvidia_requisition_rate.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.style import COMPANY_COLOR, THEME, apply_matplotlib, footnote  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HIST = ROOT / "data" / "history"
FIG = ROOT / "reports" / "trends" / "figures"
apply_matplotlib()


def open_roles_long() -> tuple[pd.DataFrame, dict]:
    wb = pd.read_csv(HIST / "wayback_open_roles.csv", parse_dates=["date"])
    wb = wb.groupby(["company", pd.Grouper(key="date", freq="W-MON")]).open_roles.median().reset_index()
    wb["source"] = "Wayback"
    ep = pd.read_csv(ROOT / "data" / "trends" / "epoch_open_roles_daily.csv", parse_dates=["date"])
    ep = ep.groupby(["lab", pd.Grouper(key="date", freq="W-MON")]).open_postings.sum().reset_index()
    # daily rows summed within a week -> divide by days present to get the weekly mean
    days = (pd.read_csv(ROOT / "data" / "trends" / "epoch_open_roles_daily.csv", parse_dates=["date"])
            .groupby(["lab", pd.Grouper(key="date", freq="W-MON")]).date.nunique().reset_index(name="d"))
    ep = ep.merge(days, on=["lab", "date"])
    ep["open_roles"] = (ep.open_postings / ep.d).round()
    ep = ep.rename(columns={"lab": "company"})[["company", "date", "open_roles"]].assign(source="Epoch")
    long = pd.concat([wb, ep], ignore_index=True).sort_values(["company", "date"])

    # validation: Anthropic weeks present in both sources
    a = long[long.company == "Anthropic"].pivot_table(index="date", columns="source", values="open_roles")
    both = a.dropna()
    val = {}
    if len(both) >= 3:
        err = (both.Wayback - both.Epoch).abs() / both.Epoch
        val = {"weeks": len(both), "mape": float(err.mean()), "corr": float(both.Wayback.corr(both.Epoch))}
    return long, val


def fig_history(long: pd.DataFrame, val: dict) -> None:
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for c in ["Google", "Anthropic", "OpenAI"]:
        for src, ls, lw in [("Wayback", "-", 2.0), ("Epoch", "-", 2.6)]:
            d = long[(long.company == c) & (long.source == src)]
            if len(d) < 2:
                continue
            ax.plot(d.date, d.open_roles, color=COMPANY_COLOR[c], linestyle=ls, linewidth=lw,
                    alpha=0.6 if src == "Wayback" else 1.0)
        last = long[long.company == c].iloc[-1]
        ax.annotate(f"{c} {last.open_roles:,.0f}", (last.date, last.open_roles), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9, fontweight="bold", color=THEME["text"])
    ax.set_ylabel("open roles")
    ax.set_ylim(bottom=0)
    ax.margins(x=0.1)
    ax.set_title("Open roles over time (fainter = Internet Archive captures, solid = Epoch daily)")
    note = "Wayback Machine captures (counts only) + Epoch AI (CC BY)"
    if val:
        note += f" · Anthropic overlap check: {val['weeks']} weeks, mean abs. error {val['mape']:.0%}, r={val['corr']:.2f}"
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, note)
    fig.savefig(FIG / "history_open_roles.png")
    plt.close(fig)


def nvidia_requisitions() -> pd.DataFrame | None:
    f = ROOT / "data" / "processed" / "nvidia.csv"
    d = pd.read_csv(f, usecols=["job_id", "posting_date", "job_status"], dtype=str)
    d = d[d.job_status == "active"].copy()
    d["jr"] = pd.to_numeric(d.job_id.str.extract(r"JR(\d+)")[0], errors="coerce")
    d["date"] = pd.to_datetime(d.posting_date, errors="coerce")
    d = d.dropna(subset=["jr", "date"])
    if len(d) < 500:
        return None
    # monotone envelope: highest requisition number issued by each date
    env = d.groupby("date").jr.max().sort_index().cummax()
    n_week = d.set_index("date").jr.resample("W-MON").size()
    weekly = env.resample("W-MON").last().dropna()
    # only weeks with enough surviving postings to pin the counter down (older weeks are sparse)
    weekly = weekly[n_week.reindex(weekly.index).fillna(0) >= 5]
    gap_days = weekly.index.to_series().diff().dt.days
    rate = (weekly.diff() / gap_days).rename("reqs_per_day")
    out = pd.DataFrame({"max_jr": weekly, "reqs_per_day": rate,
                        "postings_that_week": n_week.reindex(weekly.index).values}).reset_index(names="week")
    out["reqs_per_day_4wk"] = out.reqs_per_day.rolling(4, 1).mean()
    out.to_csv(HIST / "nvidia_requisition_rate.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 3.8))
    o = out.dropna(subset=["reqs_per_day"])
    o = o[o.reqs_per_day >= 0]
    ax.bar(o.week, o.reqs_per_day, width=5, color=COMPANY_COLOR["NVIDIA"], alpha=0.45)
    ax.plot(o.week, o.reqs_per_day_4wk, color=COMPANY_COLOR["NVIDIA"], linewidth=2.4)
    last = o.iloc[-1]
    ax.annotate(f"{last.reqs_per_day_4wk:.0f} / day", (last.week, last.reqs_per_day_4wk), xytext=(6, 0),
                textcoords="offset points", va="center", fontweight="bold", color=THEME["text"])
    ax.set_ylabel("requisitions created per day")
    ax.set_title("NVIDIA: requisitions created per day, estimated from requisition-ID sequence")
    ax.margins(x=0.08)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    footnote(fig, "Highest JR number posted by each date among currently open postings (weekly), "
                  "differenced · bars = weekly, line = 4-week mean · counts all requisitions, incl. filled")
    fig.savefig(FIG / "nvidia_requisition_rate.png")
    plt.close(fig)
    return out


def main() -> None:
    long, val = open_roles_long()
    long.to_csv(HIST / "open_roles_long.csv", index=False)
    fig_history(long, val)
    print("history points:", long.groupby(["company", "source"]).size().to_dict())
    print("validation:", val)
    for c in ["Google", "Anthropic"]:
        d = long[(long.company == c) & (long.source == "Wayback")]
        if len(d):
            y = d.set_index("date").open_roles.resample("QS").median().dropna()
            print(c, "quarterly median:", {str(k.date()): int(v) for k, v in y.items()})
    nv = nvidia_requisitions()
    if nv is not None:
        o = nv.dropna(subset=["reqs_per_day"])
        print("NVIDIA reqs/day (4wk, last 6 weeks):", o.tail(6)[["week", "reqs_per_day_4wk"]].round(1).values.tolist())
    else:
        print("NVIDIA: not enough full-board data yet")


if __name__ == "__main__":
    main()
