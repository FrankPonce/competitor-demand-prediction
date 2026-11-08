# Data Dictionary

Shared schema for every company dataset (one CSV per company, plus an optional
combined file). Each row is one job posting. Field names follow the CadetX brief.

## Required fields

| Field | Type | Description | Notes |
| ----- | ---- | ----------- | ----- |
| `job_id` | string | Unique identifier for the posting | Prefer the source's own ID, prefixed by company (e.g. `anthropic-123456`) so IDs stay unique in the combined file |
| `company_name` | string | Hiring company | One of the project's target companies |
| `job_title` | string | Title as published | Kept raw; normalized title is derived later |
| `job_description` | string | Full description text | Main NLP input. Public posting content only; check redistribution rights before committing |
| `posting_date` | date (ISO 8601) | Date the posting was published | If the source gives no publish date, record that and use `first_seen_date` instead (see below) |
| `location` | string | Location(s) as published | Multiple locations separated by `; ` |
| `job_url` | string | Canonical URL of the posting | For traceability and validation |

## Recommended fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `employment_type` | string | Full-time, part-time, contract, internship |
| `department` / `job_category` | string | e.g. Engineering, AI Research, Data, Product |
| `seniority_level` | string | Junior, Mid, Senior, Lead, Principal (derived if not published) |
| `remote_type` | string | Remote, hybrid, onsite (derived from location/description) |
| `salary_range` | string | Only where published by the company |
| `updated_at` | datetime | Last-updated timestamp from the source, if available |
| `scraped_date` | datetime | When this record was collected (UTC) |
| `first_seen_date` | date | First snapshot in which the posting appeared |
| `last_seen_date` | date | Most recent snapshot in which the posting appeared |
| `job_status` | string | `active` / `closed` (closed = missing from a later snapshot) |
| `company_industry` | string | Sector label for grouping |
| `source_name` | string | Source the record came from (e.g. `greenhouse_board`, `kaggle_<dataset>`) |

## Derived analytical fields (Tasks 3–8)

| Field | Task | Description |
| ----- | ---- | ----------- |
| `cleaned_description` | 3 | Preprocessed text for modelling |
| `extracted_skills` | 4 | List of skills found in the description |
| `skill_categories` | 4 | Skills grouped (Cloud, ML, DevOps, …) via shared taxonomy |
| `tech_stack_tags` | 4 | Named technologies (Python, Kubernetes, CUDA, …) |
| `skill_frequency_vector` | 4 | Vectorized skills for ML |
| `posting_week` / `posting_month` | 5 | Time buckets for trend analysis |
| `hiring_velocity_bucket` | 5 | Low / medium / high |
| `emerging_skill_flag` | 5 | Marks new or rising skills |
| `role_cluster_id` | 8 | Cluster of similar roles |
| `embedding_vector` | 8 | Sentence embedding (e.g. Sentence-BERT), stored separately rather than in the CSV |

## Excluded data

No personal or sensitive information is collected: no recruiter or employee
names, emails, or phone numbers, and no applicant data. If a description
contains contact details, remove them during preprocessing.

## Deduplication and snapshots

- Primary key: `job_id`.
- Each collection run is a snapshot stamped with `scraped_date`. Across
  snapshots, update `first_seen_date`, `last_seen_date`, and `job_status`
  instead of duplicating rows.
- Raw snapshot files are named `data/raw/<company>/<YYYY-MM-DD>.json` (or `.csv`).
