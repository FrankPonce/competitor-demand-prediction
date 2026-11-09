# Sprint 5 — Hiring Trend Analysis

**Week of:** 2026-12-07 (done early, 2026-11-09) · **CadetX task 5** · **Status:** ✅ Done

## Goal

Aggregate postings over time, measure hiring velocity, and find growth,
slowdowns and shifts, using one time-series structure shared by all four
companies.

## CadetX deliverables

- [x] Trend-analysis tables & visual summaries: [`data/trends/`](../../data/trends/) · [generated summary with charts](../../reports/trends/summary.md)
- [x] Short note on the key hiring patterns observed: [Key patterns](#key-patterns) below

## Shared time-series structure

Every company uses the same weekly frame ([`weekly_company.csv`](../../data/trends/weekly_company.csv)):

| Field | Meaning |
|---|---|
| `week` | Monday of the ISO week (complete weeks only) |
| `new_postings` | Postings **first seen** that week: the hiring flow |
| `closed` | Postings last seen that week that are no longer open |
| `active` | Postings open at any point in the week: the stock |
| `new_4wk_avg` | 4-week rolling mean of `new_postings`: the headline velocity |
| `net_change` | `new_postings − closed` |
| `hiring_velocity_bucket` | low / medium / high vs. the company's own weekly terciles |
| `scrape_days`, `low_coverage` | Data-quality flags (see Limitations) |

Per-posting fields from the brief are in [`posting_trend_fields.csv`](../../data/trends/posting_trend_fields.csv):
`posting_week`, `posting_month`, `hiring_velocity_bucket`, `emerging_skill_flag`.

**Validation:** our computed stock for Anthropic ends at 675 active postings,
against Epoch's own count of 673 open roles. The flow logic agrees with an
independent count.

## Key patterns

![Open roles](../../reports/trends/figures/open_roles.png)

**1. Both labs grew their open roles, Anthropic much faster.**
Between 2026-03-18 and 2026-11-02, Anthropic went from 442 to 673 open roles (+52%) and OpenAI from 630 to 811 (+29%).
New postings average about **42/week at Anthropic** and **53/week at OpenAI**. Most postings stay up about 40 days
(median 39 days at Anthropic, 41 at OpenAI).

![Weekly new postings](../../reports/trends/figures/weekly_new_postings.png)

**2. Anthropic paused, then surged.**
Anthropic's 4-week average fell to **22 new postings/week** in early August, then hit **77/week** by the end of August.
The by-category view shows where it went: go-to-market openings fell from 179 to 84 (Aug 8), then rose to 226 by late
October. Corporate roles doubled (80 → 194), and compute (34 → 86) and research (73 → 121) also climbed.
OpenAI's velocity was steadier (4-week average between 38 and 69).

![Open roles by category](../../reports/trends/figures/open_roles_by_category.png)

**3. OpenAI is building product and compute.**
OpenAI's product openings rose from 109 to 178 (peak 190) and compute from 65 to 111. Go-to-market grew too (221 → 283),
but as a *share of new postings* sales/GTM fell 3.5 pp. Marketing & communications (+2.8 pp), data center &
facilities (+1.8 pp) and ML/AI engineering (+1.7 pp) took that share.

![Role family shift](../../reports/trends/figures/role_family_shift.png)

**4. Anthropic's mix tilted to infrastructure and security:** Infrastructure & SRE +1.8 pp, Security & Privacy
+1.1 pp, Data Center & Facilities +1.1 pp. Safety/policy and marketing shares eased slightly
(−1.2 pp each) while their absolute counts still grew.

**5. Emerging skills point to physical build-out and the public sector.**
These are the skills that grew most in new postings between the first and last 13 weeks (Anthropic + OpenAI).
The flagged ones (≥ +2 pp and ≥1.5× growth) are:

| Skill | Early → recent share |
|---|---|
| Government & Public Sector | 6% → 9% |
| Data Center Design & Construction | 5% → 8% |
| Identity & Access | 2% → 5% |
| LLM APIs | 3% → 6% |
| Commissioning | 3% → 5% |

AI Agents (14% → 17%) and Account Management (12% → 15%) grew the most in absolute terms, but from a high base.

![Emerging skills](../../reports/trends/figures/emerging_skills.png)

**6. NVIDIA and Google: too early for a trend.**
Our two snapshots (Nov 8 and 9) show NVIDIA's sitemap turning over about 25–30 postings in a day, so it posts roughly
20+ roles a day. Google's published dates only cover roles still open, so older weeks look small because those
roles already closed (survivorship). These two companies get real weekly flows as snapshots accumulate.

## How it's built

`python -m src.trends.build_trends` ([code](../../src/trends/build_trends.py)) reads the Sprint 4 features plus
Epoch's daily open-role counts and writes:

| File | Content |
|---|---|
| `weekly_company.csv` | Weekly new / closed / active, 4-week average, velocity bucket, coverage flags |
| `epoch_open_roles_daily.csv` | Daily open roles by lab × category (Epoch AI, CC BY) |
| `monthly_role_family.csv` | New postings per month by role family |
| `role_family_shift.csv` | Role-family share of new postings, early vs. recent 13 weeks |
| `emerging_skills.csv` | Skill share change, early vs. recent, per company and combined, with `emerging_skill_flag` |
| `posting_lifetime.csv` | Median days open for closed postings, by company and role family |
| `nvidia_google_recent_published.csv` | Open postings by week published (NVIDIA, Google) |
| `posting_trend_fields.csv` | Per-posting `posting_week`, `posting_month`, `hiring_velocity_bucket`, `emerging_skill_flag` |

Charts use one fixed, colour-blind-checked colour per company (Anthropic blue, OpenAI orange, NVIDIA aqua,
Google yellow), with direct labels. Every chart has a table version in the summary.

## Snapshot #2 and pipeline hardening

The second snapshot (2026-11-09) ran into a temporary DNS outage. It was rerun, and the collector now:

- retries connection errors with backoff, and
- **refuses to save a snapshot when more than 5% of fetches fail**, because missing postings would otherwise be
  recorded as "closed".

The weekly merge now has real history: 1,170 Anthropic and 1,583 OpenAI postings are marked closed.

## Limitations

- **Epoch scrape gaps.** Daily scrapes skip some days (up to 8, e.g. Apr 2–10 and Aug 14–20). Postings published in a
  gap are first seen on the next scrape, so single weeks are lumpy (the Aug 17 week partly reflects catch-up).
  Use the 4-week average. Weeks with fewer than 4 scrape days are flagged `low_coverage`.
- **Left-censoring.** Everything open on 2026-03-18 counts as "first seen" that day, so that week is excluded
  from flows.
- **Current week excluded.** Only complete Monday–Sunday weeks are used.
- **`active` ≠ point-in-time open roles.** It counts postings open *at any point* in the week, so it runs a bit higher than
  Epoch's daily count.
- **NVIDIA "closed"** only means "dropped out of the newest-100 sitemap window", not necessarily filled.

---

[← Back to README](../../README.md)
