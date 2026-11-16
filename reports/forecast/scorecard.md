# Frozen Forecast Scorecard (generated)

Forecasts are frozen in `data/forecasts/frozen/` (committed, never edited) and scored here as actuals arrive. See [Sprint 7](../../docs/sprints/sprint-07-demand-forecasting.md).

**17 of 128 targets resolved** · overall 80%-interval coverage **71%** (target 80%) · realized skill vs naive **+21%**

| series                   |   targets |   mae |   naive_mae |   coverage80 |   skill_vs_naive |
|:-------------------------|----------:|------:|------------:|-------------:|-----------------:|
| anthropic_new            |         1 |  42.8 |        50   |            0 |            0.144 |
| anthropic_open           |         1 |   3.4 |         3   |            1 |           -0.133 |
| anthropic_open_compute   |         1 |   9.2 |         8   |            0 |           -0.15  |
| anthropic_open_corporate |         1 |   3.8 |         7   |            1 |            0.457 |
| anthropic_open_gtm       |         1 |   6.8 |         6   |            1 |           -0.133 |
| anthropic_open_product   |         1 |   1   |         0   |            1 |         -inf     |
| anthropic_open_research  |         1 |   2   |         2   |            1 |            0     |
| google_open              |         2 |  72   |       114   |            1 |            0.368 |
| nvidia_reqs              |         1 |  55.7 |        50.2 |            0 |           -0.11  |
| openai_new               |         1 |  48.9 |        60   |            0 |            0.185 |
| openai_open              |         1 |   4   |         2   |            1 |           -1     |
| openai_open_compute      |         1 |   2.6 |         2   |            1 |           -0.3   |
| openai_open_corporate    |         1 |   4.9 |         2   |            1 |           -1.45  |
| openai_open_gtm          |         1 |  13.3 |        16   |            0 |            0.169 |
| openai_open_product      |         1 |   6   |         4   |            1 |           -0.5   |
| openai_open_research     |         1 |   5.1 |         6   |            1 |            0.15  |
