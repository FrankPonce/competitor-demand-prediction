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

## Update — Review & polish (2026-11-09)

- Visual identity: dark theme plus one fixed, colour-blind-validated colour per company (🟠 Anthropic, 🟣 OpenAI, 🟢 NVIDIA, 🔵 Google) in `src/style.py`; charts re-rendered; README banner and badges.
- Repo health: the corpus is now committed as per-company CSVs (delta-friendly). The 30 MB Parquet is a local cache, which avoids about 30 MB of growth per weekly rebuild.
- Added 41 regression tests (`python -m pytest`) covering robots rules, parsing, salary, sections and skill false positives.
- Added `notebooks/` and `presentations/` placeholders; refreshed stale counts.

## Update — Sprint 6 done (2026-11-09)

- Built a two-lens comparison (`src/compare/`): all roles vs. like-for-like technical roles, shares not counts, lift vs. the average of the other three.
- Profiles: Anthropic = AI safety, multi-cloud, Staff+ seniority, highest pay, heavy GTM build-out; OpenAI = APIs/backend/observability, experimentation culture, firm requirements; NVIDIA = CUDA/HPC/networking stack; Google = TPU, compilers, people management, PhD-preferred.
- Caveat recorded: Google's keyword-driven sample inflates GenAI/LLM/TPU shares.
- 48 tests passing.

## Update — Project review: closing the gaps (2026-11-09)

- **Uneven data fixed:** NVIDIA is now the full board (2,799 postings, via the listing endpoint the careers page uses); Google is an unbiased 26-hub × 5-level sample (917 postings, 130/130 slices fully covered at twice-weekly cadence).
- **Longer history:** Internet Archive open-role counts (counts only) for Google 2023–26 and Anthropic 2024–26, within 1.2% of Epoch where they overlap. NVIDIA requisition-ID estimator: 45–55/day in spring → 70–80/day in autumn.
- **Beyond the taxonomy:** Fightin' Words log-odds on phrases surfaces TS/SCI clearances, SMB/DACH segments, customer-deployment language and "AI tools" fluency.
- **Geography and pay:** footprint and expansion maps (11 new-city signals); pay trends.
- Sprint 6 re-run on the better data; Google's earlier AI focus was overstated by the keyword sample (60% → 40% technical).
- Routine change: Google now runs twice weekly alongside NVIDIA. 55 tests passing.
