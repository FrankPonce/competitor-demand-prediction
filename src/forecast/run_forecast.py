"""Sprint 7: backtest, select, forecast and freeze.

Usage:  python -m src.forecast.run_forecast

1. Rolling-origin backtest per series: at each origin, train on data up to that week and forecast 1-8 weeks
   ahead. Short series (≈34 weeks) use every origin from week 16; long ones the last 52 weeks (every 2nd week).
2. Score with MASE: absolute error divided by the in-sample mean absolute week-to-week change at that origin.
   1.0 = as good as "repeat last week"; below 1.0 = better.
3. Select the model with the lowest MASE per series (ensemble and baselines included).
4. Fit on all data, forecast 8 weeks; 80% intervals from the selected model's own backtest errors at each
   horizon (empirical 10th-90th percentiles), not from model assumptions.
5. Freeze: data/forecasts/frozen/<date>.csv is committed and never edited. src.forecast.score_frozen scores it
   against actuals as new data arrives.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .models import model_set, predict, select_arima_order
from .series import Series, build

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "forecasts"
H = 8


def origins(n: int) -> list[int]:
    if n <= 60:
        return list(range(16, n))
    return list(range(n - 52, n, 2))


def backtest(s: Series, order) -> pd.DataFrame:
    rows = []
    names = list(model_set(s.seasonal)) + ["ensemble"]
    y = s.y
    for o in origins(len(y)):
        train = y.iloc[:o]
        scale = train.diff().abs().mean()
        if not scale or np.isnan(scale):
            continue
        h = min(H, len(y) - o)
        actual = y.iloc[o:o + h].to_numpy()
        for m in names:
            pred = predict(m, train, h, s.seasonal, order)
            for k in range(h):
                rows.append({"series": s.id, "model": m, "origin": y.index[o - 1], "h": k + 1,
                             "actual": actual[k], "pred": pred[k], "err": actual[k] - pred[k],
                             "scaled": abs(actual[k] - pred[k]) / scale})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    series = build()
    all_bt, scores, fc_rows, meta = [], [], [], {}
    for s in series:
        order = select_arima_order(s.y.iloc[: max(16, len(s.y) // 2)])  # chosen on early data only
        bt = backtest(s, order)
        all_bt.append(bt)
        sc = bt.groupby("model").agg(mase=("scaled", "mean"), mae=("err", lambda e: e.abs().mean()),
                                     n=("err", "size")).reset_index()
        sc["series"] = s.id
        naive_mase = float(sc.loc[sc.model == "naive", "mase"].iloc[0])
        sc["skill_vs_naive"] = 1 - sc.mase / naive_mase
        scores.append(sc)
        best = sc.sort_values("mase").iloc[0]
        model = best.model
        mbt = bt[bt.model == model]
        # symmetric empirical interval: 80th percentile of |error| at each horizon in the backtest
        q80 = mbt.groupby("h").err.apply(lambda e: e.abs().quantile(0.8))
        bias = mbt.groupby("h").err.mean()  # >0 = model under-forecast in the backtest
        point = predict(model, s.y, H, s.seasonal, order)
        last = s.y.index[-1]
        for k in range(H):
            hk = min(k + 1, q80.index.max())
            fc_rows.append({"series": s.id, "company": s.company, "label": s.label, "unit": s.unit,
                            "origin_week": last.date(), "target_week": (last + pd.Timedelta(weeks=k + 1)).date(),
                            "h": k + 1, "model": model, "point": round(point[k], 1),
                            "lo80": round(max(point[k] - q80.loc[hk], 0), 1), "hi80": round(point[k] + q80.loc[hk], 1),
                            "backtest_bias": round(float(bias.loc[hk]), 1),
                            "last_actual": round(float(s.y.iloc[-1]), 1)})
        meta[s.id] = {"model": model, "mase": round(float(best.mase), 3), "naive_mase": round(naive_mase, 3),
                      "skill_vs_naive": round(1 - float(best.mase) / naive_mase, 3),
                      "mean_bias_h8": round(float(bias.iloc[-1]), 1),
                      "arima_order": list(order), "n_weeks": len(s.y), "seasonal": s.seasonal}
        print(f"{s.id:26s} best={model:8s} MASE {best.mase:.2f} (naive {naive_mase:.2f}) arima{order}")

    bt = pd.concat(all_bt, ignore_index=True)
    sc = pd.concat(scores, ignore_index=True)
    fc = pd.DataFrame(fc_rows)
    bt.to_csv(OUT / "backtest_errors.csv", index=False)
    sc.round(4).to_csv(OUT / "backtest_scores.csv", index=False)
    fc.to_csv(OUT / "latest_forecast.csv", index=False)
    (OUT / "model_selection.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Scheduled refreshes set FREEZE_FORECAST=0: they update latest_forecast.csv but freeze nothing new,
    # so the public scorecard keeps tracking the same frozen file.
    if os.environ.get("FREEZE_FORECAST", "1") == "0":
        return
    frozen = OUT / "frozen" / f"{date.today().isoformat()}.csv"
    frozen.parent.mkdir(parents=True, exist_ok=True)
    if not frozen.exists():  # a frozen forecast is never overwritten
        fc.to_csv(frozen, index=False)
        print("frozen ->", frozen.relative_to(ROOT))


if __name__ == "__main__":
    main()
