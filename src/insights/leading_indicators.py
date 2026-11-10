"""Sprint 9: do job postings lead public events?

Usage:  python -m src.insights.leading_indicators

Signals  expansion signals (a city's first appearance in a company's postings, Sprint 5)
Events   curated, cited public events: office announcements/openings, funding, infrastructure
         (data/events/events.csv, every row with a source URL)

For each signal, the first public event for the same company and city is found:
    lead_days = event_date - signal_date   (> 0: hiring came first, i.e. postings were a leading indicator)
Signals without any matching public event (as of the analysis date) form the WATCHLIST: the project's
live, falsifiable predictions.

Also: hiring response around funding rounds (Anthropic open roles 13 weeks before vs. after).

Outputs: data/insights/lead_lag.csv, data/insights/watchlist.csv, data/insights/funding_response.csv
         reports/insights/figures/lead_lag.png, timeline.png
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.forecast.series import build  # noqa: E402
from src.style import COMPANY_COLOR, THEME, apply_matplotlib, footnote  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data" / "events" / "events.csv"
SIGNALS = ROOT / "data" / "trends" / "expansion_signals.csv"
OUT = ROOT / "data" / "insights"
FIG = ROOT / "reports" / "insights" / "figures"
ANALYSIS_DATE = pd.Timestamp("2026-11-10")
apply_matplotlib()


def lead_lag() -> tuple[pd.DataFrame, pd.DataFrame]:
    ev = pd.read_csv(EVENTS, parse_dates=["event_date"])
    sig = pd.read_csv(SIGNALS, parse_dates=["first_seen"])
    sig = sig[sig.signal]
    rows, watch = [], []
    presence = {"office_announcement", "office_opening", "infrastructure"}  # events that establish a location
    for s in sig.itertuples():
        same_city = ev[(ev.company == s.company) & (ev.city == s.city)]
        e = same_city[same_city.event_type.isin(presence)].sort_values("event_date")
        if e.empty:
            ctx = same_city.sort_values("event_date")
            watch.append({"company": s.company, "city": s.city, "country": s.country,
                          "first_seen": s.first_seen.date(), "postings_so_far": s.postings_total,
                          "open_now": s.open_now, "days_since_signal": (ANALYSIS_DATE - s.first_seen).days,
                          "context": "; ".join(f"{r.event_date.date()} {r.description}" for r in ctx.itertuples())})
            continue
        first = e.iloc[0]
        lead = (first.event_date - s.first_seen).days
        rows.append({"company": s.company, "city": s.city, "signal_date": s.first_seen.date(),
                     "first_event": first.event_type, "event_date": first.event_date.date(), "lead_days": lead,
                     "reading": "hiring led" if lead > 14 else ("simultaneous" if lead >= -14 else "hiring lagged"),
                     "event": first.description, "source": first.source_url})
    return pd.DataFrame(rows).sort_values("lead_days", ascending=False), pd.DataFrame(watch)


def funding_response() -> pd.DataFrame:
    ev = pd.read_csv(EVENTS, parse_dates=["event_date"])
    y = {s.id: s.y for s in build()}["anthropic_open"]
    rows = []
    for e in ev[ev.event_type == "funding"].itertuples():
        before = y[(y.index > e.event_date - pd.Timedelta(weeks=13)) & (y.index <= e.event_date)]
        after = y[(y.index > e.event_date) & (y.index <= e.event_date + pd.Timedelta(weeks=13))]
        after26 = y[(y.index > e.event_date) & (y.index <= e.event_date + pd.Timedelta(weeks=26))]
        rows.append({"company": e.company, "event": e.description, "date": e.event_date.date(),
                     "open_roles_at_event": round(float(before.iloc[-1])),
                     "change_13w_before": round(float(before.iloc[-1] - before.iloc[0])),
                     "change_13w_after": round(float(after.iloc[-1] - after.iloc[0])) if len(after) > 1 else None,
                     "change_26w_after": round(float(after26.iloc[-1] - after26.iloc[0])) if len(after26) > 1 else None})
    return pd.DataFrame(rows)


def fig_lead_lag(ll: pd.DataFrame, watch: pd.DataFrame) -> None:
    d = ll.iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 0.55 * (len(d) + len(watch)) + 1.8))
    y = 0
    labels = []
    for r in d.itertuples():
        col = COMPANY_COLOR[r.company]
        ax.barh(y, r.lead_days, color=col, height=0.55)
        ax.annotate(f"{r.lead_days:+d} d  ({r.reading})", (r.lead_days, y),
                    xytext=(6 if r.lead_days >= 0 else -6, 0), textcoords="offset points",
                    ha="left" if r.lead_days >= 0 else "right", va="center", fontsize=8.5, color=THEME["text"])
        labels.append(f"{r.company} · {r.city}  ({r.first_event.replace('_', ' ')})")
        y += 1
    for r in watch.sort_values("first_seen", ascending=False).itertuples():
        ax.scatter([0], [y], marker=">", s=80, color=COMPANY_COLOR[r.company])
        ax.annotate(f"no public event yet ({r.days_since_signal} d since first posting)", (0, y),
                    xytext=(10, 0), textcoords="offset points", va="center", fontsize=8.5, color=THEME["text2"])
        labels.append(f"{r.company} · {r.city}  (watchlist)")
        y += 1
    ax.set_yticks(range(len(labels)), labels)
    ax.axvline(0, color=THEME["muted"], linewidth=1)
    ax.set_xlabel("days from first job posting in the city to the first public event   (positive = hiring came first)")
    ax.grid(axis="y", visible=False)
    lo = min(ll.lead_days.min(), 0)
    ax.set_xlim(lo - 60, max(ll.lead_days.max(), 0) + 330)
    ax.set_title("Do job postings lead public announcements? New-city hiring vs office news")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, "Signals: first appearance of a city in postings (Epoch AI + snapshots) · events: cited news & "
                  "company announcements (data/events/events.csv)")
    fig.savefig(FIG / "lead_lag.png")
    plt.close(fig)


def fig_timeline(ll: pd.DataFrame) -> None:
    series = {s.id: s.y for s in build()}
    ev = pd.read_csv(EVENTS, parse_dates=["event_date"])
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.4), sharex=True)
    for ax, (company, sid) in zip(axes, [("Anthropic", "anthropic_open"), ("OpenAI", "openai_open")]):
        y = series[sid]
        y = y[y.index >= pd.Timestamp("2025-11-01")]
        col = COMPANY_COLOR[company]
        ax.plot(y.index, y.values, color=col, linewidth=2.4)
        top = y.max() * 1.18
        evs = ev[(ev.company == company) & (ev.event_date >= y.index.min())]
        for d, grp in evs.groupby("event_date"):  # one label per date so same-day events don't collide
            label = " · ".join(f"{ {'funding': '$', 'office_opening': 'O', 'office_announcement': 'A', 'event': 'E', 'infrastructure': 'I'}[e.event_type]} "
                               f"{e.city if isinstance(e.city, str) else 'funding'}" for e in grp.itertuples())
            ax.axvline(d, color=THEME["axis"], linewidth=1, linestyle=":")
            ax.annotate(label, (d, top), rotation=90, va="top", ha="right", fontsize=8, color=THEME["text2"])
        last_x, k = None, 0
        for s in ll[ll.company == company].sort_values("signal_date").itertuples():
            sd = pd.Timestamp(s.signal_date)
            if sd < y.index.min():
                continue
            k = k + 1 if last_x is not None and (sd - last_x).days < 50 else 0  # stagger nearby labels
            last_x = sd
            yy = float(y.asof(sd))
            ax.scatter([sd], [yy], marker="*", s=160, color=col, edgecolor=THEME["text"], linewidth=0.6, zorder=4)
            ax.annotate(f"first {s.city} posting", (sd, yy), xytext=(6, -16 - 13 * k), textcoords="offset points",
                        fontsize=7.5, color=THEME["text"])
        ax.set_title(f"{company}: open roles, first postings in new cities (stars) and public events (A = announced, "
                     "O = opened, $ = funding, E = event)", fontsize=10.5)
        ax.set_ylim(0, top * 1.02)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    footnote(fig, "Open roles: Epoch AI + Internet Archive · events: data/events/events.csv (cited)")
    fig.savefig(FIG / "timeline.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    ll, watch = lead_lag()
    fr = funding_response()
    ll.to_csv(OUT / "lead_lag.csv", index=False)
    watch.to_csv(OUT / "watchlist.csv", index=False)
    fr.to_csv(OUT / "funding_response.csv", index=False)
    fig_lead_lag(ll, watch)
    fig_timeline(ll)
    print(ll[["company", "city", "signal_date", "first_event", "event_date", "lead_days", "reading"]].to_string(index=False))
    print("\nWATCHLIST\n", watch.to_string(index=False))
    print("\nFUNDING\n", fr.to_string(index=False))
    print(f"\nanalysis date {date(2026, 11, 10)}")


if __name__ == "__main__":
    main()
