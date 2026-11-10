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

## Update — Sprint 8 done (2026-11-10)

- Added 13 AI-market peers through the same documented public Greenhouse/Ashby APIs (source review recorded); corpus now 17 companies / 11,223 postings. Peers are included in weekly snapshots.
- Five similarity measures (skills, role mix, TF-IDF, Sentence-BERT embeddings, talent-pool overlap) plus a combined score; heatmap, network graph and talent-pool chart.
- Findings: Anthropic and OpenAI are near-twins (0.99); an "LLM + go-to-market" bloc (Harvey, Perplexity, Cohere, Baseten); NVIDIA and Google sit apart; enterprise AEs are the most contested talent pool; 53% of xAI's postings are data-center build-out.
- 62 tests passing.

## Update — Sprint 9 done (2026-11-10)

- Researched 13 dated, cited public events (offices, funding, infrastructure) for Anthropic and OpenAI.
- Leading-indicator test: hiring led in 2 of 6 expansions (Singapore +154 d, Berlin +52 d), was simultaneous in 2 and lagged in 2; Series H funding was followed by +305 open roles in 26 weeks.
- Live watchlist of 5 unannounced new-city signals; Hiring Intelligence Report with a shared structure and company cards.
- 64 tests passing.

## Update — Sprint 10 done (2026-11-10)

- One scheduled pipeline in GitHub Actions (`refresh.yml`): full snapshot on Mondays, NVIDIA + Google on Thursdays, Internet Archive monthly; rebuild → score frozen forecast → export → commit. Collection failures are non-fatal; scheduled runs never freeze new forecasts.
- New context sources with source-register rows: SEC EDGAR (NVIDIA, Alphabet quarterly financials), Epoch AI notable models (207 releases), newsroom RSS (237 headlines), GDELT (rate-limited locally), EPO OPS patents (key pending), California WARN (0 matches).
- **AI Hiring Signals** console in `dashboard/`: globe of hubs and new-city arcs, signal feed, pulse with forecast bands, company deep-dives incl. hiring vs SEC financials, prediction tracker, market map. Static, served by Vercel.
- A new test caught a matcher bug (`opens?` matched inside "OpenAI"); fixed. 77 tests passing.
- Owner setup left: repository secrets and connecting Vercel to the repo.

## Update — story layer (2026-11-10)

- The console now opens with a briefing and one chapter per company. Rule-based evidence (themes from job titles, growth, lift vs peers, cities, corroborating news) is written up by a free open model (Groq gpt-oss-120b) and every number is checked against the evidence before publishing.
- EPO patents live: OpenAI +127%, NVIDIA +72%, Google −19% publications over the last 4 quarters.
- Headline findings: Anthropic government roles 6 → 25 and data-center roles 8 → 26 per 13 weeks (Austin's first posting is a data-center role); Google chip design concentrated in Tel Aviv/Haifa; OpenAI ads/shopping roles at 13× peers.
- 102 tests passing.
