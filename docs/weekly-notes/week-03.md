# Weekly Notes — Week 3 (2026-11-10)

**Attendees:** Frank Mediavilla (solo: Scrum Leader, Data Quality Lead, Documentation Lead, Technical Lead)
**Current sprint:** Sprint 7 — Task 7, Demand Forecasting (done early)

## Progress this week

- Built 16 weekly series (open roles, open roles by function, new-posting flows, NVIDIA requisition rate) on an 8-week horizon.
- Rolling-origin backtests over 12,200 forecasts. Best models beat naive by up to 32% (drift/ETS for growing stocks, seasonal naive for Google, averages for noisy flows).
- Empirical 80% intervals from backtest errors; forecasts frozen in `data/forecasts/frozen/2026-11-10.csv` and scored weekly by `score_frozen.py`.
- Snapshots now record Google's board total (3,028 on 2026-11-10) as a forecast actual.

## Decisions

- Headline metric: skill vs naive at the same horizons (MASE ratio).
- Symmetric empirical intervals; backtest bias reported separately (growth gets under-forecast).
- Frozen forecasts are never edited; one per freeze date.

## Blockers / open questions

- Anthropic's August regime change can't be forecast from its own history, so it needs leading indicators (Sprint 9 event timeline).

## Data quality check (Data Quality Lead)

- Archive gaps are interpolated and flagged; Epoch's last week is partial.

## Technical notes (Technical Lead)

- ARIMA order chosen on the early half only to avoid look-ahead; statsmodels convergence warnings suppressed.

## Next steps

- [ ] Thursday: `run_snapshot nvidia google`. Monday: full snapshot + Epoch refresh + `score_frozen`.
- [ ] Sprint 8: similarity scoring + more Greenhouse/Ashby companies.
