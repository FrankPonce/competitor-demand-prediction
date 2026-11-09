"""Sprint 5 addendum: geographic footprint, expansion signals and pay trends.

Usage:  python -m src.trends.geo_pay

Expansion signal = the first date a city appears in a company's postings. Only Anthropic and OpenAI
have the history for this (Epoch AI since 2026-03-18 + our snapshots). Cities already present in the
first two weeks are treated as the existing footprint; later first appearances are expansion signals.

Geodata: city coordinates from GeoNames (CC BY 4.0, via `geonamescache`), country outlines from
Natural Earth 1:110m (public domain).

Outputs: data/trends/city_footprint.csv, expansion_signals.csv, pay_trend_monthly.csv
         reports/trends/figures/footprint_map.png, expansion_map.png, pay_trend.png
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

from src.preprocess.corpus_io import load_corpus  # noqa: E402
from src.style import COMPANIES, COMPANY_COLOR, THEME, apply_matplotlib, footnote  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "trends"
FIG = ROOT / "reports" / "trends" / "figures"
WORLD = ROOT / "data" / "external" / "naturalearth" / "ne_110m_admin_0_countries.geojson"
EPOCH_START = pd.Timestamp("2026-03-18")
BASELINE_END = EPOCH_START + pd.Timedelta(days=14)
apply_matplotlib()

ALIASES = {"new york city": "New York", "nyc": "New York", "bengaluru": "Bangalore", "zürich": "Zurich",
           "washington": "Washington", "washington d.c.": "Washington", "washington dc": "Washington",
           "sf": "San Francisco", "são paulo": "Sao Paulo", "gurugram": "Gurgaon", "delhi": "New Delhi"}
_STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY "
              "NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())
EXTRA_COUNTRY = {"usa": "US", "us": "US", "united states": "US", "united states of america": "US", "uk": "GB",
                 "united kingdom": "GB", "england": "GB", "korea": "KR", "south korea": "KR", "uae": "AE",
                 "can": "CA", "the netherlands": "NL", "czechia": "CZ", "taiwan": "TW"}


@lru_cache(maxsize=1)
def _geo():
    import geonamescache

    gc = geonamescache.GeonamesCache(min_city_population=15000)
    countries = {c["name"].lower(): iso for iso, c in gc.get_countries().items()}
    countries.update(EXTRA_COUNTRY)
    index: dict[str, list] = {}
    for c in gc.get_cities().values():
        for nm in {c["name"], *(c.get("alternatenames") or [])}:
            if nm and len(nm) > 2:
                index.setdefault(nm.lower(), []).append(c)
    capitals = {iso: c.get("capital", "") for iso, c in gc.get_countries().items()}
    return countries, index, capitals


def parse_locations(loc: str) -> list[tuple[str, str]]:
    """'San Francisco, CA; London, UK' -> [('San Francisco','US'), ('London','GB')]; remote entries dropped."""
    countries, _, _ = _geo()
    out = []
    for part in str(loc).split(";"):
        p = part.strip()
        if not p or re.search(r"remote", p, re.I):
            continue
        hint = ""
        if ":" in p:  # Epoch: "United States: San Francisco"
            c, p = (s.strip() for s in p.split(":", 1))
            hint = countries.get(c.lower(), "")
        toks = [t.strip() for t in p.split(",") if t.strip()]
        if toks and toks[0] == "US" and len(toks) > 2:  # NVIDIA: "US, CA, Santa Clara, ..."
            toks, hint = toks[2:], "US"
        if toks and toks[0].lower() in countries and len(toks) > 1:  # NVIDIA: "Israel, Yokneam"
            hint, toks = countries[toks[0].lower()], toks[1:]
        for t in toks[1:]:
            if t in _STATES:
                hint = hint or "US"
            elif t.lower() in countries:
                hint = hint or countries[t.lower()]
        if not toks:
            continue
        city = ALIASES.get(toks[0].lower(), toks[0])
        if city.lower() in countries:  # country only
            hint, city = countries[city.lower()], ""
        out.append((city, hint))
    return out


@lru_cache(maxsize=None)
def geocode(city: str, hint: str) -> tuple[float, float, str, str] | None:
    countries, index, capitals = _geo()
    if not city and hint:  # country only -> capital
        city = capitals.get(hint, "")
    cands = index.get(city.lower(), [])
    if hint:
        in_country = [c for c in cands if c["countrycode"] == hint]
        if not in_country and capitals.get(hint) and city != capitals[hint]:
            # e.g. "Ontario, CAN": a province, not a city -> place it at the country's capital
            return geocode(capitals[hint], hint)
        cands = in_country
    if not cands:
        return None
    best = max(cands, key=lambda c: c["population"])
    return float(best["latitude"]), float(best["longitude"]), best["name"], best["countrycode"]


def explode(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in df.itertuples(index=False):
        for city, hint in parse_locations(r.location):
            g = geocode(city, hint)
            if g:
                rows.append({"job_id": r.job_id, "company": r.company_name, "city": g[2], "country": g[3],
                             "lat": g[0], "lon": g[1], "first_seen": r.first_seen_date, "active": r.active})
    e = pd.DataFrame(rows)
    e["first_seen"] = pd.to_datetime(e.first_seen)
    return e


# ---------------------------------------------------------------- maps


def _basemap(ax) -> None:
    gj = json.loads(WORLD.read_text(encoding="utf-8"))
    for f in gj["features"]:
        if f["properties"].get("ADMIN") == "Antarctica":
            continue
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            ax.add_patch(Polygon(np.array(poly[0]), closed=True, facecolor=THEME["panel"],
                                 edgecolor=THEME["axis"], linewidth=0.4, zorder=1))
    ax.set_xlim(-130, 162)
    ax.set_ylim(-45, 68)
    ax.set_aspect("equal")
    ax.axis("off")


OFFSET = {"Anthropic": (-0.9, 0.6), "OpenAI": (0.9, 0.6), "NVIDIA": (-0.9, -0.6), "Google": (0.9, -0.6)}


def fig_footprint(fp: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 6.4))
    _basemap(ax)
    mx = fp.postings.max()
    for c in COMPANIES:
        d = fp[fp.company == c]
        dx, dy = OFFSET[c]
        ax.scatter(d.lon + dx, d.lat + dy, s=12 + 900 * (d.postings / mx) ** 0.6, color=COMPANY_COLOR[c],
                   alpha=0.75, edgecolor=THEME["surface"], linewidth=0.8, zorder=3, label=c)
    top = fp.groupby(["city", "lat", "lon"]).postings.sum().reset_index().sort_values("postings", ascending=False)
    placed = []
    for r in top.itertuples():  # label the biggest city per ~4° area so metro clusters stay readable
        if len(placed) >= 14 or any(abs(r.lat - la) < 4 and abs(r.lon - lo) < 4 for la, lo in placed):
            continue
        placed.append((r.lat, r.lon))
        ax.annotate(r.city, (r.lon, r.lat), xytext=(9, 7), textcoords="offset points", fontsize=8.5,
                    color=THEME["text"], zorder=4)
    leg = ax.legend(loc="lower left", fontsize=9, markerscale=0.6, frameon=False)
    for h in leg.legend_handles:
        h.set_sizes([60])
    ax.set_title("Hiring footprint: open postings by city (bubble area scales with postings)")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    footnote(fig, "Open postings in the latest snapshot · NVIDIA = full board, Google = sample · "
                  "GeoNames (CC BY) · Natural Earth")
    fig.savefig(FIG / "footprint_map.png")
    plt.close(fig)


def fig_expansion(ex: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 6.4))
    _basemap(ax)
    new = ex[ex.signal]
    old = ex[~ex.signal]
    for c in ["Anthropic", "OpenAI"]:
        o, n = old[old.company == c], new[new.company == c]
        dx, dy = OFFSET[c]
        ax.scatter(o.lon + dx, o.lat + dy, s=22, color=COMPANY_COLOR[c], alpha=0.35, zorder=2)
        ax.scatter(n.lon + dx, n.lat + dy, s=150, marker="*", color=COMPANY_COLOR[c],
                   edgecolor=THEME["text"], linewidth=0.6, zorder=4, label=f"{c}: new city")
        for r in n.itertuples():
            # flip the label left when another new city sits close to the east of this one
            crowded = ((new.lon - r.lon).between(0.1, 12) & (new.lat - r.lat).abs().lt(4)).any()
            ax.annotate(f"{r.city} ({r.first_seen:%b})", (r.lon + dx, r.lat + dy),
                        xytext=(-6, 4) if crowded else (6, 4), ha="right" if crowded else "left",
                        textcoords="offset points", fontsize=7.5, color=THEME["text"], zorder=5)
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.set_title("Expansion signals: cities first appearing in postings since April 2026 (stars) vs. existing footprint (dots)")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    footnote(fig, "Epoch AI history (CC BY) + project snapshots · first appearance of a city in any posting")
    fig.savefig(FIG / "expansion_map.png")
    plt.close(fig)


def fig_pay(pt: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for (c, grp), d in pt.groupby(["company", "group"]):
        d = d[d.n >= 8]
        if len(d) < 3:
            continue
        ls = "-" if grp == "Technical" else "--"
        ax.plot(pd.to_datetime(d.month), d.median_mid / 1000, color=COMPANY_COLOR[c], linestyle=ls, marker="o",
                markersize=4)
        ax.annotate(f"{c} · {grp}", (pd.to_datetime(d.month.iloc[-1]), d.median_mid.iloc[-1] / 1000),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=THEME["text"])
    ax.set_ylabel("median pay midpoint (k USD)")
    ax.set_title("Disclosed pay of new postings by month (solid = technical, dashed = sales & GTM)")
    ax.margins(x=0.18)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, "Months with ≥8 postings disclosing pay · base-pay range midpoint · equity excluded")
    fig.savefig(FIG / "pay_trend.png")
    plt.close(fig)


# ---------------------------------------------------------------- main


def main() -> None:
    corpus = load_corpus()
    feat = pd.read_parquet(ROOT / "data" / "features" / "posting_features.parquet")[["job_id", "role_family"]]
    df = corpus.merge(feat, on="job_id", how="left")
    df["active"] = df.in_live & (df.job_status == "active")
    e = explode(df)

    fp = (e[e.active].groupby(["company", "city", "country", "lat", "lon"]).job_id.nunique()
          .rename("postings").reset_index())
    fp.to_csv(OUT / "city_footprint.csv", index=False)

    h = e[e.company.isin(["Anthropic", "OpenAI"])]
    ex = (h.groupby(["company", "city", "country", "lat", "lon"])
          .agg(first_seen=("first_seen", "min"), postings_total=("job_id", "nunique"),
               open_now=("active", "sum")).reset_index())
    ex["signal"] = ex.first_seen > BASELINE_END
    ex.sort_values(["signal", "first_seen"], ascending=[False, True]).assign(
        first_seen=lambda d: d.first_seen.dt.date).to_csv(OUT / "expansion_signals.csv", index=False)

    tech = {"ML / AI Engineering", "Research", "Software Engineering", "Infrastructure & SRE",
            "Hardware & Silicon", "Data & Analytics", "Security & Privacy"}
    p = df[df.company_name.isin(["Anthropic", "OpenAI"]) & df.salary_min.notna()].copy()
    p["first_seen"] = pd.to_datetime(p.first_seen_date)
    p = p[p.first_seen > BASELINE_END]
    p["group"] = np.where(p.role_family.isin(tech), "Technical",
                          np.where(p.role_family == "Sales & Go-to-Market", "Sales & GTM", "Other"))
    p = p[p.group != "Other"]
    p["month"] = p.first_seen.dt.to_period("M").dt.start_time.dt.date
    p = p[p.first_seen.dt.to_period("M") < p.first_seen.max().to_period("M")]  # drop the partial current month
    p["mid"] = (p.salary_min + p.salary_max) / 2
    pt = (p.groupby(["company_name", "group", "month"]).mid.agg(["median", "count"]).reset_index()
          .rename(columns={"company_name": "company", "median": "median_mid", "count": "n"}))
    pt.to_csv(OUT / "pay_trend_monthly.csv", index=False)

    fig_footprint(fp)
    fig_expansion(ex)
    fig_pay(pt)
    sig = ex[ex.signal].sort_values("first_seen")
    print(f"{len(fp)} company-city points; {len(sig)} expansion signals")
    print(sig[["company", "city", "country", "first_seen", "postings_total", "open_now"]].to_string(index=False))
    print(pt[pt.n >= 8].pivot_table(index="month", columns=["company", "group"], values="median_mid").round(-3))


if __name__ == "__main__":
    main()
