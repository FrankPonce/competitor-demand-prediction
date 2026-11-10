<div align="center">

<img src="assets/banner.svg" alt="Competitor Demand Prediction: hiring intelligence for Anthropic, OpenAI, NVIDIA and Google" width="100%">

<br>

![Status](https://img.shields.io/badge/status-Sprint%2010%20·%20Automated%20Pipeline-30363d?style=for-the-badge&labelColor=161b22)
![Progress](https://img.shields.io/badge/sprints-9%20%2F%2012%20done-b95115?style=for-the-badge&labelColor=161b22)
![Python](https://img.shields.io/badge/python-3.12-2d6ac1?style=for-the-badge&logo=python&logoColor=white&labelColor=161b22)
![Program](https://img.shields.io/badge/CadetX-Virtual%20Work%20Experience-5ea529?style=for-the-badge&labelColor=161b22)

[**Roadmap**](#-sprint-roadmap) · [**Data sources**](#-data-sources) · [**Quickstart**](#-quickstart) · [**Repo map**](#-repository-map) · [**Ethics**](#-data-ethics)

</div>

---

> 📄 **Start here: [Hiring Intelligence Report](reports/insights/insight_report.md)**, with the findings, company profiles and a test of whether job postings predict company moves.

## 🎯 Overview

Job postings show what a company plans to do before it shows up in
earnings reports or product launches. This project builds an end-to-end
hiring-intelligence pipeline:

```mermaid
%%{init: {'theme':'base','themeVariables':{'background':'#0d1117','primaryColor':'#161b22','primaryTextColor':'#e6edf3','primaryBorderColor':'#30363d','lineColor':'#6e7681','fontFamily':'Segoe UI, Inter, sans-serif'}}}%%
flowchart LR
    A[🔎 Collect<br/>weekly snapshots] --> B[🧹 Preprocess<br/>NLP cleaning]
    B --> C[🧩 Extract skills<br/>shared taxonomy]
    C --> D[📊 Trends<br/>hiring velocity]
    D --> E[🔮 Forecast<br/>demand]
    C --> F[🤝 Compare &<br/>similarity]
    E --> G[💡 Insights &<br/>presentation]
    F --> G
```

**Colour code** used in every chart and table: 🟠 **Anthropic** · 🟣 **OpenAI** · 🟢 **NVIDIA** · 🔵 **Google**

| | |
|---|---|
| **Problem** | Companies lack a systematic, data-driven way to read competitor hiring and anticipate demand. |
| **Goal** | Use external job-posting data to forecast competitor demand, skill trends, and market direction. |
| **Who it's for** | Strategy, HR & talent, product managers, CTOs, investors. |
| **Team** | Solo: [Frank Mediavilla](https://github.com/FrankPonce), rotating through Scrum Lead, Data Quality, Docs and Tech Lead roles. |
| **Timeline** | 12 weekly sprints · Nov 2026 → Jan 2027 |

**Latest signal:** Anthropic's open roles grew about **9× in two years** (≈74 → 667), Google's about +70% since 2023 with a clear yearly cycle ([Sprint 5](docs/sprints/sprint-05-hiring-trends.md)).

![Open roles history](reports/trends/figures/history_open_roles.png)

![Expansion map](reports/trends/figures/expansion_map.png)

**How they differ** ([Sprint 6](docs/sprints/sprint-06-competitor-comparison.md)): the skills each company over-indexes on, compared with the other three.

![Distinctive skills](reports/comparison/figures/distinctive_skills.png)

**Where they sit in the AI market** ([Sprint 8](docs/sprints/sprint-08-similarity-scoring.md)): 17 companies, linked to their 3 most similar.

![Similarity network](reports/similarity/figures/similarity_network.png)

---

## 🗺️ Sprint roadmap

All **10 CadetX tasks + both optional tasks** run as one sprint per week.
Click a sprint to see its goal, deliverables, and results.

| # | Sprint | Week of | Summary | Status |
|:-:|---|:-:|---|:-:|
| 01 | [**Data Sources & Legal**](docs/sprints/sprint-01-data-sources-legal.md) | Nov 9 | Reviewed terms + robots.txt for all four companies, found a compliant route for each, plus CC BY history for two | ✅ |
| 02 | [**Data Collection**](docs/sprints/sprint-02-data-collection.md) | Nov 16 | 4 collectors built; first snapshot of 2,170 postings + 4,111 historical; [Data Collection Reports](reports/data-collection/) | ✅ |
| 03 | [**NLP Preprocessing**](docs/sprints/sprint-03-nlp-preprocessing.md) | Nov 23 | Unified corpus (4,958 postings as of Nov 9); 23–54% boilerplate removed; sections, salary, spaCy lemmas; [summary](reports/preprocessing/summary.md) | ✅ |
| 04 | [**Skill Extraction**](docs/sprints/sprint-04-skill-extraction.md) | Nov 30 | 211-skill shared taxonomy; 45k skill mentions; role family, seniority, education features; 89% precision; [summary](reports/skills/summary.md) | ✅ |
| 05 | [**Hiring Trends**](docs/sprints/sprint-05-hiring-trends.md) | Dec 7 | Multi-year history (Internet Archive, validated within 1.2%), weekly velocity, expansion maps, untracked emerging signals, pay, NVIDIA requisition rate; [summary](reports/trends/summary.md) | ✅ |
| 06 | [**Competitor Comparison**](docs/sprints/sprint-06-competitor-comparison.md) | Dec 14 | Two-lens framework on full/unbiased data; Anthropic = safety + GTM, OpenAI = APIs/platform, NVIDIA = GPU/HPC/robotics stack, Google = Cloud sales + GenAI + management layer; [summary](reports/comparison/summary.md) | ✅ |
| 07 | [**Demand Forecasting**](docs/sprints/sprint-07-demand-forecasting.md) | Dec 21 | 16 series, 8-week horizon; rolling backtests (up to +32% vs naive); empirical intervals; forecasts **frozen** and scored weekly; [summary](reports/forecast/summary.md) · [scorecard](reports/forecast/scorecard.md) | ✅ |
| 08 | [**Similarity Scoring**](docs/sprints/sprint-08-similarity-scoring.md) | Dec 28 | Market map of 17 AI companies (+13 peers via public ATS APIs); 5 measures incl. Sentence-BERT; talent-pool overlap; [summary](reports/similarity/summary.md) | ✅ |
| 09 | [**Insights & Reporting**](docs/sprints/sprint-09-insights-reporting.md) | Jan 4 | **[Hiring Intelligence Report](reports/insights/insight_report.md)**, company cards, leading-indicator test vs 13 cited events (2 led, 2 simultaneous, 2 lagged) + live watchlist | ✅ |
| 10 | [**Automated Pipeline**](docs/sprints/sprint-10-automated-pipeline.md) <sub>optional</sub> | Jan 11 | One scheduled end-to-end pipeline | 🟡 |
| 11 | [**Fine-Tuned Skill Model**](docs/sprints/sprint-11-fine-tuning.md) <sub>optional</sub> | Jan 18 | BERT/RoBERTa token classifier vs. rule-based baseline | ⬜ |
| 12 | [**Final Presentation**](docs/sprints/sprint-12-final-presentation.md) | Jan 25 | Mentor review, final deck, polished repo | ⬜ |

<sub>✅ done · 🟡 in progress · ⬜ not started · Weekly notes live in <a href="docs/weekly-notes/">docs/weekly-notes/</a></sub>

---

## 🏢 Data sources

Each company has a documented, compliant route. Full evidence is in
[`source-register.csv`](docs/source-register.csv) and the
[Sprint 1 review](docs/sprints/sprint-01-data-sources-legal.md).

| Company | ATS | Current postings | History |
|---|---|---|---|
| 🟠 **Anthropic** | Greenhouse | [Job Board API](https://docs.greenhouse.io/job-board.html) (public, documented) | [Epoch AI](https://epoch.ai/data/frontier-lab-hiring) archive since Mar 2026 · CC BY |
| 🟣 **OpenAI** | Ashby | [Posting API](https://developers.ashbyhq.com/docs/public-job-posting-api) (public, documented) | [Epoch AI](https://epoch.ai/data/frontier-lab-hiring) archive since Mar 2026 · CC BY |
| 🟢 **NVIDIA** | Workday | Full board (2,800) via the careers page's own listing endpoint + job-page JSON-LD | Requisition-ID sequence estimate + own snapshots |
| 🔵 **Google** | Google Careers | Unpaginated results, 26 hubs × 5 levels, no keywords (unbiased flow sample) | Internet Archive open-role counts 2023–26 |

> [!NOTE]
> History comes from three places: Epoch AI (Anthropic/OpenAI daily since Mar 2026), Internet Archive
> captures (Google 2023–26, Anthropic 2024–26; counts only) and our own snapshots (all four, Mondays and
> Thursdays since 2026-11-08). NVIDIA history is estimated from its requisition-ID sequence.

**Latest snapshot · 2026-11-09** · corpus of **8,317** unique postings

| 🟠 Anthropic | 🟣 OpenAI | 🟢 NVIDIA | 🔵 Google | Epoch history |
|:-:|:-:|:-:|:-:|:-:|
| **675** | **813** | **2,799** | **917** | **4,114** |
| full board | full board | full board | unbiased sample | Mar → Nov 2026 |

---

## ⚡ Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

python -m src.collect.epoch_history          # Anthropic + OpenAI history (CC BY)
python -m src.collect.wayback_history        # Internet Archive open-role counts (Google, Anthropic)
python -m src.collect.run_snapshot           # weekly snapshot, all four companies
python -m src.collect.run_snapshot nvidia --limit 3   # quick test, saves nothing
python -m src.preprocess.build_corpus        # cleaned corpus -> data/processed/corpus/
python -m src.features.build_features       # skills + features -> data/features/
python -m src.trends.build_trends           # weekly trends + charts -> data/trends/, reports/trends/
python -m src.trends.emerging_terms         # rising phrases beyond the taxonomy
python -m src.trends.geo_pay                # footprint + expansion maps, pay trends
python -m src.trends.history                # multi-year history, NVIDIA requisition rate
python -m src.compare.build_comparison      # competitor comparison -> data/comparison/, reports/comparison/
python -m src.forecast.run_forecast         # backtest + 8-week forecasts (+ freezes once per day)
python -m src.forecast.report               # forecast charts + summary
python -m src.forecast.score_frozen         # score frozen forecasts against new actuals
python -m src.similarity.build_similarity   # 17-company similarity, embeddings, talent pools
python -m src.insights.leading_indicators   # hiring signals vs cited public events
python -m src.insights.company_cards        # one-page company cards
python -m pytest                             # 64 regression tests
```

Snapshots land in `data/raw/<company>/<date>.*`. Merged per-company datasets
(with `first_seen_date`, `last_seen_date`, `job_status`) go to
`data/processed/<company>.csv`. A text-free run log is committed to
[`reports/collection-log.csv`](reports/collection-log.csv).

---

## 📁 Repository map

```text
├── docs/
│   ├── sprints/              one page per sprint (goal · deliverables · results)
│   ├── weekly-notes/         weekly progress notes
│   ├── data-dictionary.md    shared schema for all four companies
│   └── source-register.csv   legal / access review evidence
├── src/
│   ├── collect/              collectors · validation · snapshot runner
│   ├── preprocess/           sections · boilerplate removal · spaCy · corpus builder
│   ├── features/             skill taxonomy · extractors · feature tables
│   ├── trends/               weekly flows · emerging skills · charts
│   ├── compare/              two-lens competitor comparison
│   ├── forecast/             series · models · backtest · frozen forecasts · scorer
│   ├── similarity/           5 similarity measures · Sentence-BERT · talent pools
│   └── insights/             leading indicators vs events · company cards
├── data/
│   ├── raw/                  weekly snapshot CSVs per company (full text)
│   ├── external/             Epoch AI download (CC BY)
│   ├── processed/            per-company datasets · Epoch history · corpus/ (cleaned, per company)
│   ├── features/             posting features · skills (long) · skill matrix
│   ├── trends/               weekly / monthly trend tables
│   ├── comparison/           company profiles · distinctive skills · mixes
│   ├── history/              Internet Archive counts · long-run series · NVIDIA requisition rate
│   ├── forecasts/            backtests · latest forecast · frozen/ (never edited) · scorecard
│   ├── similarity/           17×17 matrices · pairs · talent pools · role clusters
│   ├── events/               cited public events (offices, funding, infrastructure)
│   └── insights/             lead-lag · watchlist · funding response
├── tests/                    regression tests (compliance rules, parsing, skill matching)
├── assets/                   banner and visual identity
├── notebooks/                exploration & analysis
├── reports/                  run logs, collection reports, insight reports
└── presentations/            final deck
```

---

## 🛡️ Data ethics

- **Documented routes only.** Terms and robots.txt are reviewed per source and re-checked before runs. Public APIs are preferred over scraping.
- **Gentle.** Weekly cadence, rate-limited, with an identifying User-Agent. Never paginate where robots.txt forbids it.
- **No personal data.** Posting content only. Emails and phone numbers are scrubbed automatically.
- **Open data, with attribution.** Datasets are committed so the work can be inspected and reproduced. Every row keeps its source URL, and data is removed promptly if a source owner asks.
- **Attribution.** History for Anthropic and OpenAI comes from Epoch AI, "Data on Frontier Lab Hiring", [epoch.ai](https://epoch.ai/data/frontier-lab-hiring) (CC BY).

<div align="center">
<br>
<sub>Built for the CadetX Virtual Work Experience · Competitor Demand Prediction Using Job Postings</sub>
</div>
