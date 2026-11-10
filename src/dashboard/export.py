"""Export compact JSON for the intelligence console (dashboard/data/*.json).

Usage:  python -m src.dashboard.export    (after the pipeline + src.external.sources have run)

Files
    meta.json       timestamps, coverage counts, sources
    companies.json  focus companies: KPIs, history + forecast, functions, role mix, skills, hubs, peers
    globe.json      footprint points, HQ -> new-city arcs (status: led / simultaneous / lagged / watch)
    signals.json    the "what changed" feed: new cities, watchlist, news matches, surges, filings, model releases
    news.json       latest headlines (headline + link only), topic-tagged
    tracker.json    frozen-forecast scorecard, watchlist status, lead-lag cases
    market.json     17-company similarity network + talent-pool highlights
    context.json    SEC financials, model releases, patents, WARN notices
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.collect.peers import segment
from src.forecast.series import build
from src.style import COMPANIES, COMPANY_COLOR

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
OUT = ROOT / "dashboard" / "data"
SERIES = {"Anthropic": "anthropic_open", "OpenAI": "openai_open", "Google": "google_open", "NVIDIA": "nvidia_reqs"}
HQ = {"Anthropic": ("San Francisco", 37.7749, -122.4194), "OpenAI": ("San Francisco", 37.7749, -122.4194),
      "NVIDIA": ("Santa Clara", 37.3541, -121.9552), "Google": ("Mountain View", 37.3861, -122.0839)}
TAGLINE = {
    "Anthropic": "Safety-first frontier lab scaling go-to-market fast",
    "OpenAI": "Product & platform engineering at consumer scale",
    "NVIDIA": "The accelerated-computing stack, from silicon to robotics",
    "Google": "Cloud selling, GenAI and a deep management layer",
}
# word boundaries matter: a bare "opens?" would match inside "OpenAI"
OFFICE_WORDS = r"\b(?:offices?|hubs?|headquarter\w*|expan\w*|opens?|opening|launch(?:es)? in|enters?)\b"


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if (o != o) else round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.strftime("%Y-%m-%d")
    return o


def write(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(_clean(obj), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def ts(s: pd.Series) -> list:
    return [[d.strftime("%Y-%m-%d"), round(float(v), 1)] for d, v in s.items()]


# ---------------------------------------------------------------- builders


def companies(series) -> dict:
    prof = pd.read_csv(D / "comparison" / "company_profiles.csv", index_col=0)
    fam = pd.read_csv(D / "comparison" / "role_family_mix.csv", index_col=0)
    ds = pd.read_csv(D / "comparison" / "distinctive_skills.csv")
    hubs = pd.read_csv(D / "comparison" / "top_hubs.csv").set_index("company")["top hubs"]
    sim = pd.read_csv(D / "similarity" / "similarity_combined.csv", index_col=0)
    fc = pd.read_csv(D / "forecasts" / "latest_forecast.csv")
    out = {}
    for c in COMPANIES:
        s = series[SERIES[c]]
        f = fc[fc.series == SERIES[c]]
        p = prof[c]
        back = s.y.iloc[-27] if len(s.y) > 27 else s.y.iloc[0]
        funcs = {}
        for short, label in [("gtm", "Go-to-market"), ("research", "Research"), ("product", "Product"),
                             ("compute", "Compute"), ("corporate", "Corporate")]:
            sid = f"{c.lower()}_open_{short}"
            if sid in series:
                funcs[label] = ts(series[sid].y)
        hub_list = [(m.group(1), int(m.group(2)) / 100) for part in hubs[c].split(" · ")
                    for m in [re.match(r"(.+?)\s+(\d+)%$", part.strip())] if m]
        d = ds[(ds.company == c) & ds.distinctive].head(8)
        out[c] = {
            "color": COMPANY_COLOR[c], "logo": f"assets/logos/{c.lower()}.svg", "tagline": TAGLINE[c],
            "segment": segment(c), "unit": s.unit, "series_label": s.label,
            "kpi": {"open_postings": int(p["open postings (all roles)"]),
                    "tech_share": p["technical share of postings"],
                    "pay_mid": p.get("median pay midpoint, USD (tech)"),
                    "phd": p["PhD mentioned (tech)"], "min_years": p["median min. years (tech)"],
                    "momentum_6m": s.y.iloc[-1] / back - 1,
                    "outlook_8w": f.point.iloc[-1] / f.last_actual.iloc[-1] - 1,
                    "outlook_point": f.point.iloc[-1], "outlook_lo": f.lo80.iloc[-1], "outlook_hi": f.hi80.iloc[-1],
                    "model": f.model.iloc[0]},
            "history": ts(s.y),
            "forecast": [[r.target_week, r.point, r.lo80, r.hi80] for r in f.itertuples()],
            "functions": funcs,
            "role_mix": [[k, v] for k, v in fam[c].sort_values(ascending=False).head(8).items()],
            "skills": [[r.skill, r.share, r.others_avg, r.lift] for r in d.itertuples()],
            "hubs": hub_list[:6],
            "peers": [[o, v] for o, v in sim[c].drop(c).nlargest(5).items()],
        }
    return out


def news_matches(news: pd.DataFrame, watch: pd.DataFrame) -> list[dict]:
    """Headlines that mention a watchlist company + city with office/expansion wording: possible confirmations."""
    hits = []
    for w in watch.itertuples():
        m = news[(news.company == w.company) & news.title.str.contains(rf"\b{re.escape(w.city)}\b", case=False)
                 & news.title.str.contains(OFFICE_WORDS, case=False)]
        for n in m.itertuples():
            hits.append({"company": w.company, "city": w.city, "date": n.date, "title": n.title, "url": n.url,
                         "source": n.source, "signal_date": str(w.first_seen),
                         "lead_days": (pd.Timestamp(n.date) - pd.Timestamp(w.first_seen)).days})
    return hits


def globe(series) -> dict:
    fp = pd.read_csv(D / "trends" / "city_footprint.csv")
    fp = fp[fp.company.isin(COMPANIES)]
    ex = pd.read_csv(D / "trends" / "expansion_signals.csv")
    ll = pd.read_csv(D / "insights" / "lead_lag.csv")
    watch = pd.read_csv(D / "insights" / "watchlist.csv")
    status = {(r.company, r.city): r.reading for r in ll.itertuples()}
    status.update({(r.company, r.city): "watch" for r in watch.itertuples()})
    arcs = []
    for r in ex[ex.signal].itertuples():
        hq = HQ[r.company]
        arcs.append({"company": r.company, "city": r.city, "country": r.country, "date": r.first_seen,
                     "start": [hq[1], hq[2]], "end": [r.lat, r.lon],
                     "status": status.get((r.company, r.city), "signal")})
    points = [{"company": r.company, "city": r.city, "country": r.country, "lat": r.lat, "lon": r.lon,
               "postings": int(r.postings)} for r in fp.itertuples()]
    return {"points": points, "arcs": arcs, "hq": {c: {"city": v[0], "lat": v[1], "lon": v[2]} for c, v in HQ.items()}}


def signals(series, news: pd.DataFrame, matches: list[dict]) -> list[dict]:
    items = []
    ll = pd.read_csv(D / "insights" / "lead_lag.csv")
    watch = pd.read_csv(D / "insights" / "watchlist.csv")
    for r in ll.itertuples():
        items.append({"date": r.signal_date, "company": r.company, "type": "new_city", "confidence": "confirmed",
                      "title": f"First posting in {r.city}",
                      "detail": f"Public event {r.event_date}: {r.reading} ({r.lead_days:+d} days)", "url": r.source})
    for r in watch.itertuples():
        items.append({"date": r.first_seen, "company": r.company, "type": "new_city", "confidence": "watch",
                      "title": f"First posting in {r.city}",
                      "detail": f"No public announcement yet · {r.days_since_signal} days and counting", "url": None})
    for m in matches:
        items.append({"date": m["date"], "company": m["company"], "type": "news_match", "confidence": "likely",
                      "title": f"News may confirm {m['city']} signal", "detail": m["title"], "url": m["url"]})
    # weekly surges in open roles by function (|change| ≥ 15% vs 4 weeks earlier)
    for sid, s in series.items():
        if "_open_" not in sid or len(s.y) < 6:
            continue
        chg = s.y.iloc[-1] / s.y.iloc[-5] - 1
        if abs(chg) >= 0.15:
            comp = s.company
            items.append({"date": s.y.index[-1].strftime("%Y-%m-%d"), "company": comp, "type": "surge",
                          "confidence": "confirmed", "title": f"{s.label.split(': ')[-1]} openings {chg:+.0%} in 4 weeks",
                          "detail": f"{s.y.iloc[-5]:.0f} → {s.y.iloc[-1]:.0f} open roles", "url": None})
    from src.trends.emerging_terms import THEMES  # curated, interpretable themes (not raw style phrases)

    em = pd.read_csv(D / "trends" / "emerging_terms.csv")
    curated = {t for terms in THEMES.values() for t in terms}
    for r in em[em.term.isin(curated)].sort_values("z", ascending=False).head(6).itertuples():
        items.append({"date": series["anthropic_open"].y.index[-1].strftime("%Y-%m-%d"), "company": "Anthropic + OpenAI",
                      "type": "emerging_term", "confidence": "confirmed", "title": f"Rising term: “{r.term}”",
                      "detail": f"{r.early_postings} → {r.recent_postings} postings (13-week windows)", "url": None})
    mr = pd.read_csv(D / "context" / "model_releases.csv")
    for r in mr[mr.company.isin(COMPANIES)].tail(8).itertuples():
        items.append({"date": r.date, "company": r.company, "type": "model_release", "confidence": "confirmed",
                      "title": f"Model release: {r.model}", "detail": "Epoch AI notable models (CC BY)", "url": r.link})
    fin = pd.read_csv(D / "context" / "financials_quarterly.csv")
    for c, g in fin[fin.metric == "revenue"].groupby("company"):
        g = g.sort_values("quarter_end")
        if len(g) >= 5:
            yoy = g.usd.iloc[-1] / g.usd.iloc[-5] - 1
            items.append({"date": g.quarter_end.iloc[-1], "company": c, "type": "filing", "confidence": "confirmed",
                          "title": f"Quarterly revenue ${g.usd.iloc[-1] / 1e9:.1f}B ({yoy:+.0%} YoY)",
                          "detail": "SEC 10-Q/10-K (XBRL)", "url": None})
    for n in news[news.topics.fillna("").str.contains("expansion|funding|government|infrastructure")].head(12).itertuples():
        items.append({"date": n.date, "company": n.company, "type": "news", "confidence": "context",
                      "title": n.title, "detail": f"{n.source} · {n.topics}", "url": n.url})
    return sorted(items, key=lambda i: str(i["date"]), reverse=True)


def tracker() -> dict:
    fz = sorted((D / "forecasts" / "frozen").glob("*.csv"))
    frozen = pd.read_csv(fz[0]) if fz else pd.DataFrame()
    sc_path = D / "forecasts" / "scorecard.csv"
    sc = pd.read_csv(sc_path) if sc_path.exists() and sc_path.stat().st_size > 5 else pd.DataFrame()
    head = frozen[frozen.series.isin(SERIES.values())] if len(frozen) else frozen
    return {
        "frozen_on": fz[0].stem if fz else None,
        "targets": len(frozen), "resolved": len(sc),
        "coverage80": float(sc.in_80.mean()) if len(sc) else None,
        "forecasts": [{"series": r.series, "company": r.company, "label": r.label, "target_week": r.target_week,
                       "h": r.h, "point": r.point, "lo": r.lo80, "hi": r.hi80, "last_actual": r.last_actual}
                      for r in head.itertuples()],
        "scored": sc.to_dict("records") if len(sc) else [],
        "lead_lag": pd.read_csv(D / "insights" / "lead_lag.csv").to_dict("records"),
        "watchlist": pd.read_csv(D / "insights" / "watchlist.csv").fillna("").to_dict("records"),
        "funding": pd.read_csv(D / "insights" / "funding_response.csv").to_dict("records"),
    }


def market() -> dict:
    S = pd.read_csv(D / "similarity" / "similarity_combined.csv", index_col=0)
    sizes = pd.read_csv(D / "comparison" / "company_profiles.csv", index_col=0)
    corpus_counts = pd.read_csv(D / "similarity" / "role_clusters.csv").company_name.value_counts()
    nodes = [{"name": c, "segment": segment(c), "postings": int(corpus_counts.get(c, 0)),
              "color": COMPANY_COLOR.get(c, "#8b949e"), "focus": c in COMPANY_COLOR} for c in S.index]
    edges, seen = [], set()
    for c in S.index:
        for o, v in S.loc[c].drop(c).nlargest(3).items():
            k = tuple(sorted((c, o)))
            if k not in seen:
                seen.add(k)
                edges.append({"source": k[0], "target": k[1], "value": round(float(v), 3)})
    pools = pd.read_csv(D / "similarity" / "talent_pool_shares.csv", index_col=0)
    top = pools.max(axis=1).sort_values(ascending=False).head(10).index
    return {"nodes": nodes, "edges": edges,
            "pools": {"names": list(top), "companies": list(pools.columns),
                      "values": pools.loc[top].round(3).values.tolist()}}


def context() -> dict:
    fin = pd.read_csv(D / "context" / "financials_quarterly.csv")
    mr = pd.read_csv(D / "context" / "model_releases.csv")
    pm = D / "context" / "patents_quarterly.csv"
    wn = D / "context" / "warn_notices.csv"
    return {
        "financials": {c: {m: [[r.quarter_end, r.usd] for r in g.sort_values("quarter_end").itertuples()]
                           for m, g in gc.groupby("metric")} for c, gc in fin.groupby("company")},
        "models": mr[["company", "model", "date", "domain", "link"]].fillna("").to_dict("records"),
        "patents": pd.read_csv(pm).to_dict("records") if pm.exists() else [],
        "patents_status": (f"{int(pd.read_csv(pm).publications.sum()):,} publications since 2023" if pm.exists()
                           else "awaiting EPO OPS key"),
        "warn": pd.read_csv(wn).fillna("").to_dict("records") if wn.exists() else [],
    }


def land() -> None:
    """Slim Natural Earth 1:110m countries (public domain) for the globe: geometry only, 2-decimal coordinates."""
    src = D / "external" / "naturalearth" / "ne_110m_admin_0_countries.geojson"
    gj = json.loads(src.read_text(encoding="utf-8"))

    def rnd(c):
        return [round(c[0], 2), round(c[1], 2)] if isinstance(c[0], (int, float)) else [rnd(x) for x in c]

    feats = [{"type": "Feature", "properties": {"n": f["properties"].get("NAME", "")},
              "geometry": {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"])}}
             for f in gj["features"] if f["properties"].get("NAME") != "Antarctica"]
    out = ROOT / "dashboard" / "assets" / "land.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    series = {s.id: s for s in build()}
    news_path = D / "context" / "news.csv"
    news = pd.read_csv(news_path).fillna("") if news_path.exists() else pd.DataFrame(
        columns=["date", "company", "title", "url", "source", "kind", "topics"])
    watch = pd.read_csv(D / "insights" / "watchlist.csv")
    matches = news_matches(news, watch)
    corpus_n = sum(1 for _ in open(D / "similarity" / "role_clusters.csv", encoding="utf-8")) - 1
    log = pd.read_csv(ROOT / "reports" / "collection-log.csv")
    write("meta.json", {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "last_snapshot": log.run_started_utc.max()[:10], "next_refresh": "Mon & Thu (GitHub Actions)",
        "companies_tracked": 17, "open_postings_now": corpus_n,
        "sources": ["Greenhouse & Ashby public job-board APIs", "NVIDIA Workday board", "Google Careers (sample)",
                    "Epoch AI hiring + notable models (CC BY)", "Internet Archive (counts)", "SEC EDGAR",
                    "Company newsroom RSS", "GDELT news", "EPO Open Patent Services", "California WARN notices"],
    })
    write("companies.json", companies(series))
    write("globe.json", globe(series))
    write("signals.json", signals(series, news, matches))
    write("news.json", news.head(80).to_dict("records"))
    write("tracker.json", tracker())
    write("market.json", market())
    write("context.json", context())
    land()
    sizes = {p.name: f"{p.stat().st_size / 1024:.0f} KB" for p in sorted(OUT.glob("*.json"))}
    print("exported:", sizes, "| news matches:", len(matches))


if __name__ == "__main__":
    main()
