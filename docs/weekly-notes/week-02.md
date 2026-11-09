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
