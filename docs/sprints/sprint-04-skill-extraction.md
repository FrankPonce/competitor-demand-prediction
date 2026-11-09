# Sprint 4 — Skill Extraction & Feature Engineering

**Week of:** 2026-11-30 (done early, 2026-11-09) · **CadetX task 4** · **Status:** ✅ Done

## Goal

Turn every job description into structured skill features using **one shared
taxonomy** across all four companies, plus role, seniority and education
features for the comparison and forecasting sprints.

## CadetX deliverables

- [x] Extracted-skills dataset & feature tables
  - [`data/features/posting_features.csv`](../../data/features/posting_features.csv): one row per posting (also `.parquet`)
  - [`data/features/skills_long.csv`](../../data/features/skills_long.csv): one row per (posting, skill), with the section(s) it appeared in
  - [`data/features/skill_matrix.parquet`](../../data/features/skill_matrix.parquet): posting × skill binary matrix (the brief's `skill_frequency_vector`)
  - [`reports/skills/`](../../reports/skills/): company-level share tables and the [generated summary](../../reports/skills/summary.md)
- [x] Short note on the methods used (this page)
- [x] Shared skill taxonomy: [`src/features/taxonomy.py`](../../src/features/taxonomy.py)

## Headline results

| | Anthropic | OpenAI | NVIDIA | Google |
|---|---:|---:|---:|---:|
| Postings | 1,839 | 2,391 | 100 | 579 |
| Median skills / posting | 10 | 8 | 11 | 10 |
| Median **tech** skills / posting | 3 | 3 | 10 | 7 |
| Years of experience stated | 66% | 56% | 78% | 94% |
| Median minimum years | 7 | 7 | 6 | 5 |
| PhD mentioned | 2% | 2% | 21% | 44% |
| Sales & GTM roles | 32% | 27% | 4% | 16% |
| Hardware & Accelerators skills | 9% | 11% | 86% | 19% |

Early patterns (to be tested properly in Sprints 6 and 8):

- **Anthropic and OpenAI are hiring a go-to-market machine.** Roughly 30% of postings are sales/GTM roles, and over half mention GTM skills. Both also hire heavily in finance, legal and people functions, which looks like company-building at scale.
- **NVIDIA's postings are almost all hardware and systems:** GPU 61%, HPC 34%, firmware 29%, plus the networking stack.
- **Google's AI/ML sample is the most research-flavoured.** 44% mention a PhD, and it has the highest LLM/GenAI share (56%).
- **AI Safety & Evaluation** shows up in 30% of Anthropic postings vs. 19% at OpenAI and 24% at Google.

## Methods

### 1. Shared taxonomy (211 skills, 19 categories)

Seeded by mining the most frequent capitalised and acronym terms in the
requirements, preferred and responsibilities sections, then extended with
standard industry vocabulary. Because the corpus is mostly **non-engineering**
(sales, finance, legal, data-center construction), the taxonomy covers business
domains too, not just tech.

| Tech categories (→ `tech_stack_tags`) | Non-tech categories |
|---|---|
| Programming Languages · ML Frameworks & Libraries · AI/ML Methods · LLM & Generative AI · AI Safety & Evaluation · Hardware & Accelerators · HPC & Distributed Systems · Cloud Platforms · Infrastructure & DevOps · Data Engineering & Analytics · Databases · Web, Mobile & APIs · Security & Compliance | Go-to-Market & Sales · Finance, Legal & Operations · Product & Design · Data Center & Facilities · Leadership & Collaboration · Spoken Languages |

Each skill has aliases. Plain phrases match case-insensitively, tolerate
hyphen/space variants ("fine tuning" = "fine-tuning") and plurals.
**Case-sensitive** or **context** patterns handle words that are also ordinary
English:

| Skill | Problem | Rule |
|---|---|---|
| Go, R, C | "Go deep", "D&R", "I&C", "C-suite" | Case-sensitive, only inside language lists (`Python, Go, Rust`) |
| Excel | "excel at..." | Case-sensitive, not followed by *at/in* |
| Transformers | Electrical transformers in data-center roles | Only "transformer model/architecture", "attention mechanism" |
| Inference | "causal inference" | Excludes *causal / statistical / Bayesian* |
| Spoken languages | "French market" | Needs a proficiency cue nearby (*fluent, native, business-level…*) |
| Procurement | Sales postings: "navigate enterprise procurement cycles" | Excluded for Sales & GTM roles (it's the customer's process) |
| Partnerships | "partner closely with Sales, Partnerships, Product" | Needs a verb such as *build, manage, negotiate…* or "strategic partnership" |

### 2. Section-aware matching

Skills are matched on the readable `clean_text` sections from Sprint 3 (not on
lemmas, so "Go" and multi-word phrases survive), and each match records
**where** it appeared: `in_requirements`, `in_preferred`, `in_responsibilities`,
`in_context`. Sprint 6 can then weigh "required" vs. "nice to have".

### 3. Role family, seniority, experience, education

| Feature | Method |
|---|---|
| `role_family` (15 families) | Ordered title rules (e.g. Data Center → Hardware → Research → ML → Safety → Sales → … → Software), falling back to the department. 1% end up as "Other" |
| `seniority_level` | Title cues first: Intern, Director+, Manager (people managers only; product/program/account managers count as ICs), Principal/Staff, Lead, Senior, Mid (Google "III"), Junior (Google "II", new grad). Otherwise inferred from minimum years: ≤2 Junior, 3–5 Mid, 6–9 Senior, 10+ Principal |
| `min_years_experience` | Smallest "N+ years … experience" in the requirements section (else the whole text) |
| `min_degree`, `mentions_phd`, `degree_equivalent_ok`, `law_degree` | Degree patterns in requirements vs. anywhere |

### 4. Precision check

A random sample of **100 skill matches** with surrounding context was reviewed
by hand: [`reports/skills/spot_check.csv`](../../reports/skills/spot_check.csv).

- **89/100 correct.**
- Most errors are mentions of a *team or customer*, not a required skill ("business development leaders", "go-to-market teams").
- Two error types were fixed after the review: "trademark clearance" matching the security-clearance skill, and legal negotiation being filed under sales pipeline (Negotiation is now its own skill).

## Limitations

- **Rule-based extraction** finds only skills in the taxonomy. New or rare tools are missed until added. Sprint 11's fine-tuned model is meant to improve recall.
- **Mentions ≠ requirements.** Some matches describe the team or product. Use `in_requirements` / `in_preferred` when precision matters.
- **Seniority is "Unspecified"** for 28% of OpenAI and 19% of Anthropic postings: flat titles with no stated years.
- **Samples differ:** Google is an AI/ML sample and NVIDIA is its newest ~100 postings. Compare shares and patterns, not counts.

Run: `python -m src.features.build_features` (~5–6 min).

---

[← Back to README](../../README.md)
