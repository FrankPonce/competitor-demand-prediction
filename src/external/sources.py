"""Context data sources beyond job postings (Sprint 10): business outcomes, launches, news, patents, layoffs.

Run everything:   python -m src.external.sources          (each source is skipped gracefully if unavailable)
Outputs (all in data/context/):
    financials_quarterly.csv  SEC EDGAR XBRL: revenue, R&D, net income, capex (NVIDIA, Alphabet)
    model_releases.csv        Epoch AI "Notable AI Models" (CC BY): release dates by organisation
    news.csv                  headlines + links only, from company RSS feeds and GDELT (accumulates over runs)
    patents_quarterly.csv     EPO Open Patent Services: patent publications per applicant per quarter (needs key)
    patents_recent.csv        titles of each company's latest patent publications (topic signal)
    warn_notices.csv          California WARN layoff notices matching tracked companies (accumulates)

Secrets come from environment variables / a gitignored .env file, never from code:
    SEC_CONTACT_EMAIL (SEC's required contact header), EPO_OPS_KEY + EPO_OPS_SECRET (free EPO account).
"""

from __future__ import annotations

import base64
import csv
import io
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

from src.collect.common import PoliteSession, USER_AGENT
from src.collect.peers import PEERS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "context"
csv.field_size_limit(2**31 - 1)

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # pragma: no cover
    pass

TRACKED = ["Anthropic", "OpenAI", "NVIDIA", "Google"] + [v[0] for v in PEERS.values()]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- SEC EDGAR

EDGAR = {"NVIDIA": "0001045810", "Google": "0001652044"}  # Google -> Alphabet Inc.
METRICS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "rnd_expense": ["ResearchAndDevelopmentExpense"],
    "net_income": ["NetIncomeLoss"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
}


def _quarterly(entries: list[dict]) -> dict[str, float]:
    """Quarter-end -> 3-month value. Uses ~3-month facts directly; otherwise differences year-to-date facts."""
    out: dict[str, float] = {}
    by_start: dict[str, list] = {}
    for e in entries:
        if e.get("form") not in ("10-Q", "10-K") or "start" not in e:
            continue
        days = (datetime.fromisoformat(e["end"]) - datetime.fromisoformat(e["start"])).days
        if 80 <= days <= 100:
            out[e["end"]] = e["val"]
        by_start.setdefault(e["start"], []).append(e)
    for start, es in by_start.items():  # cumulative (YTD) series sharing a fiscal-year start
        es = sorted({e["end"]: e for e in es}.values(), key=lambda e: e["end"])
        first_days = (datetime.fromisoformat(es[0]["end"]) - datetime.fromisoformat(start)).days
        if not 80 <= first_days <= 100:
            continue  # chain must start with a genuine first quarter, or YTD totals would pose as quarters
        prev_end, prev_val = es[0]["end"], es[0]["val"]
        out.setdefault(prev_end, prev_val)
        for e in es[1:]:
            step = (datetime.fromisoformat(e["end"]) - datetime.fromisoformat(prev_end)).days
            if not 80 <= step <= 100:
                break  # gap in the chain: stop rather than merge two quarters into one
            out.setdefault(e["end"], e["val"] - prev_val)
            prev_end, prev_val = e["end"], e["val"]
    return out


def edgar() -> pd.DataFrame | None:
    contact = os.environ.get("SEC_CONTACT_EMAIL")
    if not contact:
        print("EDGAR: skipped (set SEC_CONTACT_EMAIL)")
        return None
    s = PoliteSession(delay_seconds=0.5)
    s.s.headers["User-Agent"] = f"competitor-demand-prediction research {contact}"
    rows = []
    for company, cik in EDGAR.items():
        facts = s.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").json()["facts"].get("us-gaap", {})
        for metric, tags in METRICS.items():
            q: dict[str, float] = {}
            for tag in tags:  # later tags only fill gaps (filers switch tags over the years)
                if tag in facts:
                    for end, v in _quarterly(facts[tag]["units"].get("USD", [])).items():
                        q.setdefault(end, v)
            for end, v in q.items():
                rows.append({"company": company, "entity": "Alphabet Inc." if company == "Google" else "NVIDIA Corp.",
                             "quarter_end": end, "metric": metric, "usd": v})
    df = pd.DataFrame(rows)
    df = df[pd.to_datetime(df.quarter_end) >= "2021-01-01"].sort_values(["company", "metric", "quarter_end"])
    df.to_csv(OUT / "financials_quarterly.csv", index=False)
    print(f"EDGAR: {len(df)} quarterly values")
    return df


# ---------------------------------------------------------------- Epoch AI notable models

MODEL_ORGS = {"Anthropic": r"anthropic", "OpenAI": r"openai", "Google": r"google|deepmind",
              "NVIDIA": r"nvidia", "xAI": r"\bxai\b", "Cohere": r"cohere", "Databricks": r"databricks|mosaic"}


def model_releases() -> pd.DataFrame:
    raw = PoliteSession(1.0, 120).get("https://epoch.ai/data/notable_ai_models.csv").text
    d = pd.read_csv(io.StringIO(raw))
    d["date"] = pd.to_datetime(d["Publication date"], errors="coerce")
    rows = []
    for company, rx in MODEL_ORGS.items():
        m = d[d.Organization.fillna("").str.contains(rx, case=False, regex=True) & (d.date >= "2022-01-01")]
        for r in m.itertuples():
            rows.append({"company": company, "model": r.Model, "date": r.date.date(), "domain": r.Domain,
                         "organization": r.Organization,
                         "training_compute_flop": d.loc[r.Index, "Training compute (FLOP)"], "link": r.Link})
    out = pd.DataFrame(rows).sort_values("date")
    out.to_csv(OUT / "model_releases.csv", index=False)
    print(f"Epoch models: {len(out)} releases since 2022 (Epoch AI, CC BY)")
    return out


# ---------------------------------------------------------------- news (RSS + GDELT)

RSS = {
    "OpenAI": ["https://openai.com/news/rss.xml"],
    "Google": ["https://blog.google/technology/ai/rss/"],
    "NVIDIA": ["https://nvidianews.nvidia.com/releases.xml"],
}
GDELT_QUERIES = {
    "Anthropic": '"Anthropic" (Claude OR AI)',
    "OpenAI": '"OpenAI"',
    "NVIDIA": '"Nvidia"',
    "Google": '("Google DeepMind" OR "Google Cloud" OR "Gemini")',
    "xAI": '"xAI" Musk',
}
TOPICS = {
    "expansion": r"\boffice\b|opens? .* (hub|office)|expan(d|sion)|new (hub|office|headquarters)|headquarter",
    "funding": r"funding|raises|valuation|series [a-z]\b|investment round|ipo\b",
    "launch": r"launch|releases?|introduc|unveil|announces? .*(model|product)|\bgpt-|\bclaude\b|\bgemini\b",
    "people": r"layoff|job cuts|hiring|hires|talent|poach|headcount|workforce",
    "government": r"government|defen[cs]e|pentagon|military|federal|national security|regulat",
    "infrastructure": r"data ?cent(er|re)|gigawatt|\bgw\b|compute|supercomputer|chips?|stargate",
    "partnership": r"partner(ship)?|deal with|agreement|collaborat",
}


def _topics(title: str) -> str:
    return ";".join(k for k, rx in TOPICS.items() if re.search(rx, title, re.I))


def news() -> pd.DataFrame:
    import feedparser

    rows = []
    for company, urls in RSS.items():
        for u in urls:
            feed = feedparser.parse(u, agent=USER_AGENT)
            for e in feed.entries[:200]:
                t = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
                rows.append({"date": time.strftime("%Y-%m-%d", t) if t else _now(), "company": company,
                             "title": e.get("title", "").strip(), "url": e.get("link", ""),
                             "source": f"{company} newsroom", "kind": "official"})
    s = PoliteSession(delay_seconds=6.0, timeout=60)  # GDELT asks for ≤ 1 request / 5 s
    for company, q in GDELT_QUERIES.items():
        try:
            r = s.get("https://api.gdeltproject.org/api/v2/doc/doc",
                      params={"query": f"{q} sourcelang:english", "mode": "artlist", "format": "json",
                              "maxrecords": 150, "timespan": "3months", "sort": "datedesc"})
            arts = r.json().get("articles", []) if r.text.strip().startswith("{") else []
        except Exception as ex:  # GDELT occasionally returns rate-limit text instead of JSON
            print(f"GDELT {company}: {ex}")
            arts = []
        for a in arts:
            rows.append({"date": f"{a['seendate'][:4]}-{a['seendate'][4:6]}-{a['seendate'][6:8]}",
                         "company": company, "title": a.get("title", "").strip(), "url": a.get("url", ""),
                         "source": a.get("domain", ""), "kind": "press"})
    new = pd.DataFrame(rows)
    new = new[new.title.str.len() > 15]
    new["topics"] = new.title.map(_topics)
    path = OUT / "news.csv"
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=new.columns)
    allr = pd.concat([old, new], ignore_index=True)
    allr["key"] = allr.title.str.lower().str.replace(r"\W+", " ", regex=True).str.strip()
    allr = allr.sort_values("date").drop_duplicates(["company", "key"], keep="first").drop(columns="key")
    allr.sort_values("date", ascending=False).to_csv(path, index=False)
    print(f"News: {len(new)} fetched, {len(allr)} stored (headline + link only)")
    return allr


# ---------------------------------------------------------------- EPO Open Patent Services

OPS_APPLICANTS = {"Anthropic": "anthropic", "OpenAI": "openai", "NVIDIA": "nvidia", "Google": "google"}
OPS_SEARCH = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"


def _ops_session():
    key, secret = os.environ.get("EPO_OPS_KEY"), os.environ.get("EPO_OPS_SECRET")
    if not key or not secret:
        return None
    tok = requests.post("https://ops.epo.org/3.2/auth/accesstoken", data={"grant_type": "client_credentials"},
                        headers={"Authorization": "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode(),
                                 "Content-Type": "application/x-www-form-urlencoded"}, timeout=60)
    tok.raise_for_status()
    # EPO fair use: the search quota is small (X-Throttling-Control "search=green:5"), so stay well under it.
    s = PoliteSession(delay_seconds=13, timeout=90)
    s.s.headers.update({"Authorization": f"Bearer {tok.json()['access_token']}", "Accept": "application/json"})
    return s


def _ops_search(s, q: str, rng: str = "1-1") -> dict | None:
    try:
        r = s.get(f"{OPS_SEARCH}?q={quote(q)}", headers={"X-OPS-Range": rng})
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:  # OPS answers 404 when nothing matches
            return None
        raise
    return r.json()["ops:world-patent-data"]["ops:biblio-search"]


def _quarters(since: str, today: datetime) -> list[tuple[str, str, str]]:
    out, y, q = [], int(since), 1
    while (y, q) <= (today.year, (today.month - 1) // 3 + 1):
        m0 = 3 * (q - 1) + 1
        end = (datetime(y + (m0 + 3 > 12), (m0 + 3 - 1) % 12 + 1, 1) - timedelta(days=1))
        out.append((f"{y}Q{q}", f"{y}{m0:02d}01", end.strftime("%Y%m%d")))
        q = q % 4 + 1
        y += q == 1
    return out


def patents(since: str = "2023") -> pd.DataFrame | None:
    """Patent publications per applicant per quarter (counts) + titles of the latest publications.

    Counts come from OPS's total-result-count (one tiny request per company-quarter). Finished quarters are cached
    in patents_quarterly.csv and never re-queried; the last two quarters are refreshed on each run because
    publications keep arriving for a while.
    """
    s = _ops_session()
    if s is None:
        print("Patents: skipped (set EPO_OPS_KEY and EPO_OPS_SECRET; free at developers.epo.org)")
        return None
    today = datetime.now(timezone.utc)
    path = OUT / "patents_quarterly.csv"
    old = pd.read_csv(path, dtype={"quarter": str}) if path.exists() else pd.DataFrame(
        columns=["company", "quarter", "publications"])
    qs = _quarters(since, today)
    fresh = {q for q, _, _ in qs[-2:]}
    have = {(r.company, r.quarter) for r in old.itertuples() if r.quarter not in fresh}
    rows = [r._asdict() for r in old.itertuples(index=False) if (r.company, r.quarter) in have]
    for company, name in OPS_APPLICANTS.items():
        for q, d0, d1 in qs:
            if (company, q) in have:
                continue
            res = _ops_search(s, f'pa="{name}" and pd within "{d0} {d1}"')
            rows.append({"company": company, "quarter": q,
                         "publications": int(res["@total-result-count"]) if res else 0})
    quarterly = pd.DataFrame(rows).sort_values(["company", "quarter"])
    quarterly.to_csv(path, index=False)

    # latest titles: what the newest filings are about (last ~6 months)
    d0 = (today - timedelta(days=183)).strftime("%Y%m%d")
    titles = []
    for company, name in OPS_APPLICANTS.items():
        res = _ops_search(s, f'pa="{name}" and pd>={d0}', "1-50")
        docs = (res or {}).get("ops:search-result", {}).get("exchange-documents", [])
        docs = docs if isinstance(docs, list) else [docs]
        for d in docs:
            ed = d.get("exchange-document", {})
            bib = ed.get("bibliographic-data", {})
            pubref = bib.get("publication-reference", {}).get("document-id", [])
            pubref = pubref if isinstance(pubref, list) else [pubref]
            date = next((p.get("date", {}).get("$") for p in pubref if p.get("date")), None)
            tl = bib.get("invention-title", [])
            tl = tl if isinstance(tl, list) else [tl]
            title = next((t.get("$") for t in tl if t.get("@lang") == "en"), None)
            if title:
                titles.append({"company": company, "country": ed.get("@country"), "doc_number": ed.get("@doc-number"),
                               "family_id": ed.get("@family-id"),
                               "pub_date": f"{date[:4]}-{date[4:6]}-{date[6:8]}" if date else None, "title": title})
    t = pd.DataFrame(titles, columns=["company", "country", "doc_number", "family_id", "pub_date", "title"])
    t.drop_duplicates(["company", "family_id"]).to_csv(OUT / "patents_recent.csv", index=False)
    print(f"Patents: {len(quarterly)} company-quarters, {len(t)} recent titles")
    return quarterly


# ---------------------------------------------------------------- California WARN notices

WARN_URL = "https://edd.ca.gov/siteassets/files/jobs_and_training/warn/warn_report1.xlsx"
WARN_NAMES = {c: re.compile(rf"\b{re.escape(c)}\b", re.I) for c in TRACKED}
WARN_NAMES["Google"] = re.compile(r"\bgoogle\b|\balphabet\b|\bwaymo\b", re.I)


def warn() -> pd.DataFrame:
    raw = PoliteSession(1.0, 120).get(WARN_URL).content
    df = pd.read_excel(io.BytesIO(raw), sheet_name="Detailed WARN Report ", header=1)
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    comp_col = next(c for c in df.columns if c.lower().startswith("company"))
    rows = []
    for r in df.itertuples(index=False):
        name = str(getattr(r, comp_col.replace(" ", "_").replace("/", "_"), "") or r[df.columns.get_loc(comp_col)])
        for company, rx in WARN_NAMES.items():
            if rx.search(name):
                rec = dict(zip(df.columns, r))
                rows.append({"company": company, "employer": name,
                             "notice_date": str(rec.get("Notice Date", ""))[:10],
                             "effective_date": str(rec.get("Effective Date", ""))[:10],
                             "employees": rec.get("No. Of Employees"), "type": rec.get("Layoff/Closure"),
                             "county": rec.get("County/Parish"), "state": "CA", "source": WARN_URL})
    new = pd.DataFrame(rows, columns=["company", "employer", "notice_date", "effective_date", "employees", "type",
                                      "county", "state", "source"])
    path = OUT / "warn_notices.csv"
    old = pd.read_csv(path) if path.exists() else new.iloc[0:0]
    allr = pd.concat([old, new], ignore_index=True).drop_duplicates(["employer", "notice_date", "employees"])
    allr.to_csv(path, index=False)
    print(f"WARN (CA): {len(new)} matching notices this report, {len(allr)} stored; "
          f"{len(df)} notices scanned")
    return allr


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (edgar, model_releases, news, patents, warn):
        try:
            fn()
        except Exception as e:  # one failing source must not stop the others
            print(f"{fn.__name__}: FAILED {e}")


if __name__ == "__main__":
    main()
