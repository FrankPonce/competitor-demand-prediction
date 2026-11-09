# Weekly Notes — Week 2 (2026-11-09)

**Attendees:** Frank Mediavilla (solo: Scrum Leader, Data Quality Lead, Documentation Lead, Technical Lead)
**Current sprint:** Sprint 3 — Task 3, NLP Preprocessing & Method Selection (running ahead of schedule)

## Progress this week

- Task 2 closed: full-text datasets committed, OpenAI terms reviewed manually.
- Built the preprocessing pipeline (`src/preprocess/`) and a unified corpus of 4,909 postings (live + Epoch history, deduplicated).
- Boilerplate removal strips 23–54% of raw text per company; section detection finds requirements in 90–100% of postings.

## Decisions

- Keep two text forms: `clean_text` (for embeddings and skill matching) and `cleaned_description` (lemmas for TF-IDF).
- Data-driven boilerplate detection per company, with a guard that keeps real requirements.
- Full corpus stored as Parquet (35 MB); a CSV sample is provided for browsing.

## Blockers / open questions

- None.

## Data quality check (Data Quality Lead)

- 7 non-English or bilingual postings flagged (EU roles), kept but labelled.
- NVIDIA's sample (100) is small, so its boilerplate detection is the noisiest.

## Technical notes (Technical Lead)

- spaCy `en_core_web_sm` with parser and NER disabled: about 3–6 minutes for the full corpus.

## Next steps

- [ ] Thursday: NVIDIA snapshot. Monday: full snapshot.
- [ ] Sprint 4: skill taxonomy + extraction.

## Update — Sprint 4 done (2026-11-09)

- Built a shared 211-skill / 19-category taxonomy and section-aware extractor (`src/features/`).
- 45,482 skill mentions across 4,909 postings; role family, seniority, years and education features added.
- Precision spot-check: 89/100 random matches correct; two error types fixed afterwards.
- Early signal: Anthropic and OpenAI are about 30% sales/GTM hiring; NVIDIA postings are 86% hardware/accelerator skills; Google's AI sample mentions a PhD 44% of the time.

## Update — Sprint 5 done (2026-11-09)

- Snapshot #2 taken. A DNS outage forced a rerun; the collector now retries and refuses to save incomplete snapshots.
- Trend pipeline (`src/trends/`) built: shared weekly structure, Epoch daily open roles, role-mix shift, emerging skills, posting lifetime.
- Key patterns: Anthropic open roles +52% and OpenAI +29% since March; Anthropic paused GTM hiring in summer and then surged; emerging skills point to data-center build-out and the public sector.
- Data quality: Epoch scrape gaps make single weeks lumpy, so 4-week averages are the headline.
