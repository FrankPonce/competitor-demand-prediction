# Sprint 1 — Data Sources & Legal Review

**Project:** Competitor Demand Prediction Using Job Postings  
**Sprint:** 1  
**Status:** Research and planning; no job-posting data collected  
**Prepared by:** Frank Mediavilla  
**Team arrangement:** Solo execution proposed; coverage of all four companies requires CadetX approval

## Sprint goal

Identify the intended job-posting sources, document access and permission constraints, and agree on a compliant collection approach before downloading or scraping any listings.

## Scope and assumptions

The current analysis covers Google, OpenAI, NVIDIA, and Anthropic. The project programme is designed for a four-person team, with each member specializing in one company. A solo project covering all four companies is a proposed scope and is **not confirmed until CadetX approves it**.

No automated collection should begin for a source whose terms or permission status is unresolved. NVIDIA must not be scraped unless written authorization or an approved alternative route is obtained. Robots.txt is recorded as a technical access signal; it does not, by itself, grant permission or override site terms.

## Candidate source register

| Company   | Careers source / ATS noted      | Current finding                                                                                                                                                                                                                                                                          | Sprint 1 disposition                                                                                                                    |
| --------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Google    | Google Careers                  | Google’s terms restrict automated access that violates machine-readable instructions. The supplied robots.txt disallows certain Careers paths, including pagination and application-related paths. Compatibility of the planned scraper with permitted listing pages is not established. | **Restricted; unresolved.** Verify exact allowed paths and terms, and identify an approved collection method before access.             |
| OpenAI    | Ashby-hosted careers board      | The supplied robots.txt permits general crawling except `/microsoft-for-startups/`. Third-party collection permission has not been established.                                                                                                                                          | **Unresolved.** Review applicable terms and confirm a compliant method before collection.                                               |
| NVIDIA    | Workday-hosted careers board    | NVIDIA Terms of Service explicitly prohibit robots, scrapers, crawlers, or data-gathering tools from accessing site content.                                                                                                                                                             | **Prohibited for automated collection unless written permission is obtained.** Seek written approval or an approved alternative source. |
| Anthropic | Greenhouse-hosted careers board | The supplied robots.txt allows all paths. Third-party scraping permission has not been confirmed.                                                                                                                                                                                        | **Unresolved.** Review applicable terms and confirm a compliant method before collection.                                               |

Keep the detailed, updateable record in [`source-register.csv`](source-register.csv). Re-check source terms and access rules immediately before collection because they may change.

## Legal and ethical review procedure

For each source, record the review date and the exact source URL or document reviewed. Check:

1. The careers-site terms and any applicable ATS terms for restrictions on automated access, reuse, storage, or redistribution.
2. The site’s robots.txt for relevant user-agent rules, disallowed paths, and crawl-delay instructions.
3. Whether the proposed method is permitted and whether rate limits or written authorization are required.
4. Whether the dataset can be limited to public job-posting content, with personal information excluded.
5. Whether the data can be shared in the project repository. Do not commit raw data until permission and repository-sharing conditions are clear.
6. A decision and evidence note: **approved**, **restricted**, **prohibited**, or **unresolved**. Escalate uncertainty to CadetX rather than assuming access is allowed.

This document records project research, not legal advice. A robots.txt allowance is not equivalent to consent or a license.

## Collection method decision

The proposed primary tool is the open-source Python library **ats-scrapers** (MIT-licensed), which is reported to support Greenhouse, Ashby, and Workday. Tool support and licensing do not establish that a particular website permits collection. Verify the current package documentation, the relevant board’s terms, and the exact permitted endpoints before use.

Google Careers coverage is uncertain and must be investigated separately. Apify actors are only a possible fallback for technically difficult sources; they remain subject to the same permission checks and are not an authorization workaround. No collection tool or fallback is approved for NVIDIA at this stage.

## Dataset plan

If sources are cleared and CadetX confirms scope, create one consistent CSV per company, with an optional combined dataset. Use the programme’s required schema and preserve source identifiers and collection timestamps so listings can be deduplicated and snapshots compared. Do not represent a single snapshot as historical trend data: forecasting requires repeated, consistently collected snapshots or an approved historical source.

Proposed repository locations:

- `data/raw/` — source-preserving files, only when sharing and storage are permitted
- `data/processed/` — cleaned and standardized data
- `docs/` — this review and supporting documentation
- `src/` and `notebooks/` — collection and analysis code

Keep credentials, personal data, and any data that cannot be redistributed out of the public repository. Follow the project’s `.gitignore` and CadetX submission guidance.

## Sprint 1 deliverables and acceptance checklist

- [x] Record the four candidate companies and known ATS/source notes.
- [x] Record current access and permission status without treating robots.txt as permission.
- [x] Select a tentative collection tool and note its limits and fallback conditions.
- [x] Define the proposed per-company CSV approach and snapshot caveat.
- [ ] Obtain CadetX approval for solo coverage of all four companies.
- [ ] Complete terms and permission review for Google, OpenAI, and Anthropic.
- [ ] Obtain written NVIDIA authorization or agree on an approved alternative source.
- [ ] Verify Google Careers collection coverage and permitted routes.
- [ ] Record review dates, URLs, evidence, and decisions in `source-register.csv`.
- [ ] Confirm retention and repository-sharing rules before collecting or committing data.

**Sprint 1 exit condition:** Proceed to collection only for sources with a documented, approved route and confirmed project scope. Unresolved or prohibited sources remain out of collection.

## Handoff to Sprint 2

Sprint 2 planning should begin only after the scope and source decisions above are resolved. For each cleared company, document the collection endpoint or workflow, permitted request rate, timestamp strategy, schema mapping, deduplication key, and validation checks. If clearance is delayed, use the time to test the pipeline on synthetic data or another explicitly approved sample—not on restricted live sources.
