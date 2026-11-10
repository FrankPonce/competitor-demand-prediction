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
  fetch on 2026-11-08, so Frank read it manually in a browser the same day. No blockers found.
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
  3. Full posting text is committed with its source URL (see the data-sharing
     decision under Legal requirements); remove on request.
  4. Re-check before each run that the board still doesn't link the nvidia.com
     Terms. If it starts linking them, stop automated collection and switch to
     the fallback.
- **Belt-and-braces:** Email NVIDIA recruiting asking them to confirm that
  non-commercial academic collection is fine. Not required to proceed.
- **Fallback:** Manually record a weekly sample of metadata (title, location,
  team, date seen) by browsing. The ToS restricts automated tools, not a
  person reading public pages.
- **Update 2026-11-09: full-board route.** The sitemap only lists the newest ~100
  postings, out of 2,800 open. The board's careers page loads its job list from
  `POST /wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs`, the same request every
  visitor's browser makes. This path is **not disallowed** by the board's robots.txt
  (RFC 9309: anything not disallowed is allowed), needs no login, and returns
  public listing fields (title, location, posted bucket, requisition ID). The list
  is capped at 2,000 results per query, so it is queried once per job-family facet.
  Descriptions still come from each job page's JSON-LD, **fetched once per new
  requisition** (known ones are carried forward). Same conditions: ≤1 request /
  2.5 s, robots.txt checked per URL, no nvidia.com pages, no application flow.
- **History:** the Internet Archive holds no captures of this board (checked
  2026-11-09), so NVIDIA's history comes from our own snapshots plus the
  requisition-ID sequence estimate (Sprint 5 addendum).

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
  non-commercial, and keep the source URL on every row.
- **Limit:** Coverage will be a filtered sample (e.g. AI/ML and engineering
  roles), not all of Google's postings. Document this in the Sprint 2 Data
  Collection Report.
- **Update 2026-11-09: unbiased sampling (v2).** The v1 keyword sample (AI/ML
  search terms) biased skill shares. v2 queries 26 hubs × 5 seniority levels with
  **no keywords**, newest-first, twice weekly. Same robots.txt rules (never
  `page=`); 130 requests per run.

### Peers (added in Sprint 8): approved

13 AI-market peers are collected through the **same documented public ATS APIs** as Anthropic and OpenAI:
- **Greenhouse:** xAI, Databricks, Scale AI, Together AI, Figure AI.
- **Ashby:** Cohere, Perplexity, Cursor, ElevenLabs, Harvey, Sierra, Decagon, Baseten.

One request per peer per snapshot; the companies' own websites are never contacted. Each board was checked
(2026-11-10) to belong to the named company, which names itself throughout its own postings. Same data-sharing
rules as all sources: source URL on every row, removed on request. Rows in the source register.

### Historical counts: Internet Archive (Wayback Machine)

- **Route:** archived copies of public careers pages via the Wayback CDX API and
  `web.archive.org/web/<timestamp>id_/<url>`. The companies' live sites are never
  contacted.
- **Why it's OK:** the Internet Archive's Terms of Use grant access to its
  collections "for scholarship and research purposes", which is this project's
  use. The CDX API is its documented machine interface. We request about 1 page
  every 4 s.
- **Data minimisation:** only one number per capture (the open-roles count) is
  extracted and stored. **No archived page content is kept**, locally or in git.
- **Coverage (2026-11-09):** Google careers results 2023–26, Anthropic Greenhouse
  board 2024–26. OpenAI's pages render jobs client-side (no counts recoverable).
  NVIDIA's board isn't archived.
- **Note on "keep it local":** not publishing data avoids *republishing* issues, but
  it does not make a collection method acceptable if the method itself breaks a
  site's terms. That's why history comes only from the research archive, never
  from re-crawling the companies' sites.

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
5. **Data sharing (decision 2026-11-08).** The collected datasets, including
   full posting text, are committed to the repo so reviewers can inspect and
   reproduce the work. Rationale: these are job adverts the companies publish
   openly to the general public; the project is non-commercial and academic;
   no personal data or confidential information is included; and every row
   keeps its source `job_url` for attribution. Any company or source owner who
   asks for removal gets their data taken out of the repo promptly. Epoch AI
   data is CC BY and is credited wherever it is used.
6. **Re-check before each collection run.** Terms and robots.txt change. Update
   `source-register.csv` when they do.

This is a documented good-faith review for an academic project, not legal advice.

## Collection plan for Sprint 2

| Item | Plan |
| ---- | ---- |
| Tooling | Python `requests` with small per-source collectors in `src/collect/`. `ats-scrapers` is optional for Greenhouse/Ashby, but the raw APIs are simple enough to call directly. Google and NVIDIA pages may need `playwright` because they render with JavaScript |
| Cadence | First snapshot in Sprint 2, then weekly (every Monday) through Sprint 12. NVIDIA also runs every Thursday (decided in Sprint 2) |
| Storage | `data/raw/<company>/<YYYY-MM-DD>.csv` snapshots and `data/processed/<company>.csv`, committed; raw API JSON dumps kept local for size |
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
- [x] Read OpenAI's terms of use manually (2026-11-08, no blockers)
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
- [OpenAI Terms of Use](https://openai.com/policies/terms-of-use/) (reviewed manually 2026-11-08)

---

[← Back to README](../../README.md)
