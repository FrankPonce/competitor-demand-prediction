# Sprint 11 — Fine-Tune a Skill Extraction Model (optional task)

**Week of:** 2027-01-18 · **CadetX optional task** · **Status:** 🟡 In progress (started 2026-11-10)

## Goal

Fine-tune a pre-trained model to extract skills more accurately than the rule-based baseline.

## CadetX deliverables

- [ ] Fine-tuned model & evaluation metrics
- [ ] Short note on training process & gains

## Planned approach

- Label a few hundred spans (weak labels from Sprint 4 + manual corrections)
- Token classification with BERT/RoBERTa (or spaCy NER)
- Compare precision/recall vs. Sprint 4 baseline

## Progress

- [x] Sentence dataset: 127,847 unique sentences from requirements/preferred/responsibilities; postings split 90/10
  by a hash of `job_id`, so the gold set never shares a posting with training (`src/skillmodel/data.py`)
- [x] Labelling guidelines: [`docs/skill-labelling-guidelines.md`](../skill-labelling-guidelines.md)
- [x] Gold set pre-labelled: 200 held-out sentences (40 per Anthropic, OpenAI, NVIDIA, Google, peers; 15 role
  families), 372 spans, from rule + LLM candidates reviewed against the guidelines
- [ ] Gold set verified by the owner (`python -m src.skillmodel.annotate` → localhost:8800)
- [ ] Training labels: 3,000 sentences, rules + LLM (`src.skillmodel.llm_label`, resumable within Groq's free daily budget)
- [ ] Fine-tune on the GPU (RTX 4050, 6 GB) and evaluate rules vs LLM vs model

## Outputs

_To be filled in when the sprint runs._

## Notes & decisions

_To be filled in when the sprint runs._

---

[← Back to README](../../README.md)
