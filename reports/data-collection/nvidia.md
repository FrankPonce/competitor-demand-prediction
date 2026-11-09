# Data Collection Report — NVIDIA

**Sprint 2 · CadetX Task 2** · First snapshot: 2026-11-08 · Collector: [`src/collect/nvidia_workday.py`](../../src/collect/nvidia_workday.py)

## Source

| Source | What it gives | Access |
|---|---|---|
| Workday board sitemap `nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/siteMap.xml` → each job page's JSON-LD `JobPosting` | The ~100 most recent postings: title, full description, date posted, location, employment type | Path allowed by the board's robots.txt. **101 requests per snapshot, 1 every 3 s (~5 min)** |

## Legal checks

- The board's robots.txt `Allow`s `/NVIDIAExternalCareerSite/` for all agents and advertises the sitemap. Every URL is checked against it before fetching.
- nvidia.com Terms of Service §3.2 prohibit scrapers on "the Site": nvidia.com, rapids.ai, nventures.ai, jetson-ai-lab.com, and NVIDIA-operated sites *where the Terms are linked*. The Workday-hosted board does **not** link them (browser check 2026-11-08: the only legal link is the Applicant Privacy Policy). No nvidia.com pages are fetched.
- Conditions: sitemap-listed job pages only, slow rate, no application flow, source URL kept on every row, and stop if the board starts linking the nvidia.com Terms.
- No personal data. Contacts are auto-scrubbed.

Full review: [Sprint 1](../../docs/sprints/sprint-01-data-sources-legal.md#nvidia-approved-with-conditions)

## What was collected

| | First snapshot |
|---|---|
| Postings | **100** (all sitemap URLs; 0 fetch errors) |
| Date posted | 2026-11-05 → 2026-11-09 |
| Median description | 4,271 chars |

## Fields

| Field | Filled | Source field |
|---|---:|---|
| `job_id` | 100% | `nvidia-<JR requisition id>` |
| `job_title` | 100% | JSON-LD `title` |
| `job_description` | 100% | JSON-LD `description` |
| `posting_date` | 100% | JSON-LD `datePosted` |
| `location` | 100% | JSON-LD `jobLocation.address` |
| `job_url` | 100% | sitemap `<loc>` |
| `employment_type` | 100% | JSON-LD `employmentType` |
| `remote_type` | 14% | "Remote" in the URL location segment |
| `department` | 0% | not published; infer the team from title/description in Sprint 4 |
| `salary_range` | 0% | stated inside the description text (US roles); extract in Sprint 4 |

## Limitations and cadence decision

- **The sitemap only lists the ~100 newest postings.** Those 100 covered just 4–5 days, so NVIDIA posts roughly 20 roles a day. A weekly snapshot would miss postings.
  **Decision: run NVIDIA every 3 days** (`python -m src.collect.run_snapshot nvidia`). Each run is still about 100 gentle requests.
- This captures the *flow of new postings* well, but not the full stock of open roles. Closed-status detection is weaker, because a posting dropping off the sitemap only means it's no longer among the newest. Trend analysis for NVIDIA will use **new postings per week** as its main signal.
- There is no department field; it will be derived later.

## Update 2026-11-09: full board

The sitemap route above only ever saw the newest ~100 postings. It was replaced by the board's listing
endpoint (the same request the public careers page makes), queried once per job-family facet to stay under
the 2,000-per-query cap. Result: **2,799 of 2,800 open postings** with full descriptions (2,671 newly fetched,
129 carried forward), 0 errors. The open stock is now complete, so `closed` really means removed from the board.

Mix of the full board: Engineering 1,764 · Sales 328 · University (interns/new grads) 219 · Program
Management 114 · Operations 108 · Marketing 97 · IT 47 · Research 41.

Caveat: about 73% of open postings carry a posted date within the last six weeks, because NVIDIA refreshes
postings often. For history, use the requisition-ID estimate (Sprint 5 addendum), not posted dates.
