"""Score frozen forecasts against actuals as new data arrives (prospective, out-of-sample evaluation).

Usage:  python -m src.forecast.score_frozen     (run after each weekly data refresh)

For every frozen forecast file (data/forecasts/frozen/*.csv), each target week that now has an actual value
is scored: absolute error, whether the actual fell inside the 80% interval, and the error of the naive
"no change" forecast made at the same time (its last actual), so realized skill vs naive can be reported.

Outputs: data/forecasts/scorecard.csv, reports/forecast/scorecard.md
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.style import colorize_markdown

from .series import build

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "data" / "forecasts" / "frozen"
OUT_CSV = ROOT / "data" / "forecasts" / "scorecard.csv"
OUT_MD = ROOT / "reports" / "forecast" / "scorecard.md"


def main() -> None:
    actuals = {s.id: s.y for s in build()}
    rows = []
    for f in sorted(FROZEN.glob("*.csv")):
        fc = pd.read_csv(f, parse_dates=["origin_week", "target_week"])
        for r in fc.itertuples(index=False):
            y = actuals.get(r.series)
            if y is None or r.target_week not in y.index:
                continue
            a = float(y.loc[r.target_week])
            rows.append({"frozen_file": f.name, "series": r.series, "company": r.company, "h": r.h,
                         "target_week": r.target_week.date(), "actual": a, "point": r.point,
                         "abs_err": abs(a - r.point), "naive_abs_err": abs(a - r.last_actual),
                         "in_80": r.lo80 <= a <= r.hi80})
    sc = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    total = sum(len(pd.read_csv(f)) for f in FROZEN.glob("*.csv"))
    lines = ["# Frozen Forecast Scorecard (generated)", "",
             "Forecasts are frozen in `data/forecasts/frozen/` (committed, never edited) and scored here as actuals "
             "arrive. See [Sprint 7](../../docs/sprints/sprint-07-demand-forecasting.md).", ""]
    if sc.empty:
        lines += [f"**0 of {total} forecast targets resolved yet.** The first targets fall in the week of "
                  f"{pd.read_csv(sorted(FROZEN.glob('*.csv'))[0]).target_week.min()}; rerun after the next data refresh."]
        sc = pd.DataFrame(columns=["series"])
    else:
        by = sc.groupby("series").agg(targets=("abs_err", "size"), mae=("abs_err", "mean"),
                                      naive_mae=("naive_abs_err", "mean"), coverage80=("in_80", "mean"))
        by["skill_vs_naive"] = 1 - by.mae / by.naive_mae
        lines += [f"**{len(sc)} of {total} targets resolved** · overall 80%-interval coverage "
                  f"**{sc.in_80.mean():.0%}** (target 80%) · realized skill vs naive "
                  f"**{1 - sc.abs_err.sum() / sc.naive_abs_err.sum():+.0%}**", "",
                  by.round(3).to_markdown()]
    sc.to_csv(OUT_CSV, index=False)
    OUT_MD.write_text(colorize_markdown("\n".join(lines) + "\n"), encoding="utf-8")
    print(lines[-1] if sc.empty else lines[4])


if __name__ == "__main__":
    main()
