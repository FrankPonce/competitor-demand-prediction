# Sprint 6 — Competitor Comparison

**Week of:** 2026-12-14 (done early, 2026-11-09) · **CadetX task 6** · **Status:** ✅ Done

## Goal

Compare 🟠 Anthropic, 🟣 OpenAI, 🟢 NVIDIA and 🔵 Google on skills, role mix,
seniority, pay, location and hiring velocity, within one shared framework,
to surface similarities, differences and strategic gaps.

## CadetX deliverables

- [x] Comparison tables & visuals: [`data/comparison/`](../../data/comparison/) · [generated summary with charts](../../reports/comparison/summary.md)
- [x] A short explanation of how each company compares: [Company by company](#company-by-company) below

## The comparison framework

The four datasets were collected differently, so a naive side-by-side would mostly
compare *sampling methods*. The framework controls for that:

| Rule | Why |
|---|---|
| **Same point in time:** postings open in the latest snapshot (2026-11-09) | Removes the history imbalance (Anthropic/OpenAI have Epoch history; NVIDIA/Google don't) |
| **Shares, never counts** | Board sizes and samples differ, so "% of a company's postings" is comparable |
| **Lens A: all roles** | Like-for-like for Anthropic vs OpenAI (full boards). Indicative only for NVIDIA (newest ~100) and Google (AI/ML sample) |
| **Lens B: technical roles** (ML/AI, research, software, infra, hardware, data, security) | Like-for-like across all four: OpenAI 408 · Google 349 · Anthropic 260 · NVIDIA 71 postings |
| **Distinctiveness = lift vs the *average* of the other three** | Each competitor weighs equally, so OpenAI's large board doesn't define "normal" |

> ⚠️ **Google sampling caveat:** the Google sample was gathered with search terms such as *generative AI*,
> *large language model*, *TPU* and *machine learning* (Sprint 2). Its high shares for those exact skills partly
> reflect **how the data was collected**, not only Google's priorities. Google's strongest *unbiased* signals are
> the ones its queries didn't target: people management, Java, compilers, RTL, and degree/experience requirements.

## At a glance

| | 🟠 Anthropic | 🟣 OpenAI | 🟢 NVIDIA | 🔵 Google |
|---|---:|---:|---:|---:|
| Open postings (all roles) | 675 | 813 | 99 | 582 |
| Technical share of postings | 39% | 50% | 72% | 60% |
| Sales & GTM share (lens A) | 29% | 25% | 4% | 16% |
| Median min. years, tech roles | 7 | 7 | 5 | 3 |
| PhD mentioned, tech roles | 5% | 3% | 23% | 64% |
| "Or equivalent experience" accepted, tech | 8%¹ | 12% | 83% | 94% |
| People managers (all roles) | 19% | 15% | 9% | 12% |
| Multi-location postings | 60% | 19% | 0% | 41% |
| Median disclosed pay midpoint, tech roles | **$402k** | $351k | $270k | n/a² |
| Skills phrased as *preferred* (nice-to-have) | 36% | **7%** | 28% | 37% |

<sub>¹ Anthropic states its degree policy in a standard "Logistics" block that Sprint 3 removes as boilerplate, so this undercounts. ² Google's results pages don't expose pay.</sub>

![Role family mix](../../reports/comparison/figures/role_family_mix.png)

![Skill categories](../../reports/comparison/figures/skill_categories.png)

![Distinctive skills](../../reports/comparison/figures/distinctive_skills.png)

## Company by company

### 🟠 Anthropic: safety-first, senior-heavy, scaling go-to-market

- **Role mix:** the most commercial of the four. 29% of open postings are sales/GTM and 11% finance, legal & people,
  while only 39% are technical. Combined with Sprint 5 (open roles +52% since March, GTM rebuilt from 84 to 223
  openings), Anthropic is building out its company and sales capacity fast.
- **Distinctive skills (tech roles):** AI Safety (15% vs 3% for the others) and AI Safety & Evaluation overall (38% vs
  ≤24%) are clearly distinctive, matching its positioning. Also Rust (18% vs 6%), reinforcement learning (18% vs 7%),
  and **multi-cloud**: AWS 16% and Azure 10%, against 5% and 3% elsewhere (Claude ships on several clouds).
  Security & compliance is high too (33% of tech postings).
- **Seniority:** 45% of technical roles with a known level are Principal/Staff, almost all from explicit "Staff+"
  titles. It also has the highest people-manager share (19%).
- **Pay:** highest disclosed technical pay (median midpoint about $402k).
- **Gaps:** low on C++ (7% vs 27%) and Linux (6% vs 17%). Systems-level and hardware work is a small part of its
  hiring.

### 🟣 OpenAI: product & platform engineering, API-centric

- **Role mix:** the largest board, and the most **software-engineering-heavy** of the full boards (20% of postings vs
  10% at Anthropic). Sales/GTM is still big (25%), but Sprint 5 showed its share of new postings falling while
  product, compute and marketing grow.
- **Distinctive skills:** APIs (40% vs 17%), backend development (21% vs 8%), observability (30% vs 14%), LLM APIs
  (10% vs 1%) and causal inference / experimentation (15% vs 4%). That's the profile of a company running consumer
  and developer **products at scale**, with an A/B testing culture.
- **Culture signal:** "fast-paced / ambiguity" language in 69% of tech postings (vs 34% for the others).
- **Framing:** only 7% of skill mentions are phrased as nice-to-haves (vs 28–37% elsewhere). OpenAI postings state
  what they need and rarely list preferences.
- **Gaps:** low on GPU (10% vs 27%), C++ and Google Cloud. Compute hiring sits in its own infrastructure teams rather
  than spread across roles.

### 🟢 NVIDIA: the hardware & HPC stack

- **Role mix:** 72% technical, with hardware & silicon (17%), infrastructure (19%) and data-center roles (8%), and almost
  no GTM or corporate roles in its newest postings.
- **Distinctive skills:** the whole accelerated-computing stack. Networking hardware such as InfiniBand/Ethernet
  (30% vs 2%), CUDA (17% vs 1%), NVLink/PCIe/CXL interconnects (20% vs 2%), HPC (35% vs 4%), Slurm (11% vs 1%),
  Linux (41% vs 6%), parallel programming (17% vs 2%).
- **Seniority:** 75% Senior-titled, and the most open to non-traditional paths: 83% accept "or equivalent experience"
  despite a 23% PhD-mention rate.
- **Gaps:** low on LLM language (8% vs 34%) and model evaluation (0%). NVIDIA hires the people who build the
  platform rather than the people who build frontier models on it.

### 🔵 Google: research-grade AI at scale, with a strong management layer

- **Role mix (AI/ML sample):** ML/AI engineering 13%, infrastructure 14%, product & design 9%, hardware 7% (TPU).
  Its largest hub in the sample is Bangalore (19%), followed by Sunnyvale, Mountain View and New York.
- **Distinctive skills:** TPU (16% vs 3%), compilers (11% vs 2%), RTL & verification (9% vs 2%) and Java (19% vs 5%),
  which point to its custom silicon and large internal platforms. **People management (13% vs 2%)** and technical
  leadership (36% vs 14%) stand out.
- **Credentials:** PhD mentioned in 64% of technical postings, but 94% accept "or equivalent experience". Google lists
  advanced degrees as preferred rather than required (PhD required in only 11%). It has the lowest median minimum
  years (3), so it hires across more levels.
- **Gaps:** low on observability, Kubernetes and APIs. Google's internal tooling names don't match the external
  vocabulary the taxonomy looks for (a known limitation).

## Similarities and strategic gaps

**Shared ground** (share of technical postings):
- Python 39–65%.
- AI agents 23–34%: agentic AI is now a cross-industry hiring theme.
- Distributed systems 18–25%.
- Infrastructure & DevOps 29–75%.

**Where they diverge:**

| Dimension | Leaders | Laggards | Reading |
|---|---|---|---|
| AI safety & evaluation | 🟠 Anthropic 38% | 🟢 NVIDIA 3% | Safety is a core hiring axis only at Anthropic |
| Hardware & accelerators | 🟢 NVIDIA 87% | 🟠 Anthropic 21% | Labs buy compute; NVIDIA builds it (Google: TPU in-house) |
| APIs & backend platforms | 🟣 OpenAI 40% APIs | 🔵 Google 9% | OpenAI's product-platform focus |
| Go-to-market build-out | 🟠 Anthropic 29% of roles | 🟢 NVIDIA 4% | Both labs are hiring sales capacity |
| Credential flexibility | 🔵 Google / 🟢 NVIDIA ~90% "or equivalent" | Labs (stated less often) | Different ways of writing requirements |

![Seniority mix](../../reports/comparison/figures/seniority_mix.png)

![Pay](../../reports/comparison/figures/pay.png)

![Regions](../../reports/comparison/figures/regions.png)

## How it's built

`python -m src.compare.build_comparison` ([code](../../src/compare/build_comparison.py)) reads the Sprint 4
features and writes:

| File | Content |
|---|---|
| `company_profiles.csv` | The "at a glance" metrics per company |
| `role_family_mix.csv` | Lens A role-family shares |
| `skill_category_share_tech.csv` | Lens B category shares |
| `distinctive_skills.csv` | Share, other-three average, lift, gap (pp), `distinctive` / `under_indexed` flags for every skill × company |
| `seniority_mix_tech.csv` | Lens B seniority shares |
| `skill_emphasis.csv` | Share of skill mentions in requirements / preferred / responsibilities |
| `top_hubs.csv` | Top locations per company |

Locations are mapped to regions (US, Europe, Asia-Pacific, Other) by pattern. Only 7 of 2,169 open postings were
unclassified before adding Canada/Ontario.

## Limitations

- **Sampling still matters** for NVIDIA (newest ~100, n=71 technical) and Google (keyword sample; see caveat above).
- **Boilerplate removal** hides company-wide statements (e.g. Anthropic's degree policy) from per-posting metrics.
- **Pay** is disclosed base-pay ranges (mostly US roles), midpoint of the range, and excludes equity.
- **Taxonomy vocabulary** favours external tool names, so companies with in-house tooling (Google) can under-index.

---

[← Back to README](../../README.md)
