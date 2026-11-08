# Weekly Notes — Week 1 (2026-11-08)

**Attendees:** Frank Mediavilla (solo: Scrum Leader, Data Quality Lead, Documentation Lead, Technical Lead)
**Current sprint:** Sprint 1 — Task 1, Understanding Data Sources & Legal

## Progress this week

- Aligned the plan to the CadetX brief: 10 core tasks plus 2 optional, scheduled as 12 weekly sprints.
- Reviewed terms and robots.txt for Google, OpenAI, NVIDIA, and Anthropic.
- Found a compliant route for each company (Greenhouse API, Ashby API, NVIDIA Workday sitemap, Google unpaginated pages).
- Found the Epoch AI Frontier Lab Hiring archive (CC BY) as historical data for Anthropic and OpenAI.
- Filled in the source register and data dictionary.

## Decisions

- Scope: all four original companies.
- Prefer documented public APIs over HTML scraping.
- Raw description text stays local; only derived features are committed.
- Weekly snapshots start in Sprint 2 so a time series exists for NVIDIA and Google.

## Blockers / open questions

- OpenAI terms of use page blocked automated fetch; read it manually.
- Google coverage will be a filtered sample because pagination is disallowed.

## Data quality check (Data Quality Lead)

- No data collected yet. Validation rules are defined in the Sprint 1 doc (collection plan).

## Technical notes (Technical Lead)

- NVIDIA and Google pages render with JavaScript, so Playwright may be needed.

## Next steps

- [ ] Read OpenAI terms manually
- [ ] Push repo and submit Task 1 link in CadetX portal
- [ ] Sprint 2: build collectors in `src/collect/`, take the first snapshot, write the Data Collection Reports
