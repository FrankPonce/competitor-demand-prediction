# Data Collection Report — Google

**Sprint 2 · CadetX Task 2** · First snapshot: 2026-11-08 · Collector: [`src/collect/google_careers.py`](../../src/collect/google_careers.py)

## Source

| Source | What it gives | Access |
|---|---|---|
| Google Careers results pages `google.com/about/careers/applications/jobs/results?q=…&location=…&target_level=…&sort_by=date`, **first page only** | Up to 20 postings per query, with full data embedded in the page: title, about-the-job, responsibilities, qualifications, locations, timestamps, brand (Google / DeepMind / YouTube) | Allowed by robots.txt. **257 requests per snapshot, 1 every 3 s (~13 min)** |

## Legal checks

- Google's Terms ban automated access only "in violation of the machine-readable instructions on our web pages" (robots.txt).
- google.com/robots.txt (`User-agent: *`) disallows careers results URLs with `page=`, plus the candidate-prep and connect-with-a-googler paths. The collector:
  - checks every URL with an RFC 9309 wildcard-aware robots matcher,
  - hard-refuses any URL containing `page=`,
  - never fetches job detail or application pages, because the results page already contains the data.
- Google's Terms also list "scraping content that doesn't belong to you" as grounds for suspension. Volume is kept small and non-commercial, and every row keeps its source URL.
- No personal data. Contacts are auto-scrubbed.

Full review: [Sprint 1](../../docs/sprints/sprint-01-data-sources-legal.md#google-approved-with-conditions)

## Sampling design

Pagination is off-limits, so the snapshot is a **deliberate sample**:

- **8 keywords:** machine learning, large language model, generative AI, deep learning, TPU, data scientist, AI research, ML infrastructure
- **8 locations:** Mountain View, San Francisco, New York, Seattle, London, Zurich, Bangalore, Tokyo
- **4 seniority bands:** Early · Mid · Advanced · Lead + Director
- **sorted newest first**, so each slice's first page holds its most recent postings

That gives 8 × 8 × 4 = 256 slices. Run weekly, the newest-first ordering means new postings in each slice are captured even when the slice holds more than 20 jobs in total.

## What was collected

| | First snapshot |
|---|---|
| Unique postings | **579**, from 2,945 slice results (heavy overlap across keywords and locations) |
| Slices fully captured (total ≤ 20) | 143 of 256 |
| Slices truncated at the first page | 113, mostly big hubs (Mountain View, SF, NYC) × mid/advanced levels |
| Posting dates | 2023-03-09 → 2026-11-06 |
| Brands | Google 508 · DeepMind 43 · YouTube 28 |
| Median description | 3,664 chars |

## Fields

| Field | Filled | Source |
|---|---:|---|
| `job_id` | 100% | `google-<job id>` |
| `job_title` | 100% | embedded data [1] |
| `job_description` | 100% | about-the-job + responsibilities + qualifications |
| `posting_date` | 100% | embedded timestamp [12] (inferred meaning; see limitations) |
| `location` | 100% | embedded locations [9] |
| `job_url` | 100% | `…/jobs/results/<id>` |
| `department` | 100% | brand (Google / DeepMind / YouTube) |
| `employment_type`, `remote_type`, `salary_range` | 0% | not separate fields; salary for US roles is in the text (Sprint 4) |

## Limitations

- **A sample, not a census.** It covers AI/ML-flavoured roles in 8 hubs, so Google's absolute posting counts are not comparable to the full-board counts for Anthropic and OpenAI. Cross-company comparisons should use shares and rates, or restrict all four companies to the same AI/ML role families.
- The embedded data is a positional array. Field meanings were inferred on 2026-11-08 and could change without notice, so the validator will flag it if they break.
- Timestamp [12] is treated as the posting date; [14] is treated as last updated.
- Newest-first capture can still miss postings in very busy slices if more than 20 new ones appear in a week. The truncated-slice count in the run log tracks this.

## Update 2026-11-09: unbiased sampling (v2)

The keyword sample above inflated exactly the skills its search terms named (GenAI, LLM, TPU). v2 drops
keywords: **26 global hubs × 5 seniority levels**, newest first, run twice a week. The first v2 run returned
**917 postings**. For every slice, `covered_days` (how far back the 20 newest postings reach) exceeded 3.5 days,
so the twice-weekly cadence captures each slice's **entire** new-posting flow (126/130 even at weekly cadence).
Google is now an unbiased *flow* sample. It is still not a census of the open stock; the Internet Archive history
provides the board total instead (about 3,200–3,800 open roles in 2026).
