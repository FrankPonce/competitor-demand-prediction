"""Weekly series to forecast (Monday-start weeks), built from the project's trend and history tables.

| id                         | company   | what                                   | source                                  |
|----------------------------|-----------|----------------------------------------|-----------------------------------------|
| anthropic_open             | Anthropic | open roles (stock)                     | Internet Archive 2024-26 + Epoch 2026   |
| openai_open                | OpenAI    | open roles (stock)                     | Epoch 2026                              |
| google_open                | Google    | open roles (stock)                     | Internet Archive 2023-26                |
| {lab}_open_{category}      | lab       | open roles by Epoch function category  | Epoch 2026                              |
| {lab}_new                  | lab       | new postings per week (flow)           | Sprint 5 weekly flows                   |
| nvidia_reqs                | NVIDIA    | requisitions created per day           | requisition-ID estimator                |

Weekly values are means of the daily/capture values in that week. Missing weeks in the archive series are
linearly interpolated and flagged (`interpolated` column), never invented beyond the observed range.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EPOCH_DAILY = ROOT / "data" / "trends" / "epoch_open_roles_daily.csv"
WAYBACK = ROOT / "data" / "history" / "wayback_open_roles.csv"
FLOWS = ROOT / "data" / "trends" / "weekly_company.csv"
NV = ROOT / "data" / "history" / "nvidia_requisition_rate.csv"
CATEGORIES = {"Go-to-market": "gtm", "Research": "research", "Product": "product", "Compute": "compute",
              "Corporate": "corporate"}


@dataclass
class Series:
    id: str
    company: str
    label: str
    unit: str
    y: pd.Series            # weekly, Monday-indexed, no gaps
    interpolated: pd.Series  # bool per week
    seasonal: bool = False   # long enough for a yearly cycle


def week_start(dates: pd.Series) -> pd.Series:
    return pd.to_datetime(dates).dt.to_period("W-SUN").dt.start_time


def _regular(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    s = s.sort_index()
    idx = pd.date_range(s.index.min(), s.index.max(), freq="7D")
    r = s.reindex(idx)
    interp = r.isna()
    return r.interpolate("time").round(1), interp


def google_board_totals() -> pd.Series:
    """Google board totals recorded in the snapshot run log (note: 'board total=NNNN')."""
    log = ROOT / "reports" / "collection-log.csv"
    if not log.exists():
        return pd.Series(dtype=float)
    d = pd.read_csv(log)
    d = d[(d.company == "Google") & d.notes.fillna("").str.contains("board total=\\d", regex=True)]
    if d.empty:
        return pd.Series(dtype=float)
    vals = d.notes.str.extract(r"board total=(\d+)")[0].astype(float)
    weeks = week_start(pd.to_datetime(d.run_started_utc).dt.tz_localize(None))
    return pd.Series(vals.values, index=weeks.values).groupby(level=0).mean()


def build() -> list[Series]:
    out: list[Series] = []
    ep = pd.read_csv(EPOCH_DAILY, parse_dates=["date"])
    ep["week"] = week_start(ep.date)
    daily_tot = ep.groupby(["lab", "date", "week"]).open_postings.sum().reset_index()
    wk_tot = daily_tot.groupby(["lab", "week"]).open_postings.mean()
    wb = pd.read_csv(WAYBACK, parse_dates=["date"])
    wb["week"] = week_start(wb.date)
    wbw = wb.groupby(["company", "week"]).open_roles.mean()

    # Anthropic: archive before Epoch, Epoch once it starts
    a_ep = wk_tot.loc["Anthropic"]
    a_wb = wbw.loc["Anthropic"]
    a = pd.concat([a_wb[a_wb.index < a_ep.index.min()], a_ep])
    y, f = _regular(a)
    out.append(Series("anthropic_open", "Anthropic", "Anthropic open roles", "open roles", y, f))
    y, f = _regular(wk_tot.loc["OpenAI"])
    out.append(Series("openai_open", "OpenAI", "OpenAI open roles", "open roles", y, f))
    g = wbw.loc["Google"]
    snap = google_board_totals()
    if len(snap):  # our own snapshots record the board total from 2026-11-10 on
        g = pd.concat([g, snap]).groupby(level=0).mean()
    y, f = _regular(g)
    out.append(Series("google_open", "Google", "Google open roles", "open roles", y, f, seasonal=True))

    cat = ep.groupby(["lab", "category", "date", "week"]).open_postings.sum().reset_index()
    cat = cat.groupby(["lab", "category", "week"]).open_postings.mean()
    for lab in ["Anthropic", "OpenAI"]:
        for c, short in CATEGORIES.items():
            if (lab, c) in cat.index.droplevel(2):
                y, f = _regular(cat.loc[(lab, c)])
                out.append(Series(f"{lab.lower()}_open_{short}", lab, f"{lab} open roles: {c}", "open roles", y, f))

    fl = pd.read_csv(FLOWS, parse_dates=["week"]).dropna(subset=["new_postings"])
    for lab in ["Anthropic", "OpenAI"]:
        s = fl[fl.company == lab].set_index("week").new_postings.astype(float)
        y, f = _regular(s)
        out.append(Series(f"{lab.lower()}_new", lab, f"{lab} new postings / week", "new postings", y, f))

    nv = pd.read_csv(NV, parse_dates=["week"]).dropna(subset=["reqs_per_day"])
    nv = nv[nv.postings_that_week >= 5].set_index("week").reqs_per_day
    nv.index = week_start(pd.Series(nv.index)).values
    nv = nv[nv.index >= pd.Timestamp("2026-04-13")]  # dense part of the estimator
    y, f = _regular(nv)
    out.append(Series("nvidia_reqs", "NVIDIA", "NVIDIA requisitions / day", "requisitions per day", y, f))
    return out


if __name__ == "__main__":
    for s in build():
        print(f"{s.id:26s} n={len(s.y):3d}  {s.y.index.min().date()} → {s.y.index.max().date()}  "
              f"interp={int(s.interpolated.sum()):3d}  last={s.y.iloc[-1]:.0f}")
