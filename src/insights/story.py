"""Story layer: turn hiring signals into readable, evidence-backed claims per company (Sprint 10 extension).

Two steps, deliberately separated:
1. Evidence engine (deterministic, testable): interpretation rules read job titles/departments of open postings and
   produce *claims* such as "building its own data centers", each with the signal (counts, growth, lift vs peers),
   the place (from job locations), example titles, corroborating headlines/events and a confidence label.
2. Narrator (optional): a free LLM (src.llm) writes headlines and short paragraphs from those facts only. Every
   number in its text must appear in the facts, otherwise the template text is kept.

Run after src.dashboard.export:   python -m src.insights.story
Output: dashboard/data/story.json (read by the dashboard) and data/insights/story_facts.json (audit trail).
"""

from __future__ import annotations

import json
import re
import time
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import llm
from src.preprocess.corpus_io import load_corpus
from src.trends.geo_pay import parse_locations

warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression")
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
DASH = ROOT / "dashboard" / "data"
FOCUS = ["Anthropic", "OpenAI", "NVIDIA", "Google"]
WINDOW = 91  # days: "recent" = last 13 weeks, compared with the 13 weeks before

# ---------------------------------------------------------------- interpretation rules
# title: regex on job title (+ department); skip: companies for which the theme is the core business, not a signal;
# news: regex that would corroborate the claim in a headline/event; min_open: postings needed to claim it.
THEMES = {
    "dc_build": {
        "label": "Building its own data centers",
        "title": r"data ?cent(er|re).{0,40}(construct|capacity|deliver|facilit|controls|operations|site|critical|commission"
                 r"|energy|power|electrical|mechanical|design)|(construct|capacity|facilit|controls|site|critical|"
                 r"electrical|mechanical|commission).{0,40}data ?cent|data hall|white space|critical (facilit|environment)"
                 r"|power generation|substation|high[- ]voltage|commissioning|site (selection|acquisition)"
                 r"|(energy|power) (procurement|development|markets|strategy)|interconnection|\butility\b",
        "skip": ["NVIDIA"],  # data-center systems are NVIDIA's product, not its own build-out
        "news": r"data ?cent|gigawatt|\bgw\b|campus|stargate|colossus|power plant|compute capacity|supercomputer",
        "reading": "Power, cooling, construction and site roles mean the company is building or running its own "
                   "compute sites instead of only renting cloud capacity.",
        "min_open": 4,
    },
    "government": {
        "label": "Selling to government and defense",
        "title": r"clearance|ts/sci|top secret|public sector|federal|government|department of defen[cs]e|defen[cs]e "
                 r"(?:industr|sector|customer|program)|national security|\bdod\b|military|intelligence community"
                 r"|govcloud|fedramp|\bsled\b",
        "skip": [],
        "news": r"pentagon|department of defen[cs]e|\bdod\b|federal|national security|military|public sector"
                r"|government (?:contract|agenc|customer|deal)",
        "reading": "Security-clearance and public-sector roles point to contracts with government and defense customers, "
                   "which need cleared staff on site.",
        "min_open": 3,
    },
    "enterprise_deploy": {
        "label": "Deploying inside large enterprises",
        "title": r"forward[- ]deployed|deployment strateg|solutions? (architect|engineer)|implementation|customer success"
                 r"|applied ai engineer|technical account|engagement manager|professional services|customer engineer",
        "skip": [],
        "news": r"enterprise|partnership|deploy|customers?\b",
        "reading": "Engineers who work at customer sites mean the product is being rolled out inside large organisations, "
                   "not only sold self-serve.",
        "min_open": 6,
    },
    "sales_push": {
        "label": "Scaling the sales machine",
        "title": r"account executive|account director|account manager|\bsales\b|business development|partnerships?"
                 r"|go[- ]to[- ]market|\bgtm\b|revenue|channel|alliances",
        "skip": [],
        "news": r"enterprise|customers?|revenue|sales|partnership",
        "reading": "A growing sales force means the company is chasing revenue in new segments or regions.",
        "min_open": 8,
    },
    "robotics": {
        "label": "Moving into robotics",
        "title": r"robot|humanoid|actuator|mechatronic|manipulat|embodied|\bisaac\b|teleoperation",
        "skip": [],
        "news": r"robot|humanoid|embodied|physical ai",
        "reading": "Robotics, actuator and test-rig roles mean AI is being built into physical machines.",
        "min_open": 4,
    },
    "devices": {
        "label": "Building hardware devices",
        "title": r"consumer (device|hardware|electronics)|industrial design|product design engineer|firmware|embedded"
                 r"|\bnpi\b|manufacturing|supply chain|hardware (engineer|product|program)|acoustic|display|camera",
        "skip": ["NVIDIA", "Google"],
        "news": r"device|hardware|gadget|wearable",
        "reading": "Hardware, manufacturing and supply-chain roles suggest a physical product in development.",
        "min_open": 4,
    },
    "chips": {
        "label": "Designing its own chips",
        "title": r"\basic\b|silicon|\bchip\b|\btpu\b|\brtl\b|design verification|physical design|\bsoc\b|accelerator"
                 r"|packaging|tape[- ]?out",
        "skip": ["NVIDIA"],
        "news": r"chip|silicon|tpu|accelerator|semiconductor",
        "reading": "Chip-design and verification roles mean in-house silicon, which cuts dependence on GPU suppliers.",
        "min_open": 4,
    },
    "safety_policy": {
        "label": "Investing in safety and policy",
        "title": r"safety|alignment|interpretab|policy|trust|red team|responsible|frontier risk|model welfare",
        "skip": [],
        "news": r"safety|alignment|policy|regulat|responsible",
        "reading": "Safety, alignment and policy roles show how much the company invests in governing its models.",
        "min_open": 6,
    },
    "consumer_ads": {
        "label": "Monetising consumers",
        "title": r"\bads?\b|advertis|monetiz|\bgrowth\b|subscription|commerce|shopping|consumer product|marketplace",
        "skip": ["Google"],
        "news": r"\bads?\b|advertis|shopping|subscription|consumer",
        "reading": "Ads, growth and subscription roles mean the company is turning a large user base into revenue.",
        "min_open": 5,
    },
    "networking": {
        "label": "Owning the network between GPUs",
        "title": r"network|infiniband|ethernet|nvlink|\bswitch|optic|photonic|interconnect|\bserdes\b|\bnic\b",
        "skip": [],
        "news": r"network|infiniband|ethernet|spectrum-x|nvlink|photonic|optic",
        "reading": "Networking, optics and interconnect roles show investment in linking thousands of chips into one "
                   "system: the bottleneck has moved from the single chip to the cluster.",
        "min_open": 10,
    },
    "autonomous": {
        "label": "Building self-driving and automotive AI",
        "title": r"autonomous|self[- ]driving|\bav\b|automotive|\bdrive\b|\badas\b|vehicle",
        "skip": [],
        "news": r"autonomous|self-driving|automotive|vehicle|robotaxi",
        "reading": "Autonomous-driving and automotive roles mean cars remain a growth market for the company's chips "
                   "and software.",
        "min_open": 8,
    },
}

NOTABLE = {"dc_build", "government", "chips", "robotics", "devices"}  # strategic moves, surfaced earlier
GTM_FAMILIES = {"Sales & Go-to-Market", "Marketing & Communications"}
CORP_FAMILIES = {"Finance, Legal & People", "Operations"}
DC_FAMILIES = {"Data Center & Facilities"}
ENG_FAMILIES = {"Software Engineering", "ML / AI Engineering", "Infrastructure & SRE", "Research", "Data Science & Analytics",
                "Security & Privacy", "Hardware Engineering"}


# ---------------------------------------------------------------- helpers

def _num(x, d=0):
    return None if x is None or (isinstance(x, float) and x != x) else round(float(x), d) if d else int(round(float(x)))


def _cities(locs: pd.Series, top: int = 3) -> list[list]:
    c = Counter()
    for loc in locs.dropna():
        for city, _cc in parse_locations(loc):
            if city:
                c[city] += 1
    return [[k, v] for k, v in c.most_common(top)]


def _examples(titles: pd.Series, n: int = 4) -> list[str]:
    clean = titles.dropna().str.replace(r"\s*[-–,(].*$", "", regex=True).str.strip()
    out, seen = [], set()
    for t in titles.dropna()[clean.map(clean.value_counts()).sort_values(ascending=False).index]:
        k = t.lower()[:40]
        if k not in seen:
            seen.add(k)
            out.append(t.strip())
        if len(out) == n:
            break
    return out


def load() -> dict:
    corpus = load_corpus()
    feats = pd.read_parquet(D / "features" / "posting_features.parquet", columns=["job_id", "company_name", "role_family"])
    c = corpus.merge(feats, on=["job_id", "company_name"], how="left")
    c["date"] = pd.to_datetime(c.posting_date.fillna(c.first_seen_date), errors="coerce", utc=True).dt.tz_localize(None)
    c["blob"] = (c.job_title.fillna("") + " | " + c.department.fillna("")).str.lower()
    news = pd.read_csv(D / "context" / "news.csv") if (D / "context" / "news.csv").exists() else pd.DataFrame()
    events = pd.read_csv(D / "events" / "events.csv")
    return {"c": c, "news": news, "events": events,
            "companies": json.loads((DASH / "companies.json").read_text(encoding="utf-8")),
            "globe": json.loads((DASH / "globe.json").read_text(encoding="utf-8")),
            "tracker": json.loads((DASH / "tracker.json").read_text(encoding="utf-8")),
            "context": json.loads((DASH / "context.json").read_text(encoding="utf-8"))}


def corroborate(company: str, rx: str, news: pd.DataFrame, events: pd.DataFrame, cities: list[str]) -> list[dict]:
    """Headlines/events that mention the company and the theme (or one of the theme's cities)."""
    hits = []
    city_rx = "|".join(re.escape(x) for x in cities if len(x) > 3)
    if len(news):
        n = news[(news.company == company) & news.title.str.contains(rx, case=False, regex=True)]
        if city_rx:
            n = pd.concat([n, news[(news.company == company) & news.title.str.contains(city_rx, case=False, regex=True)
                                   & news.title.str.contains(rx, case=False, regex=True)]])
        for r in n.drop_duplicates("url").sort_values("date", ascending=False).head(3).itertuples():
            hits.append({"date": r.date, "title": r.title, "url": r.url, "source": r.source})
    e = events[(events.company == company) & events.description.fillna("").str.contains(rx, case=False, regex=True)]
    for r in e.sort_values("event_date", ascending=False).head(2).itertuples():
        hits.append({"date": r.event_date, "title": r.description, "url": r.source_url, "source": r.source_name})
    return hits[:3]


# ---------------------------------------------------------------- evidence engine

def theme_claims(company: str, data: dict) -> list[dict]:
    c = data["c"]
    me = c[c.company_name == company]
    open_me = me[me.job_status == "active"]
    active = c[(c.company_name.isin(FOCUS)) & (c.company_name != company) & (c.job_status == "active")]
    has_history = me.in_epoch.fillna(False).any() or (me.job_status == "closed").any()
    now = me.date.max()
    claims = []
    for key, th in THEMES.items():
        if company in th["skip"]:
            continue
        rx = re.compile(th["title"], re.I)
        hit = open_me[open_me.blob.str.contains(rx)]
        n_open = len(hit)
        if n_open < th["min_open"]:
            continue
        share = n_open / max(len(open_me), 1)
        others = active[~active.company_name.isin(th["skip"])]  # compare only with companies where it is a signal
        peer_share = others.blob.str.contains(rx).mean() if len(others) else 0
        lift = share / peer_share if peer_share > 0 else None
        recent = prior = None
        if has_history:  # dated postings incl. closed ones: growth is meaningful
            allhit = me[me.blob.str.contains(rx)]
            recent = int((allhit.date > now - pd.Timedelta(days=WINDOW)).sum())
            prior = int(((allhit.date <= now - pd.Timedelta(days=WINDOW))
                         & (allhit.date > now - pd.Timedelta(days=2 * WINDOW))).sum())
        growth = (recent / prior) if (recent is not None and prior) else None
        new_theme = recent is not None and prior == 0 and recent >= th["min_open"]
        distinctive = lift is not None and lift >= 1.6
        rising = growth is not None and growth >= 1.4 and recent >= 5
        notable = key in NOTABLE and (lift is None or lift >= 1.0)
        if not (distinctive or rising or new_theme or notable):
            continue
        cities = _cities(hit.location)
        corr = corroborate(company, th["news"], data["news"], data["events"], [x[0] for x in cities])
        strength = n_open * (min(lift, 4) if lift else 1) * (min(growth, 3) if growth else 1) * (1.5 if new_theme else 1)
        strength *= 1.6 if key in NOTABLE else 1
        weak = not (rising or new_theme) and (lift is None or lift < 1.3)  # about the same as peers
        conf = "confirmed" if corr else ("watch" if weak else "likely" if n_open >= 10 or rising or new_theme else "watch")
        signal = [f"{n_open} open roles ({share:.0%} of {company}'s open postings)"]
        if lift:
            signal.append(f"{lift:.1f}× the share at the other three companies")
        if recent is not None:
            signal.append(f"{recent} new in the last 13 weeks vs {prior} in the 13 weeks before")
        # one short line with the most telling fact (change > distinctiveness > size), for headlines and cards
        if growth and growth >= 1.4:
            key_fact = f"{prior} → {recent} new roles per 13 weeks ({growth:.1f}×)"
        elif new_theme:
            key_fact = f"{recent} new roles in 13 weeks, none in the 13 weeks before"
        elif lift and lift >= 1.5:
            key_fact = f"{n_open} open roles, {lift:.1f}× the share at peers"
        else:
            key_fact = f"{n_open} open roles"
        where = [x[0] for x in cities if x[1] >= max(2, 0.2 * n_open)]
        claims.append({
            "key_fact": key_fact, "concentrated_in": where,
            "id": key, "label": th["label"], "reading": th["reading"], "confidence": conf,
            "open_roles": n_open, "share_of_open": round(share, 3), "lift_vs_peers": round(lift, 2) if lift else None,
            "new_13w": recent, "prior_13w": prior, "growth": round(growth, 2) if growth else None,
            "cities": cities, "examples": _examples(hit.job_title), "corroboration": corr,
            "signal": signal, "strength": round(strength, 2),
        })
    return sorted(claims, key=lambda x: -x["strength"])[:4]


def expansion_claims(company: str, data: dict) -> list[dict]:
    """New cities: what kind of office do the postings there suggest?"""
    c = data["c"]
    me = c[c.company_name == company]
    arcs = [a for a in data["globe"]["arcs"] if a["company"] == company]
    ll = {(r["company"], r["city"]): r for r in data["tracker"]["lead_lag"]}
    out = []
    for a in sorted(arcs, key=lambda a: a["date"], reverse=True):
        here = me[me.location.fillna("").str.contains(re.escape(a["city"]), case=False)]
        fam = Counter(here.role_family.dropna())
        gtm = sum(v for k, v in fam.items() if k in GTM_FAMILIES)
        eng = sum(v for k, v in fam.items() if k in ENG_FAMILIES)
        corp = sum(v for k, v in fam.items() if k in CORP_FAMILIES)
        dc = sum(v for k, v in fam.items() if k in DC_FAMILIES)
        kind = ("data-center site" if dc and dc >= max(gtm, eng) else
                "regional hub" if corp > max(gtm, eng) else
                "sales office" if gtm > eng else "engineering hub" if eng > gtm else "mixed team")
        r = ll.get((company, a["city"]))
        news_part = (f"announced {abs(r['lead_days'])} days {'after' if r['lead_days'] > 0 else 'before'} the first "
                     f"posting" if r and r["lead_days"] else "announced the same day" if r else "no announcement yet")
        out.append({"summary": f"{a['city']}: looks like a {kind} ({len(here)} postings, first {a['date']}; {news_part})",
                    "city": a["city"], "country": a["country"], "first_posting": a["date"], "status": a["status"],
                    "postings": int(len(here)), "kind": kind, "role_mix": [[k, v] for k, v in fam.most_common(3)],
                    "lead_days": r["lead_days"] if r else None, "event": r["event"] if r else None,
                    "source": r["source"] if r else None, "examples": _examples(here.job_title, 3)})
    return out


def company_facts(company: str, data: dict) -> dict:
    co = data["companies"][company]
    k = co["kpi"]
    ctx = data["context"]
    models = sorted([m for m in ctx["models"] if m["company"] == company], key=lambda m: m["date"], reverse=True)
    fin = ctx["financials"].get(company)
    fin_fact = None
    if fin and fin.get("revenue") and len(fin["revenue"]) >= 5:
        rev = fin["revenue"]
        last, yago = rev[-1], rev[-5]
        fin_fact = {"quarter_end": last[0], "revenue_usd_b": round(last[1] / 1e9, 1),
                    "revenue_yoy": round(last[1] / yago[1] - 1, 3)}
        if fin.get("rnd_expense"):
            fin_fact["rnd_usd_b"] = round(fin["rnd_expense"][-1][1] / 1e9, 1)
    pq = D / "context" / "patents_quarterly.csv"
    pat = None
    if pq.exists():
        p = pd.read_csv(pq)
        p = p[p.company == company].sort_values("quarter")
        if len(p) >= 9:
            last4, prev4 = p.publications.iloc[-5:-1].sum(), p.publications.iloc[-9:-5].sum()  # skip the open quarter
            pat = {"patent_publications_last_4_quarters": int(last4), "patent_publications_4_quarters_before": int(prev4),
                   # a % change on a tiny base (Anthropic: 1 → 5) would mislead, so only from 10 publications up
                   "change_pct": _num((last4 / prev4 - 1) * 100) if prev4 >= 10 else None,
                   "source": "EPO Open Patent Services (publications naming the company as applicant)"}
    pr = D / "context" / "patents_recent.csv"
    if pat is not None and pr.exists():
        t = pd.read_csv(pr)
        pat["recent_patent_titles"] = list(dict.fromkeys(t[t.company == company].title.str.capitalize()))[:6]
    funding = [f for f in data["tracker"]["funding"] if f["company"] == company]
    last_hist = co["history"][-1]
    return {
        "company": company, "segment": co["segment"], "unit": co["unit"],
        # "size" is the tracked hiring series; postings_analysed is what the skill/role analysis is based on
        # (for Google a sample of the board, so the two differ on purpose)
        "size": {"metric": co["series_label"], "week": last_hist[0], "value": last_hist[1]},
        "postings_analysed": k["open_postings"],
        "change_6m_pct": _num(k["momentum_6m"] * 100) if k["momentum_6m"] is not None else None,
        "forecast_next_8_weeks_pct": _num(k["outlook_8w"] * 100) if k["outlook_8w"] is not None else None,
        "technical_share_pct": _num(k["tech_share"] * 100), "pay_mid_usd": k["pay_mid"],
        "top_roles": [[r[0], _num(r[1] * 100)] for r in co["role_mix"][:3]],
        "distinctive_skills": [[s[0], round(s[3], 1)] for s in co["skills"][:4]],
        "top_hubs": [[h[0], _num(h[1] * 100)] for h in co["hubs"][:3]],
        "nearest_peer": co["peers"][0] if co["peers"] else None,
        "recent_models": [[m["date"], m["model"]] for m in models[:3]],
        "financials": fin_fact, "patents": pat,
        "funding": [{"event": f["event"], "date": f["date"], "open_roles_change_26w_after": f["change_26w_after"]}
                    for f in funding],
    }


def build_facts(data: dict) -> dict:
    out = {}
    for co in FOCUS:
        out[co] = {"facts": company_facts(co, data), "claims": theme_claims(co, data),
                   "expansions": expansion_claims(co, data)}
    return out


# ---------------------------------------------------------------- templates (always available)

def _pct(v):
    return f"{'+' if v > 0 else ''}{v}%"


def template_company(co: str, f: dict) -> dict:
    facts, claims, exps = f["facts"], f["claims"], f["expansions"]
    top = claims[0] if claims else None
    head = f"{co}: {top['label'].lower()}" if top else f"{co}: steady hiring"
    if facts["unit"] == "open roles":
        size = f"{co} has {facts['size']['value']:,.0f} open roles"
    else:
        size = f"{co} is opening about {facts['size']['value']:.0f} new requisitions a day"
    mom = f", {_pct(facts['change_6m_pct'])} in six months" if facts["change_6m_pct"] is not None else ""
    lede = [size + mom + "."]
    if top:
        place = f", concentrated in {' and '.join(top['concentrated_in'][:2])}" if top["concentrated_in"] else ""
        lede.append(f"The clearest signal is {top['label'].lower()}: {top['key_fact']}{place}.")
    new = [e for e in exps if e["status"] == "watch"]
    if new:
        lede.append(f"Unannounced new cities: {', '.join(e['city'] for e in new)}.")
    watch = (f"Whether {new[0]['city']} gets an official announcement." if new
             else f"Whether the {top['label'].lower()} signal keeps growing." if top else "The next snapshot.")
    return {"headline": head, "lede": " ".join(lede), "claims": {c["id"]: {"title": c["label"], "reading": c["reading"]}
                                                                 for c in claims}, "watch": watch}


def template_brief(facts: dict) -> dict:
    tops = [(co, f["claims"][0]) for co, f in facts.items() if f["claims"]]
    tops.sort(key=lambda x: -x[1]["strength"])
    bullets = [f"{co}: {c['label'].lower()} ({c['key_fact']})." for co, c in tops[:3]]
    return {"headline": "What the job boards say this week",
            "paragraph": " ".join(bullets) if bullets else "No strong new signals this week.", "bullets": bullets}


# ---------------------------------------------------------------- narrator (LLM) + number check

SYSTEM = (
    "You are an analyst writing a competitive-intelligence briefing from job-posting evidence. Write plain, confident "
    "English for busy executives: short sentences, no hype, no marketing words, no emojis. Use ONLY the facts in the "
    "JSON you are given. Every number you write must appear in the facts (you may round percentages). Do not invent "
    "products, partners, dates, cities or reasons. When evidence is only from job postings, say what it suggests "
    "(\"suggests\", \"points to\"), not what is certain.\n"
    "What makes a good story: lead with what CHANGED (key_fact growth such as '6 → 25') or what is DISTINCTIVE versus "
    "peers (lift), and WHERE it is happening (concentrated_in, new-city summaries). Connect signals when they fit "
    "together (e.g. data-center roles + a new city whose first posting is a data-center role; patents rising with "
    "research hiring). Do not repeat 'X% of openings' for every claim; a claim's reading should explain what it "
    "suggests and why, using a place, an example job title or a corroborating headline. A claim with confidence "
    "'confirmed' has a matching headline or event; mention it. Answer with a single JSON object.")

GLOSSARY = {
    "open_roles": "postings in this theme open now",
    "lift_vs_peers": "this company's share of postings in the theme divided by the average share at the other focus "
                     "companies. 1.0 = same as peers; below 1.3 = roughly the same, do not call it a spike or surge; "
                     "3+ = a strong specialisation. It is NOT growth over time",
    "new_13w / prior_13w": "postings first seen in the last 13 weeks vs the 13 weeks before (growth over time); "
                           "only exists for Anthropic and OpenAI, which have dated history",
    "key_fact": "the single most telling number for the claim, already worded; prefer quoting it",
    "confidence": "confirmed = a matching headline or event exists; likely = strong posting signal; watch = weak or "
                  "early signal, word it cautiously",
    "change_6m_pct / forecast_next_8_weeks_pct": "change of the tracked hiring series (size.metric)",
    "patents": "EPO patent publications naming the company as applicant, last 4 complete quarters vs the 4 before",
}
MULTIPLE_WORDS = {"double": 2, "doubled": 2, "doubles": 2, "two-fold": 2, "twofold": 2, "triple": 3, "tripled": 3,
                  "triples": 3, "three-fold": 3, "threefold": 3, "four-fold": 4, "fourfold": 4, "quadrupled": 4,
                  "five-fold": 5, "fivefold": 5, "ten-fold": 10, "tenfold": 10}

NUM = re.compile(r"(?<![\w.])\$?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(%|×|x\b|[kKmMbB]\b)?")


def _numbers(obj) -> set[float]:
    s = json.dumps(obj, ensure_ascii=False)
    vals = set()
    for m in NUM.finditer(s):
        v = float(m.group(1).replace(",", ""))
        vals.add(v)
        if m.group(2) == "%" or (0 < v < 1 and "." in m.group(1)):
            vals.add(round(v * 100, 1) if v < 1 else v)
    return vals


def unsupported_numbers(text: str, facts: dict) -> list[str]:
    """Numbers in `text` that do not match any number in `facts` (years, ordinals and 1-10 as words are fine)."""
    allowed = _numbers(facts)
    for v in list(allowed):  # allow rounded forms
        allowed |= {round(v), round(v, 1), round(v / 1e9, 1), round(v / 1e3), round(v * 100)}
    bad = []
    for m in NUM.finditer(text):
        raw = m.group(1).replace(",", "")
        v = float(raw)
        if 2000 <= v <= 2035 or v in (0, 1, 2, 3, 4, 5, 6, 8, 12, 13, 26, 52, 80, 100):  # years, horizons, generic
            continue
        if any(abs(v - a) <= max(1.0, 0.02 * abs(a)) for a in allowed):
            continue
        bad.append(m.group(0))
    # multiples written as words ("doubled", "four-fold") describe growth over time: they must match a growth
    # ratio in the facts (within 25%), not a lift versus peers
    ratios = [v for k, v in _walk(facts) if k == "growth" and isinstance(v, (int, float))]
    ratios += [d["new_13w"] / d["prior_13w"] for d in _dicts(facts) if d.get("new_13w") and d.get("prior_13w")]
    ratios += [float(m.group(1)) for m in re.finditer(r"new roles per 13 weeks \(([\d.]+)×\)",
                                                      json.dumps(facts, ensure_ascii=False))]
    for w in re.findall(r"\b(" + "|".join(map(re.escape, MULTIPLE_WORDS)) + r")\b", text.lower()):
        target = MULTIPLE_WORDS[w]
        if not any(abs(r - target) <= 0.25 * target for r in ratios):
            bad.append(w)
    return bad


def _dicts(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _dicts(v)
    elif isinstance(o, list):
        for v in o:
            yield from _dicts(v)


def _walk(o, key=None):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, k)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v, key)
    else:
        yield key, o


def _strings(obj) -> str:
    if isinstance(obj, dict):
        return " ".join(_strings(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_strings(v) for v in obj)
    return str(obj) if isinstance(obj, str) else ""


def llm_view(f: dict) -> dict:
    """The part of the evidence the narrator sees (smaller = fits the free tier's tokens-per-minute budget)."""
    keep = ("id", "label", "confidence", "key_fact", "concentrated_in", "open_roles", "lift_vs_peers", "new_13w",
            "prior_13w")
    return {"facts": f["facts"],
            "claims": [{**{k: c[k] for k in keep}, "example_titles": c["examples"][:3],
                        "corroborating_headlines": [h["title"] for h in c["corroboration"]]} for c in f["claims"]],
            "new_cities": [e["summary"] for e in f["expansions"]]}


def _ask(prompt: dict, facts_for_check: dict, label: str, max_tokens: int = 2500) -> tuple[dict | None, str]:
    """LLM call + number check; one retry that names the unsupported numbers."""
    msg = json.dumps(prompt, ensure_ascii=False, default=str)
    for attempt in range(2):
        res = llm.chat_json(SYSTEM, msg, max_tokens=max_tokens)
        if not res:
            return None, "template"
        obj, model = res
        bad = unsupported_numbers(_strings(obj), facts_for_check)
        if not bad:
            return obj, model
        print(f"  {label}: unsupported numbers {bad[:5]}" + (", retrying" if attempt == 0 else ", using template"))
        msg = json.dumps({**prompt, "previous_attempt_problem": f"These numbers are not in the facts: {bad[:8]}. "
                          "Rewrite using only numbers that appear in the facts."}, ensure_ascii=False, default=str)
        time.sleep(20)
    return None, "template (LLM numbers not in evidence)"


def narrate_company(co: str, f: dict, template: dict) -> tuple[dict, str]:
    view = llm_view(f)
    prompt = {
        "task": f"Write the {co} chapter of a hiring-intelligence page.",
        "output_schema": {
            "headline": "max 12 words: the single most important thing the hiring shows, as a statement",
            "lede": "2-3 sentences: the story, connecting the strongest signals (change, place, corroboration)",
            "claims": {"<claim id>": {"title": "max 8 words, a statement", "reading": "1-2 sentences: what this "
                                      "suggests and why, with a place, example title or headline"}},
            "watch": "1 sentence: the concrete next signal that would confirm or reject the story",
        },
        "claim_ids": [c["id"] for c in f["claims"]],
        "glossary": GLOSSARY,
        "evidence": view,
    }
    obj, model = _ask(prompt, view, co)
    if obj is None:
        return template, model
    if not isinstance(obj.get("claims"), dict) or not obj.get("headline") or not obj.get("lede"):
        return template, "template (malformed LLM output)"
    claims = {cid: {**template["claims"][cid], **{k: v for k, v in (obj["claims"].get(cid) or {}).items()
                                                  if k in ("title", "reading") and isinstance(v, str)}}
              for cid in template["claims"]}
    return {"headline": obj["headline"], "lede": obj["lede"], "claims": claims,
            "watch": obj.get("watch") or template["watch"]}, model


def narrate_brief(facts: dict, template: dict) -> tuple[dict, str]:
    slim = {co: {"size": f["facts"]["size"], "change_6m_pct": f["facts"]["change_6m_pct"],
                 "top_claims": [{k: c[k] for k in ("label", "key_fact", "concentrated_in", "confidence")}
                                for c in f["claims"][:2]],
                 "new_cities": [e["summary"] for e in f["expansions"][:3]],
                 "patents": {k: v for k, v in (f["facts"]["patents"] or {}).items() if k != "recent_patent_titles"}}
            for co, f in facts.items()}
    prompt = {"task": "Write the opening briefing of a hiring-intelligence page covering Anthropic, OpenAI, NVIDIA "
                      "and Google: what are these companies preparing for, judged by who they hire and where?",
              "output_schema": {"headline": "max 12 words, the big picture across the four companies",
                                "paragraph": "3-4 sentences connecting the strongest signals across companies",
                                "bullets": []},
              "glossary": GLOSSARY, "evidence": slim}
    obj, model = _ask(prompt, slim, "brief", max_tokens=1800)
    if obj is None:
        return template, model
    if not obj.get("paragraph"):
        return template, "template (malformed LLM output)"
    # bullets stay deterministic (exact key facts); the model writes only the headline and the connecting paragraph
    return {"headline": obj.get("headline") or template["headline"], "paragraph": obj["paragraph"],
            "bullets": template["bullets"]}, model


def main() -> None:
    data = load()
    facts = build_facts(data)
    (D / "insights").mkdir(exist_ok=True)
    (D / "insights" / "story_facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False, default=str),
                                                     encoding="utf-8")
    providers = llm.available()
    print("narrator:", ", ".join(providers) or "templates only")
    pause = 25 if providers else 0  # stay under Groq's 8k tokens/minute
    brief, brief_by = narrate_brief(facts, template_brief(facts))
    chapters = {}
    for co in FOCUS:
        time.sleep(pause)
        text, by = narrate_company(co, facts[co], template_company(co, facts[co]))
        chapters[co] = {"text": text, "written_by": by, **facts[co]}
        print(f"{co}: {len(facts[co]['claims'])} claims, {len(facts[co]['expansions'])} expansions · {by}")
    out = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
           "brief": {**brief, "written_by": brief_by}, "chapters": chapters,
           "method": "Claims come from fixed interpretation rules over job titles and locations (src/insights/story.py). "
                     "Prose is written by an open model from those facts only and rejected if it cites a number "
                     "that is not in the evidence."}
    (DASH / "story.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":"), default=str),
                                     encoding="utf-8")
    print(f"story.json: {(DASH / 'story.json').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
