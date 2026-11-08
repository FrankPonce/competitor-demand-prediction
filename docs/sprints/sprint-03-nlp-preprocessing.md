# Sprint 3 — NLP Preprocessing & Method Selection

**Week of:** 2026-11-23 · **CadetX task 3** · **Status:** ⬜ Not started

## Goal

Clean and structure job descriptions so every company's text is comparable.

## CadetX deliverables

- [ ] Cleaned & preprocessed job-posting text
- [ ] Documented preprocessing workflow + code in GitHub

## Planned approach

- Strip boilerplate (company 'about us', EEO/benefits blocks) so it doesn't swamp skill signals
- Normalize whitespace, unicode, casing; language detection; sentence segmentation
- Tokenization + lemmatization (spaCy), stop-word handling kept configurable
- Section splitting: responsibilities vs. qualifications vs. nice-to-haves
- Write `cleaned_description` to `data/processed/`

## Outputs

_To be filled in when the sprint runs._

## Notes & decisions

_To be filled in when the sprint runs._

---

[← Back to README](../../README.md)
