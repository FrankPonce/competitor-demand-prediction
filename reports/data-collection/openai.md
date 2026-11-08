# Data Collection Report — OpenAI

**Sprint 2 · CadetX Task 2** · First snapshot: 2026-11-08 · Collector: [`src/collect/ashby.py`](../../src/collect/ashby.py)

## Sources

| Source | What it gives | Access |
|---|---|---|
| Ashby Public Job Posting API, `api.ashbyhq.com/posting-api/job-board/openai?includeCompensation=true` | All listed open postings with plain-text description, publish date, compensation | Public, documented, no auth. **1 request per snapshot** |
| Epoch AI "Data on Frontier Lab Hiring" (zip) | Daily-scraped history since 2026-03-18 with first/last seen and full text | CC BY, with attribution |

## Legal checks

- Ashby documents the posting API as public, with no authentication.
- openai.com/robots.txt disallows only `/microsoft-for-startups/`. We don't fetch openai.com pages at all.
- OpenAI's terms of use page blocked automated fetching (HTTP 403). **A manual read is still pending.**
- Postings with `isListed: false` (direct-link only) are skipped to respect the board's intent.
- No personal data. Contacts are auto-scrubbed and raw text stays local.

Full review: [Sprint 1](../../docs/sprints/sprint-01-data-sources-legal.md#openai-approved)

## What was collected

| | Live snapshot |
|---|---|
| Postings | **816** open |
| Date range | published 2023-05-25 → 2026-11-08 |
| Median description | 6,880 chars |

Top departments: Go To Market 169 · Applied AI 119 · Scaling 105 · Research 53 · User Operations 50 · Marketing 43 · Forward Deployed Engineering 37 · Security 31

History: shared Epoch AI archive (see the [Anthropic report](anthropic.md)).

## Fields

| Field | Filled | Source field |
|---|---:|---|
| `job_id` | 100% | `openai-<ashby uuid>` |
| `job_title` | 100% | `title` |
| `job_description` | 100% | `descriptionPlain` |
| `posting_date` | 100% | `publishedAt` |
| `location` | 100% | `location` + `secondaryLocations` |
| `job_url` | 100% | `jobUrl` |
| `employment_type` | 100% | `employmentType` |
| `department` | 100% | `department` |
| `salary_range` | 80% | `compensation.compensationTierSummary` |
| `remote_type` | 71% | `workplaceType` / `isRemote` |

## Limitations

- `publishedAt` is the *last* publish time, so reposts reset it. Use first-seen dates for velocity.
- Unlisted postings are excluded by design.
- The manual OpenAI terms read is still outstanding.
