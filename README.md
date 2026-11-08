# Competitor Demand Prediction Using Job Postings

A CadetX Virtual Work Experience project exploring job-posting data to identify
skill trends, hiring demand, and shifts in the technology market.

## Status

Task 1 — Understanding Data Sources & Legal (in progress)

## Team arrangement

The CadetX brief is designed for a team of four, one company specialist each,
with four weekly rotating roles. This project is being carried out **solo** by
Frank Mediavilla, who holds all four roles (Scrum Leader, Data Quality Lead,
Documentation Lead, Technical Lead) and covers all four companies. Work is
asynchronous; weekly notes in `docs/weekly-notes/` stand in for the team meeting
minutes.

## Target companies

- Google
- OpenAI
- NVIDIA
- Anthropic

## Data collection

No job-posting data has been collected yet. Sources and access routes were
reviewed on 2026-11-08 (details in `docs/sprint-01-data-sources-legal.md` and
`docs/source-register.csv`):

| Company | Current postings route | Historical route |
| ------- | ---------------------- | ---------------- |
| Anthropic | Greenhouse public Job Board API | Epoch AI Frontier Lab Hiring archive (CC BY) |
| OpenAI | Ashby public Job Posting API | Epoch AI Frontier Lab Hiring archive (CC BY) |
| NVIDIA | Workday board sitemap (robots.txt allows the path) | Own weekly snapshots |
| Google | Google Careers results pages without pagination + job pages | Own weekly snapshots |

## Repository structure

- `docs/` — task documents, weekly notes, source register, and data dictionary
- `data/raw/` — approved source data; excluded from Git until reuse rights are confirmed
- `data/processed/` — cleaned or derived data; excluded from Git by default
- `notebooks/` — exploratory analysis
- `src/` — reusable processing and modelling code
- `reports/` — findings and written deliverables
- `presentations/` — final presentation materials

## Data handling

Do not collect personal or sensitive information. Preserve source URLs and
collection dates in project documentation. Do not publish job-description text
or datasets unless the relevant permissions allow it.

## Project plan

All 12 CadetX tasks (the 10 core tasks plus both optional ones) are planned
as 12 weekly sprints. The two optional tasks come before the final
presentation so it can include them. Each sprint ends with work pushed to this
repository and the repo link submitted in the CadetX portal.

| Sprint | Week of | CadetX task | Deliverables | Status |
| ------ | ------- | ----------- | ------------ | ------ |
| 1  | 2026-11-09 | 1 · Understanding Data Sources & Legal | Approved source list; legal requirements; collection plan | In progress |
| 2  | 2026-11-16 | 2 · Data Collection | Data Collection Report per company; raw dataset; **weekly snapshots start** | Not started |
| 3  | 2026-11-23 | 3 · NLP Preprocessing & Method Selection | Cleaned text; documented preprocessing workflow + code | Not started |
| 4  | 2026-11-30 | 4 · Skill Extraction & Feature Engineering | Extracted-skills dataset, feature tables, shared skill taxonomy | Not started |
| 5  | 2026-12-07 | 5 · Hiring Trend Analysis | Weekly/monthly trend tables and visuals; hiring-pattern note | Not started |
| 6  | 2026-12-14 | 6 · Competitor Comparison | Comparison tables and visuals; per-company explanation | Not started |
| 7  | 2026-12-21 | 7 · Demand Forecasting | Forecast outputs and plots; model choice rationale | Not started |
| 8  | 2026-12-28 | 8 · Company Similarity Scoring | Similarity tables, heatmaps/network graphs; drivers explanation | Not started |
| 9  | 2027-01-04 | 9 · Insight Generation & Reporting | Insight report and visuals; hiring-strategy explanation | Not started |
| 10 | 2027-01-11 | Optional · Automated Pipeline | Scheduled end-to-end pipeline (GitHub Actions/cron) + docs | Not started |
| 11 | 2027-01-18 | Optional · Fine-tune Skill Extraction Model | Fine-tuned BERT/RoBERTa/spaCy model + evaluation metrics | Not started |
| 12 | 2027-01-25 | 10 · Final Presentation & Mentor Review | Final presentation; clean, complete repository | Not started |

Sprint documents live in `docs/` (for example `docs/sprint-01-data-sources-legal.md`).
Weekly notes live in `docs/weekly-notes/`.

**Forecasting caveat:** Sprints 5 and 7 need data over time. A one-off
snapshot is not a time series. Two things cover this. For Anthropic and
OpenAI, the Epoch AI archive supplies history. For NVIDIA and Google, weekly
snapshots start in Sprint 2, which gives roughly 5 points by Sprint 7 and 10
by the end. Forecasts for those two will be short-horizon and clearly labelled
as limited.
