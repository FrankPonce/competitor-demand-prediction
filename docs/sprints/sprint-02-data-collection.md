# Sprint 2 — Data Collection

**Week of:** 2026-11-16 (started early, 2026-11-08) · **CadetX task 2** · **Status:** ✅ Done (snapshots continue on schedule)

## Goal

Collect job-posting data for all four companies using only the routes approved
in [Sprint 1](sprint-01-data-sources-legal.md). Start the weekly snapshot series
that later sprints use as a time series.

## CadetX deliverables

- [x] Data Collection Report per company (sources, legal checks, fields, limitations)
  - [Anthropic](../../reports/data-collection/anthropic.md) · [OpenAI](../../reports/data-collection/openai.md) · [NVIDIA](../../reports/data-collection/nvidia.md) · [Google](../../reports/data-collection/google.md)
- [x] Raw collected dataset, committed with full text:
  - weekly snapshots: [`data/raw/<company>/`](../../data/raw/)
  - merged per-company datasets: [`data/processed/`](../../data/processed/)
  - Epoch AI history: [`data/processed/epoch_history.csv`](../../data/processed/epoch_history.csv)

## What was built

| File | Purpose |
|---|---|
| [`common.py`](../../src/collect/common.py) | Polite HTTP session (identifying User-Agent, fixed delay, retries), RFC 9309 robots.txt matcher with wildcard support, HTML → text, contact scrubbing |
| [`greenhouse.py`](../../src/collect/greenhouse.py) | Anthropic via Greenhouse Job Board API |
| [`ashby.py`](../../src/collect/ashby.py) | OpenAI via Ashby Posting API |
| [`nvidia_workday.py`](../../src/collect/nvidia_workday.py) | NVIDIA via sitemap job pages → JSON-LD `JobPosting` |
| [`google_careers.py`](../../src/collect/google_careers.py) | Google via unpaginated, newest-first results slices; reads embedded job data |
| [`epoch_history.py`](../../src/collect/epoch_history.py) | Epoch AI CC BY history for Anthropic and OpenAI |
| [`validate.py`](../../src/collect/validate.py) | Required fields, unique IDs, date format, no emails, https URLs |
| [`run_snapshot.py`](../../src/collect/run_snapshot.py) | Runs collectors, saves raw + snapshot, merges snapshots (first/last seen, status), appends the run log |
| [`report_stats.py`](../../src/collect/report_stats.py) | Markdown stats for reports and weekly notes |

Every URL is checked against the site's robots.txt before fetching. The Google
collector also hard-refuses any URL containing `page=`.

## First snapshot (2026-11-08)

| Company | Postings | Requests | Validation issues | Notes |
|---|---:|---:|---:|---|
| Anthropic | 675 | 1 | 0 | Full board |
| OpenAI | 816 | 1 | 0 | Full board (listed postings) |
| NVIDIA | 100 | 102 | 0 | Newest ~100 postings (4–5 days' worth) → **run every 3 days** |
| Google | 579 | 257 | 0 | AI/ML sample; 143 of 256 slices complete |
| Epoch history | 4,111 | 1 | — | Anthropic + OpenAI, 2026-03-18 → 2026-10-31, 2,626 closed |

**2,170 current postings plus 4,111 historical postings, all with full description text, and no validation issues.**

Run log (text-free, committed): [`reports/collection-log.csv`](../../reports/collection-log.csv)

## Decisions

- **APIs over scraping** for Anthropic and OpenAI. Each takes one request per snapshot.
- **NVIDIA uses the JSON-LD** embedded in each job page. That is the structured data the page publishes for search engines, so no JavaScript rendering is needed.
- **Google uses newest-first slices.** Pagination is disallowed, so each query is a narrow keyword × location × seniority slice sorted by date. Run weekly, this catches most *new* AI/ML postings in each slice. It is a deliberate sample, not a census.
- **Datasets are committed with full text** so reviewers can inspect them (see the [Sprint 1 data-sharing decision](sprint-01-data-sources-legal.md#legal-requirements)). Raw API JSON dumps stay local because they duplicate the CSVs and are large.
- **Test runs (`--limit`) never write snapshot CSVs**, so they can't pollute the time series.

## Update (2026-11-09): coverage fixes after the project review

| Company | Before | After |
|---|---|---|
| 🟢 NVIDIA | Sitemap: newest ~100 of the board | **Full board (2,800 postings)** via the listing endpoint the careers page itself calls, queried per job-family facet (2,000-per-query cap). Descriptions fetched once per *new* requisition. First backfill: 2,822 requests, 0 errors |
| 🔵 Google | 8 AI/ML keywords × 8 hubs × 4 levels (keyword-biased) | **26 hubs × 5 levels, no keywords** (v2), newest first, twice weekly. First run: 917 postings; **130/130 slices** capture their full new-posting flow at twice-weekly cadence |
| History | Epoch only (Anthropic/OpenAI, from Mar 2026) | + Internet Archive counts: Google 2023–26, Anthropic 2024–26 (validated against Epoch: 1.2% mean error) |

Safeguards added: snapshots are refused if more than 5% of detail fetches fail **or** the listing covers
less than 95% of the board's stated total. Google postings that drop out of the top 20 are marked
`unknown`, not `closed`.

## Collection routine (until Sprint 12)

1. Re-check the source register: the robots.txt files, and whether the NVIDIA board now links nvidia.com's terms.
2. **Every Monday:** `python -m src.collect.run_snapshot` (all four companies).
   **Plus every Thursday:** `python -m src.collect.run_snapshot nvidia google` (Google v2 slices are sized for a twice-weekly cadence; NVIDIA keeps closures accurate).
3. Skim the console for validation issues and check `reports/collection-log.csv`.
4. Note the counts in the weekly note.

## Open items

- [x] Read OpenAI's terms of use manually (done 2026-11-08, no blockers)
- [ ] Second snapshot on 2026-11-16 to confirm the merge (first/last seen, closed status) works across weeks

---

[← Back to README](../../README.md)
