# Frontier Lab Hiring

Daily archive of Anthropic's and OpenAI's job postings. It records when each
advertised role appeared and disappeared, how its text changed, and which area
of the lab's work it belongs to.

Data through 2 Nov 2026 (counts and postings are shown with a seven-day delay).
File generated 9 Nov 2026. Published at https://epoch.ai/data/frontier-lab-hiring.

## Files

### frontier_lab_hiring_open_roles_by_category.csv

The daily series behind the chart: one row per scrape date, lab and
sub-category, counting that lab's postings in that sub-category open on that
day. Zero counts are included, so every date a lab was scraped carries a row
for each of the 16 sub-categories plus Other. Summing rows over
`subcategory` within a `category` gives the category series.

| Field | Type | Meaning |
|---|---|---|
| date | date (YYYY-MM-DD) | The scrape date. |
| lab | text | "Anthropic" or "OpenAI". |
| category | text | The sub-category's category (group): Research, Compute, Product, Go-to-market, Corporate, or Other. |
| subcategory | text | One of the 16 sub-categories defined below, or Other. |
| open_postings | integer | Number of this lab's postings in this sub-category open at that day's scrape. |

### frontier_lab_hiring_open_roles_by_country.csv

The daily series behind the chart's country view: one row per scrape date,
lab and country, counting the postings open on that day whose location lists
that country. A posting is counted once per country it lists, so a posting
offered in London and Dublin adds one to the United Kingdom and one to
Ireland, and the sum over countries on a day exceeds the lab's number of open
postings (by around two percent). A posting listing several cities in one
country adds one to that country. Remote postings count under the country
they name. Locations that could not be mapped to a country are reported under
the country value "Unmapped". Rows with a zero count are omitted, so a missing
date × lab × country is zero. Alongside the per-lab rows, rows with `lab` set
to "All labs" give the two labs' counts added together.

| Field | Type | Meaning |
|---|---|---|
| date | date (YYYY-MM-DD) | The scrape date. |
| lab | text | "Anthropic", "OpenAI", or "All labs" for the two labs together. |
| country | text | The country's English name, or "Unmapped" for locations that could not be mapped to a country. |
| open_postings | integer | Number of this lab's postings open at that day's scrape whose location lists this country. |

### frontier_lab_hiring_open_roles_by_city.csv

The country series broken down to cities: one row per scrape date, lab,
country and city, counting the postings open on that day whose location lists
that city. A posting is counted once per city it lists. The city is Remote for
a listing that is remote within the country and Unspecified for one that names
a country or region but no city. Rows with a zero count are omitted. As in the country file, rows with `lab`
set to "All labs" give the two labs' counts added together.

| Field | Type | Meaning |
|---|---|---|
| date | date (YYYY-MM-DD) | The scrape date. |
| lab | text | "Anthropic", "OpenAI", or "All labs" for the two labs together. |
| country | text | The English name of the country the city is in. |
| city | text | The city's English name; `Remote` for a listing that is remote within the country, `Unspecified` for one that names a country or region but no city. |
| open_postings | integer | Number of this lab's postings open at that day's scrape whose location lists this city. |

### frontier_lab_hiring_postings.csv

One row per posting ever observed: its lifetime in the archive, its label and
its location.

| Field | Type | Meaning |
|---|---|---|
| posting | text | Posting key (e.g. `Anthropic:123`, `OpenAI:<uuid>`), stable across the files in this ZIP. |
| lab | text | "Anthropic" or "OpenAI". |
| category | text | The posting's category (group), implied by its sub-category. |
| subcategory | text | The posting's sub-category (defined below). |
| confidence | text | "high", "medium" or "low": how clearly the advert fitted its sub-category (see Confidence below). |
| title | text | The posting's latest observed job title. |
| first_seen | date (YYYY-MM-DD) | First scrape date on which the posting appeared. |
| last_seen | date (YYYY-MM-DD) | Most recent scrape date on which the posting appeared. |
| open_at_latest_scrape | boolean (true/false) | Whether the posting was still up at the latest scrape. |
| countries | text | The countries the posting's location maps to, one per distinct country. Empty when the location could not be mapped. |
| cities | text | `Country: City` pairs for the cities the posting's location maps to; `Remote` in place of a city for a listing that is remote within the country, `Unspecified` when it names a country or region but no city. Empty when the location could not be mapped. |
| location_source | text | Where the location came from: `field` when taken from the job board's location field, `title` or `body` when inferred from the advert's title or text. Empty when the location could not be mapped. |

### frontier_lab_hiring_posting_texts.csv

One row per posting: the advert's text as last observed.

| Field | Type | Meaning |
|---|---|---|
| posting | text | Posting key — joins to frontier_lab_hiring_postings.csv. |
| lab | text | "Anthropic" or "OpenAI". |
| category | text | The posting's category (group). |
| subcategory | text | The posting's sub-category (defined below). |
| title | text | The posting's latest observed job title. |
| department | text | The department or team label the lab itself filed the posting under. |
| description | text | The full advert text, latest observed version. |

### frontier_lab_hiring_revisions.csv

One row per version of a posting's text, with the label given to that
version. A posting has one revision when it first appears and gains another
each time the lab changes its title, department or advert text; the daily
counts use the label in force on each day.

| Field | Type | Meaning |
|---|---|---|
| revision_key | text | Identifies this version of the posting's text; unique within the file. |
| posting_key | text | Posting key — joins to frontier_lab_hiring_postings.csv. |
| lab | text | "Anthropic" or "OpenAI". |
| effective_date | date (YYYY-MM-DD) | First scrape date on which this version of the text was observed. It stays in force until the next revision's effective_date. |
| title | text | The job title in this version. |
| department | text | The department or team label in this version. |
| category | text | The category (group) given to this version. |
| subcategory | text | The sub-category given to this version. |
| confidence | text | "high", "medium" or "low" for this version's label. |
| taxonomy_version | text | The taxonomy version under which this version was classified, as a version string such as "v1.0". It changes when we revise the taxonomy or the classification instructions, and when we judge that a change of language model warrants a new version. |

## How the files fit together

`posting` identifies the same role in frontier_lab_hiring_postings.csv and
frontier_lab_hiring_posting_texts.csv — each has exactly one row per posting,
so the two files join one-to-one on `posting`. frontier_lab_hiring_revisions.csv
has one or more rows per posting; its `posting_key` joins to `posting` in the
other two files, and the revision with the latest `effective_date` is the
version those files describe.

The daily series is derived from posting visibility: a posting counts as open
on a given date if that day's scrape of the lab's careers page returned it.
Counting the open postings per lab and sub-category on each scrape date
yields frontier_lab_hiring_open_roles_by_category.csv, so the daily counts
and the posting lifetimes can never disagree. Counting the same open postings
per lab and country on each scrape date — once per country a posting's
location lists — yields frontier_lab_hiring_open_roles_by_country.csv, and per lab, country and city — once per city it lists —
frontier_lab_hiring_open_roles_by_city.csv.
On each day a posting counts under the label of the revision in force that
day, so when a lab rewrites an advert and the new version is classified
differently, the counts move from that day on;
frontier_lab_hiring_postings.csv carries the latest label.

## Taxonomy

Taxonomy version: v1.0 (October 2026).

We classify every posting into one of 16 sub-categories grouped
into five categories, plus Other, rather than using the labs' own department
labels, because those labels differ: the same work is filed under different
names at each lab, and one shared set of definitions is what makes the two
comparable. The sub-categories describe which area of the lab's effort a role
exists to push forward rather than where it sits on an org chart.

- **Research** — training better models, and keeping them safe.
  - **Research** — Training and experimentation, plus everything researchers need to do it: research scientists and engineers, pretraining, post-training and RL, fine-tuning, evaluations and benchmarks, model architecture, data science on model behaviour, and research on data mixtures and synthetic data. Also the infrastructure and tooling that serves researchers: sandboxing and execution environments for training, research CI, and developer productivity for research workflows.
  - **Data** — Acquiring and producing the data models learn from: human-data programmes (raters, annotators, feedback and preference pipelines, task design), data vendor and licensing management, large-scale dataset acquisition, curation and quality operations, and the tooling built for those pipelines. The output of the work is data rather than a trained model.
  - **Safety & safeguards** — Work whose subject is the model's harmful behaviour or misuse: safeguards, trust & safety, model policy, preparedness, dangerous-capability evaluations, CBRN and cyber-harm analysis, red-teaming of models, abuse and enforcement, alignment and interpretability research, societal impact, and model welfare.
- **Compute** — building and running the machine the models run on.
  - **Silicon** — The lab's own chips: chip architecture, RTL, design verification, physical design, packaging and signal integrity, ASIC firmware, silicon bring-up, and accelerator runtime software for in-house chips.
  - **Datacenters** — The physical plant: siting, power, cooling, construction, commissioning and electrical work; server and fleet hardware; and datacenter supply and capacity planning where the role is technical rather than financial.
  - **ML infrastructure** — The software the models run on: clusters, scheduling, training runtime, kernels, and inference serving and performance.
- **Product** — what ships to customers.
  - **Product & platform** — The software that ships to customers: the API and developer platform, the consumer and business applications, coding products, and frontend, mobile, full-stack and application engineering, together with the product management, design, analytics, UX research and developer tooling embedded in the product organisation. A customer-facing product whose subject is a corporate function (a security product, an ads product) is still product.
  - **Robotics** — Robots and embodiment: actuators, manipulation, teleoperation, humanoid hardware, robot learning, and robotics simulation and test infrastructure.
  - **Consumer devices** — Dedicated consumer hardware: device software and firmware, camera, connectivity, industrial design, wearables, and device-specific product work.
  - **Ads** — The lab's advertising business: ad products, ad formats and delivery, ad sales and measurement, advertiser platforms, and the sales and marketing roles dedicated to selling advertising.
- **Go-to-market** — selling the products and standing behind them.
  - **Go-to-market** — Selling: account executives and sales management, sales strategy and operations, deal desk, partnerships and channel, marketing, brand, communications aimed at customers, demand generation, growth, customer success in its commercial sense, competitive intelligence, and sales enablement. Also brand and marketing web engineering, in-house creative studios, and pre-sale technical evangelism and solutions engineering.
  - **Forward deployed** — Engineers and architects who go to the customer: forward deployed engineering, applied AI engineering and architecture, deployment engineering, technical success, customer engineering, and professional services. What sets the work apart is building or configuring something for a named customer after the sale.
  - **Customer support** — Running support at scale: support engineers and specialists, support delivery, support operations, support automation, user operations, and the vendor management behind them.
- **Corporate** — running the company.
  - **Information security** — Protecting the company and its systems from adversaries: security engineering, detection and response, application, platform, infrastructure and network security, identity and access, threat intelligence and investigations, vulnerability management, privacy engineering, governance and security compliance, insider risk, and offensive security against the company's own systems.
  - **Finance, people & workplace** — Running the company: finance, accounting, tax, treasury, audit, procurement and sourcing; recruiting and talent; people operations, compensation and benefits; workplace, facilities, real estate, physical and corporate security, health and safety; corporate IT and helpdesk; and company-wide programme management, business analytics and operations not embedded in one organisation.
  - **Policy, legal & comms** — The company's interface to the state and the public: public policy, global affairs, regulatory affairs, all legal and counsel work wherever it is filed, communications and press, public-benefit and economic-impact research, and externally facing societal and economic research.
- **Other** — Used when nothing else fits, which is rare by design.

Some boundaries matter more than others for reading the data. Safety is about
the model and information security is about the company, wherever the lab
files the role. Functions with one home — legal, finance, recruiting, IT,
workplace, support — stay in that function whoever they serve, while
engineering, product and programme management, data science and design roles
take the category of the organisation they are embedded in. Silicon,
Datacenters and ML infrastructure are for people who build or run the
machine, not for everyone whose work touches it. Robotics and Consumer
devices take precedence over everything else, so that these small, distinct
programmes stay visible.

## Confidence

Each label carries a confidence rating in frontier_lab_hiring_postings.csv:

- **high** — the title and the duties described agree on the sub-category.
- **medium** — the department or a close reading of the advert was needed to decide.
- **low** — two sub-categories were genuinely arguable, or the advert says too little to be sure.

## Methodology

Both labs' public careers pages — Anthropic's careers page
(https://www.anthropic.com/careers) and OpenAI's job board
(https://jobs.ashbyhq.com/openai) — are scraped once a day, and every
advertised role is kept after it disappears. A posting is one advert with a
stable identifier on the lab's site; when the lab changes its title,
department or text, a new revision is recorded with the day it took effect.
A language model reads each posting's title, the lab's own department and
team label, and the full advert text, and assigns exactly one sub-category
using the definitions above; the category follows from it. The title and
department are evidence rather than the answer, because the two labs organise
the same work under different names, and the advert's concrete
responsibilities decide when they disagree. On each day a posting counts
under the label in force that day, so when a lab rewrites an advert and the
new version is classified differently, the counts move from that day on. When
we revise the taxonomy or the classification instructions, and when a change
of language model warrants it, we reclassify the full history so that every
version is labelled the same way. Each such reclassification comes with a new
version number, recorded in `taxonomy_version`, and can change earlier counts.

Roughly half of all postings have had at least one revision to their text,
most of them small edits. When a revision is classified, the model
occasionally lands on a different sub-category for near-identical text, so
about 3% of postings change label across their revisions; treat these as
noise rather than as a reorganisation of the lab's hiring.

A posting that stops being returned by the daily scrape stops counting as
open from that day: its last_seen is the last date it appeared, and the daily
counts fall accordingly. A disappearance means the role was taken off the
careers page — it may have been filled, closed unfilled, or reposted under a
new posting id.

## Reading the data

**Do the counts measure hiring or headcount?** Neither directly. They count
open postings — advertised roles — and a single posting can cover several
hires, stay up after being filled, or be reposted.

**How often is the data updated?** Both careers pages are scraped once a day,
and the data is published with a seven-day delay.

## License

Epoch AI's data is free to use, distribute, and reproduce provided the source
and authors are credited under the Creative Commons Attribution license
(https://creativecommons.org/licenses/by/4.0/).

## Citation

Epoch AI, 'Data on Frontier Lab Hiring'. Published online at epoch.ai.
Retrieved from 'https://epoch.ai/data/frontier-lab-hiring' [online resource]. Accessed 2 Nov 2026.

BibTeX:

```bibtex
@misc{EpochFrontierLabHiring2026,
  title = {{Data on Frontier Lab Hiring}},
  author = {{Epoch AI}},
  year = {2026},
  month = {11},
  url = {https://epoch.ai/data/frontier-lab-hiring},
  note = {Accessed: 2 Nov 2026}
}
```
