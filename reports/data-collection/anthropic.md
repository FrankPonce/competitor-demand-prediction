# Data Collection Report — Anthropic

**Sprint 2 · CadetX Task 2** · First snapshot: 2026-11-08 · Collector: [`src/collect/greenhouse.py`](../../src/collect/greenhouse.py)

## Sources

| Source | What it gives | Access |
|---|---|---|
| Greenhouse Job Board API, `boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true` | All currently open postings, full description | Public, documented, no auth. **1 request per snapshot** |
| Epoch AI "Data on Frontier Lab Hiring" (zip) | Daily-scraped history since 2026-03-18 with first/last seen and full text | CC BY, with attribution |

## Legal checks

- Greenhouse documents the Job Board API as public ("authentication is not required for any GET endpoints").
- anthropic.com/robots.txt allows all paths. Anthropic's consumer terms prohibit scraping their *Services*. We don't touch anthropic.com; the API is Greenhouse infrastructure intended for exactly this.
- Epoch AI data is CC BY. Attribution is in the README and here.
- No personal data. Emails and phone numbers in descriptions are auto-scrubbed. Raw text stays local (gitignored).

Full review: [Sprint 1](../../docs/sprints/sprint-01-data-sources-legal.md#anthropic-approved)

## What was collected

| | Live snapshot | Epoch history (Anthropic + OpenAI) |
|---|---|---|
| Postings | **675** open | 4,111 total (1,485 open, 2,626 closed) |
| Date range | first published 2024-04-22 → 2026-11-06 | first seen 2026-03-18 → 2026-10-31 |
| Median description | 8,557 chars | 7,319 chars |

Top departments (live): Sales 122 · AI Research & Engineering 74 · Applied AI 69 · Security 54 · Finance 51 · Product Eng & Design 49 · Infrastructure 37 · Safeguards 36

## Fields

| Field | Filled | Source field |
|---|---:|---|
| `job_id` | 100% | `anthropic-<greenhouse id>` |
| `job_title` | 100% | `title` |
| `job_description` | 100% | `content` (HTML → text) |
| `posting_date` | 100% | `first_published` |
| `location` | 100% | `location.name` |
| `job_url` | 100% | `absolute_url` |
| `department` | 100% | `departments[].name` |
| `remote_type` | 92% | metadata "Location Type" + location text |
| `employment_type` | 0% | not exposed by the API |
| `salary_range` | 0% | not a separate field (often inside the description text; extract in Sprint 4) |

## Limitations

- `first_published` reflects the latest (re)publish, so long-running reposted roles can look newer than they are. Epoch first-seen dates and our own `first_seen_date` correct for this over time.
- Salary appears only inside the description text.
- Epoch history starts 2026-03-18 (about 8 months), with a 7-day publication delay.
