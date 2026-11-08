# Sprint 1 — Understanding Data Sources & Legal

**Project:** Competitor Demand Prediction Using Job Postings  
**CadetX task:** 1 (Sprint 1 of 12)  
**Status:** ✅ Done (source review 2026-11-08)  
**Prepared by:** Frank Mediavilla (solo; holds all four rotating roles)  
**Scope:** Google, OpenAI, NVIDIA, Anthropic

## Sprint goal

Identify a job-posting source for each company, document the legal and
ethical constraints, and agree on a compliant collection plan for Sprint 2.

CadetX Task 1 deliverables:

1. An approved list of data sources (see [Approved source list](#approved-source-list))
2. A clear understanding of legal requirements (see [Legal requirements](#legal-requirements))
3. A plan for data collection in Task 2 (see [Collection plan for Sprint 2](#collection-plan-for-sprint-2))

## Source categories considered

The brief names five source types:

| Source type | Finding |
| ----------- | ------- |
| Company careers pages / ATS boards | The main source for current postings at all four companies |
| Public ATS job-board APIs | Greenhouse (Anthropic) and Ashby (OpenAI) publish documented, unauthenticated JSON APIs for job listings. These are cleaner and lighter than HTML scraping |
| Public / open datasets | **Epoch AI "Data on Frontier Lab Hiring"** is a daily archive of Anthropic and OpenAI postings, licensed under Creative Commons Attribution. It covers our history gap for two companies |
| Kaggle / GitHub | Generic job datasets exist (e.g. LinkedIn/Glassdoor scrapes), but none is organized around these four companies and their licensing is often unclear. Not used as a primary source |
| Open-data portals | No relevant company-level coverage found |

## Approved source list

Reviewed 2026-11-08. Evidence is recorded in [`source-register.csv`](../source-register.csv).

### Anthropic: approved

- **Route:** Greenhouse Job Board API
  `GET https://boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true`
- **Why it's OK:** Greenhouse documents this API publicly. Its docs say job
  board data "is publicly available, so authentication is not required for any
  GET endpoints." The API exists so job listings can be shown outside the
  careers page. Anthropic's robots.txt allows all paths.
- **Caveat:** Anthropic's consumer terms prohibit scraping their "Services"
  (Claude.ai and associated websites). The Greenhouse API is Greenhouse
  infrastructure intended for this use. We use the API rather than scraping
  anthropic.com HTML.
- **History:** Epoch AI Frontier Lab Hiring archive (CC BY). Cite as: Epoch AI,
  "Data on Frontier Lab Hiring", epoch.ai.

### OpenAI: approved

- **Route:** Ashby Public Job Posting API
  `GET https://api.ashbyhq.com/posting-api/job-board/openai?includeCompensation=true`
  (confirm the board name `openai` from the jobs.ashbyhq.com URL in Sprint 2)
- **Why it's OK:** Ashby documents it as a public, unauthenticated API that
  returns `descriptionPlain`, `publishedAt`, location, department,
  employment type, and compensation. robots.txt on openai.com only disallows
  `/microsoft-for-startups/`.
- **Caveat:** openai.com/policies/terms-of-use returned HTTP 403 to automated
  fetch on 2026-11-08. Read it manually in a browser and note anything relevant.
- **History:** Epoch AI Frontier Lab Hiring archive (CC BY).

### NVIDIA: approved with conditions

- **Route:** Job pages listed in the Workday board's published sitemap
  `https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/siteMap.xml`
  (about 100 job URLs on 2026-11-08, with no `lastmod` dates)
- **Why it's OK:**
  - The board's own robots.txt (`nvidia.wd5.myworkdayjobs.com/robots.txt`)
    explicitly `Allow`s `/NVIDIAExternalCareerSite/` for all user agents and
    advertises the sitemap. Disallowed paths are `…Research/`,
    `/talentcommunity/`, `/NVIDIARecruitAds/`, and `/refreshFacet/`.
  - The nvidia.com Terms of Service (§3.2) ban robots and scrapers on "the
    Site". The terms define that as www.nvidia.com, rapids.ai, nventures.ai,
    jetson-ai-lab.com, and "other NVIDIA operated websites where these Terms
    are linked". The Workday board is hosted by Workday and **does not link
    those Terms**. Checked in a browser on 2026-11-08: the only legal link is
    the Applicant Privacy Policy.
- **Conditions:**
  1. Fetch only sitemap-listed job pages under `/NVIDIAExternalCareerSite/`.
     Never fetch disallowed paths, nvidia.com pages, or the application flow.
  2. Be gentle: at most 1 request every 2–3 seconds, once a week, with an
     identifying User-Agent.
  3. Do not republish full NVIDIA description text in the public repo. Commit
     derived fields (skills, categories, counts) only, and keep raw text local.
  4. Re-check before each run that the board still doesn't link the nvidia.com
     Terms. If it starts linking them, stop automated collection and switch to
     the fallback.
- **Belt-and-braces:** Email NVIDIA recruiting asking them to confirm that
  non-commercial academic collection is fine. Not required to proceed.
- **Fallback:** Manually record a weekly sample of metadata (title, location,
  team, date seen) by browsing. The ToS restricts automated tools, not a
  person reading public pages.

### Google: approved with conditions

- **Route:** Google Careers results pages **without any `page=` parameter**,
  plus individual job pages.
- **Why it's OK:** Google's Terms ban automated access only "in violation of
  the machine-readable instructions on our web pages", meaning robots.txt.
  Under `User-agent: *`, google.com/robots.txt disallows only:
  - `/about/careers/applications/candidate-prep`
  - `/about/careers/applications/connect-with-a-googler`
  - `/about/careers/applications/jobs/results` URLs that carry a `page=` parameter

  Unpaginated results pages and job detail pages are not disallowed.
- **Conditions:**
  1. Never request a URL containing `page=`. To cover more postings, narrow
     each query with filters (location, category, etc.) so the results fit on
     the first page.
  2. Never touch application, candidate-prep, or connect-with-a-googler paths.
  3. Same politeness and raw-text rules as NVIDIA.
- **Caveat:** Google's terms also list "scraping content that doesn't belong to
  you" as grounds for suspension. Keep the volume small, keep it
  non-commercial, and don't republish raw text.
- **Limit:** Coverage will be a filtered sample (e.g. AI/ML and engineering
  roles), not all of Google's postings. Document this in the Sprint 2 Data
  Collection Report.

## Legal requirements

Rules followed for every source:

1. **Terms first, robots.txt second.** Read the site terms and any ATS terms,
   and check robots.txt for the exact paths used. robots.txt is a
   machine-readable instruction. It is not a license.
2. **Prefer documented APIs over HTML scraping** wherever one exists.
3. **No personal data.** Collect posting content only. No recruiter or employee
   names, emails, or phones, and nothing from application flows. Strip any
   contact details found inside descriptions during preprocessing.
4. **Low impact.** Weekly cadence, rate-limited, identifying User-Agent, and no
   bypassing of logins, CAPTCHAs, or blocks.
5. **Copyright and redistribution.** Job descriptions are copyrighted text.
   Raw text stays out of the public repo (`data/raw/` is gitignored), and only
   derived features and aggregates are committed. Epoch AI data is CC BY, so it
   is redistributable with attribution.
6. **Re-check before each collection run.** Terms and robots.txt change. Update
   `source-register.csv` when they do.

This is a documented good-faith review for an academic project, not legal advice.

## Collection plan for Sprint 2

| Item | Plan |
| ---- | ---- |
| Tooling | Python `requests` with small per-source collectors in `src/collect/`. `ats-scrapers` is optional for Greenhouse/Ashby, but the raw APIs are simple enough to call directly. Google and NVIDIA pages may need `playwright` because they render with JavaScript |
| Cadence | First snapshot in Sprint 2, then weekly (every Monday) through Sprint 12. NVIDIA also runs every Thursday (decided in Sprint 2) |
| Storage | `data/raw/<company>/<YYYY-MM-DD>.json`, gitignored |
| Schema | Map every source to [`docs/data-dictionary.md`](../data-dictionary.md) and write `data/processed/<company>.csv` |
| Dedup key | `job_id` = `<company>-<source id>` (Greenhouse id, Ashby id, Workday `JR…` requisition, Google job id) |
| Dates | Use the source's publish date where one exists (Greenhouse `updated_at`/`first_published`, Ashby `publishedAt`). Otherwise use `first_seen_date` from snapshots |
| History | Download the Epoch AI CSVs for Anthropic and OpenAI and keep the attribution |
| Validation | Required fields non-null, unique `job_id`, URL reachable, no emails or phone numbers in text |
| Report | One Data Collection Report per company (sources, legal checks, fields, limitations) |

## Sprint 1 checklist

- [x] Four companies chosen and ATS/source identified
- [x] Terms and robots.txt reviewed for all four (2026-11-08)
- [x] Route found for each company, conditions documented
- [x] Historical source found for Anthropic and OpenAI (Epoch AI, CC BY)
- [x] Legal requirements and data-handling rules written
- [x] Collection plan for Sprint 2 written
- [x] Source register filled in
- [ ] Read OpenAI's terms of use manually (automated fetch was blocked)
- [ ] Optional: email NVIDIA recruiting for confirmation
- [x] Write the Sprint 1 weekly note (`docs/weekly-notes/week-01.md`)
- [ ] Push to GitHub and submit the repo link in the CadetX portal

## Sources

- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Ashby Public Job Posting API](https://developers.ashbyhq.com/docs/public-job-posting-api)
- [Epoch AI: Frontier Lab Hiring](https://epoch.ai/data/frontier-lab-hiring) · [documentation](https://epoch.ai/data/frontier-lab-hiring-documentation)
- [NVIDIA Terms of Service](https://www.nvidia.com/en-us/about-nvidia/terms-of-service/)
- [NVIDIA Workday robots.txt](https://nvidia.wd5.myworkdayjobs.com/robots.txt) · [sitemap](https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/siteMap.xml)
- [Google Terms of Service](https://policies.google.com/terms) · [google.com/robots.txt](https://www.google.com/robots.txt)
- [Anthropic Consumer Terms](https://www.anthropic.com/legal/consumer-terms)
- [OpenAI Terms of Use](https://openai.com/policies/terms-of-use/) (manual review pending)

---

[← Back to README](../../README.md)
