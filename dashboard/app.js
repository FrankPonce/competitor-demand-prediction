/* AI Hiring Signals · dashboard logic. Reads data/*.json exported by src.dashboard.export. */
(() => {
  "use strict";

  const FOCUS = ["Anthropic", "OpenAI", "NVIDIA", "Google"];
  const C = { surface: "#0d1117", panel: "#161b22", panel2: "#1b222c", grid: "#21262d", axis: "#30363d",
    text: "#e6edf3", text2: "#9198a1", muted: "#6e7681", accent: "#58a6ff", warn: "#e3b341" };
  const charts = [];
  let D = {};

  // ---------- helpers ----------
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const nf = new Intl.NumberFormat("en-US");
  const fmt = (v, d = 0) => (v == null || Number.isNaN(v) ? "–" : nf.format(+(+v).toFixed(d)));
  const pct = (v, sign = true) => { if (v == null) return "–"; const r = Math.round(v * 100) || 0; return `${sign && r > 0 ? "+" : ""}${r}%`; };
  const dir = (v) => (v == null ? "flat" : v > 0.02 ? "up" : v < -0.02 ? "down" : "flat");
  const money = (v) => (v == null ? "–" : v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : `$${Math.round(v / 1000)}k`);
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const day = (s) => { const [y, m, d] = s.split("-"); return `${MON[+m - 1]} ${+d}`; };
  const dateLong = (s) => { const [y, m, d] = s.split("-"); return `${+d} ${MON[+m - 1]} ${y}`; };
  const color = (co) => (D.companies[co] && D.companies[co].color) || C.text2;
  const logoUrl = (co) => (D.companies[co] ? D.companies[co].logo : null);
  const logo = (co, size = 16, c) => {
    const u = logoUrl(co);
    if (!u) return `<span class="swatch" style="--c:${c || color(co)}"></span>`;
    return `<span class="logo" style="--u:url(${u});--c:${c || color(co)};--s:${size}px" aria-hidden="true"></span>`;
  };
  const alpha = (hex, a) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
  };
  const get = (p) => fetch(p, { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(p); return r.json(); });

  // ---------- echarts base ----------
  const tooltip = (extra = {}) => ({
    trigger: "axis", backgroundColor: "rgba(22,27,34,.96)", borderColor: C.axis, borderWidth: 1,
    textStyle: { color: C.text, fontSize: 12, fontFamily: "Inter, system-ui, sans-serif" },
    axisPointer: { type: "line", lineStyle: { color: C.axis } }, confine: true, ...extra,
  });
  const axisCommon = {
    axisLine: { lineStyle: { color: C.axis } }, axisTick: { show: false },
    axisLabel: { color: C.muted, fontSize: 11, fontFamily: "JetBrains Mono, monospace" },
    splitLine: { lineStyle: { color: C.grid } },
  };
  const xTime = (o = {}) => ({ type: "time", ...axisCommon, splitLine: { show: false }, ...o });
  const yVal = (o = {}) => ({ type: "value", scale: true, ...axisCommon, ...o });
  // Charts are created only once their box has a real width (a 0-px force layout breaks ECharts),
  // and resized whenever the box changes.
  const ro = "ResizeObserver" in window ? new ResizeObserver((es) => es.forEach((e) => {
    const el = e.target;
    if (!el.clientWidth) return;
    if (el._pending) { const o = el._pending; el._pending = null; init(el, o); }
    else { const ch = echarts.getInstanceByDom(el); if (ch) ch.resize(); }
  })) : null;
  function init(el, option) {
    const ch = echarts.init(el, null, { renderer: "canvas" });
    charts.push(ch);
    try {
      ch.setOption({ backgroundColor: "transparent", textStyle: { fontFamily: "Inter, system-ui, sans-serif" },
        animationDuration: 700, ...option });
    } catch (err) { console.error(`chart #${el.id}`, err); }
  }
  function mount(el, option) {
    if (!el || !window.echarts) return;
    if (ro) ro.observe(el);
    if (el.clientWidth) init(el, option); else el._pending = option;
  }
  const disposeIn = (root) => {
    root.querySelectorAll(".chart").forEach((el) => {
      const ch = echarts.getInstanceByDom(el);
      if (ch) { charts.splice(charts.indexOf(ch), 1); ch.dispose(); }
      if (ro) ro.unobserve(el);
    });
  };

  // series + forecast band for one company
  function trajectorySeries(co, history, forecast, opts = {}) {
    const c = color(co);
    const last = history[history.length - 1];
    const fc = forecast || [];
    const bandLo = last ? [[last[0], last[1]], ...fc.map((r) => [r[0], r[2]])] : [];
    const bandW = last ? [[last[0], 0], ...fc.map((r) => [r[0], r[3] - r[2]])] : [];
    const stack = `band-${co}`;
    return [
      { name: "Actual", type: "line", data: history, showSymbol: false, smooth: 0.25,
        lineStyle: { width: 2, color: c }, itemStyle: { color: c },
        areaStyle: opts.area === false ? undefined : { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: alpha(c, 0.22) }, { offset: 1, color: alpha(c, 0) }] } } },
      { name: "lo", type: "line", data: bandLo, stack, showSymbol: false, lineStyle: { opacity: 0 }, tooltip: { show: false }, silent: true },
      { name: "80% interval", type: "line", data: bandW, stack, showSymbol: false, lineStyle: { opacity: 0 },
        areaStyle: { color: alpha(c, 0.18) }, tooltip: { show: false }, silent: true },
      { name: "Forecast", type: "line", data: last ? [[last[0], last[1]], ...fc.map((r) => [r[0], r[1]])] : [],
        showSymbol: false, lineStyle: { width: 2, type: [4, 4], color: c }, itemStyle: { color: c } },
    ];
  }
  const trajTooltip = (unit) => tooltip({
    formatter: (ps) => {
      const p = ps.filter((x) => x.seriesName === "Actual" || x.seriesName === "Forecast" || x.seriesName === "Model releases");
      if (!p.length) return "";
      const head = `<div style="color:${C.muted};font:11px JetBrains Mono,monospace">${dateLong(new Date(p[0].value[0]).toISOString().slice(0, 10))}</div>`;
      return head + p.map((x) => x.seriesName === "Model releases"
        ? `<div>◆ ${esc(x.value[2])}</div>`
        : `<div>${x.marker}${x.seriesName}: <b>${fmt(x.value[1], x.value[1] < 100 ? 1 : 0)}</b> <span style="color:${C.muted}">${unit}</span></div>`).join("");
    },
  });

  // ---------- status + hero ----------
  function renderStatus() {
    const m = D.meta;
    const st = $("#status-text");
    st.textContent = `Updated ${dateLong(m.generated_at.slice(0, 10))} · next ${m.next_refresh.replace(" (GitHub Actions)", "")}`;
    st.title = `Data generated ${m.generated_at}; last job-board snapshot ${m.last_snapshot}; refreshed ${m.next_refresh}`;
    const newCities = D.globe.arcs.length;
    const items = [
      [fmt(m.open_postings_now), "open postings tracked"],
      [m.companies_tracked, "companies"],
      [newCities, "new cities in 2026"],
      [fmt(D.tracker.targets), "forecasts scored"],
    ];
    $("#counters").innerHTML = items.map(([v, k]) => `<div class="counter"><div class="v num">${v}</div><div class="k">${k}</div></div>`).join("");
    $("#sources").innerHTML = m.sources.map((s) => `<li>${esc(s)}</li>`).join("");
  }

  // ---------- globe ----------
  const globeOn = new Set(FOCUS);
  let globe = null;
  function renderLegend() {
    const el = $("#legend");
    el.innerHTML = FOCUS.map((co) => `<button type="button" class="chip on" aria-pressed="true" data-co="${co}" style="--c:${color(co)}">${logo(co, 14)}${co}</button>`).join("");
    el.addEventListener("click", (e) => {
      const b = e.target.closest(".chip"); if (!b) return;
      const co = b.dataset.co;
      if (globeOn.has(co) && globeOn.size > 1) globeOn.delete(co); else globeOn.add(co);
      el.querySelectorAll(".chip").forEach((x) => {
        const on = globeOn.has(x.dataset.co);
        x.classList.toggle("on", on); x.classList.toggle("off", !on); x.setAttribute("aria-pressed", on);
      });
      updateGlobe();
    });
  }

  const arcStatus = { "hiring led": ["b-led", "hiring led"], "hiring lagged": ["b-lagged", "hiring lagged"],
    simultaneous: ["b-simultaneous", "simultaneous"], watch: ["b-watch", "watch"] };

  function globeData() {
    const pts = D.globe.points.filter((p) => globeOn.has(p.company));
    const arcs = D.globe.arcs.filter((a) => globeOn.has(a.company));
    return { pts, arcs, rings: arcs.filter((a) => a.status === "watch") };
  }
  function tipHtml(d) {
    if (d.start) {
      const ll = D.tracker.lead_lag.find((x) => x.company === d.company && x.city === d.city);
      const [cls, lbl] = arcStatus[d.status] || ["b-context", d.status];
      const extra = ll ? `${ll.lead_days > 0 ? "+" : ""}${ll.lead_days} days vs announcement` : "No announcement yet";
      return `<div class="tip"><div class="t">${logo(d.company, 13)}${esc(d.company)} → ${esc(d.city)}</div>
        <div class="d">First posting ${dateLong(d.date)} · ${extra}</div><div style="margin-top:6px"><span class="badge ${cls}">${lbl}</span></div></div>`;
    }
    return `<div class="tip"><div class="t">${logo(d.company, 13)}${esc(d.city)}</div>
      <div class="d">${esc(d.company)} · ${fmt(d.postings)} posting${d.postings === 1 ? "" : "s"}</div></div>`;
  }
  function updateGlobe() {
    if (!globe) return;
    const { pts, arcs, rings } = globeData();
    globe.pointsData(pts).arcsData(arcs).ringsData(rings).labelsData(arcs);
  }
  function renderGlobe() {
    const el = $("#globe");
    if (!window.Globe || !el) return;
    const coarse = matchMedia("(pointer: coarse)").matches;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const maxP = Math.max(...D.globe.points.map((p) => p.postings));
    globe = Globe({ animateIn: !reduce })(el)
      .backgroundColor("rgba(0,0,0,0)")
      .showAtmosphere(true).atmosphereColor("#3b82c4").atmosphereAltitude(0.16)
      .hexPolygonsData(D.land.features).hexPolygonResolution(3).hexPolygonMargin(0.42)
      .hexPolygonUseDots(true).hexPolygonColor(() => "#3a4350")
      .pointLat("lat").pointLng("lon").pointColor((d) => color(d.company))
      .pointAltitude((d) => 0.005 + 0.07 * Math.log1p(d.postings) / Math.log1p(maxP))
      .pointRadius((d) => 0.18 + 0.45 * Math.sqrt(d.postings / maxP))
      .pointLabel((d) => tipHtml(d))
      .arcStartLat((d) => d.start[0]).arcStartLng((d) => d.start[1])
      .arcEndLat((d) => d.end[0]).arcEndLng((d) => d.end[1])
      .arcColor((d) => [alpha(color(d.company), 0.15), color(d.company)])
      .arcStroke(0.55).arcAltitudeAutoScale(0.42)
      .arcDashLength(0.45).arcDashGap(0.18).arcDashInitialGap(() => Math.random())
      .arcDashAnimateTime(reduce ? 0 : 2600)
      .arcLabel((d) => tipHtml(d))
      .ringLat((d) => d.end[0]).ringLng((d) => d.end[1])
      .ringColor(() => (t) => `rgba(227,179,65,${(1 - t) * 0.9})`)
      .ringMaxRadius(3.6).ringPropagationSpeed(1.6).ringRepeatPeriod(reduce ? 0 : 1300)
      .labelLat((d) => d.end[0]).labelLng((d) => d.end[1]).labelText((d) => d.city)
      .labelColor((d) => alpha(color(d.company), 0.95)).labelSize(0.9).labelDotRadius(0.32)
      .labelAltitude(0.006).labelResolution(2).labelIncludeDot(true)
      .labelLabel((d) => tipHtml(d))
      .onPointClick(showTip).onArcClick(showTip).onLabelClick(showTip)
      .onGlobeClick(() => { $("#globe-tip").hidden = true; });
    const mat = globe.globeMaterial();
    mat.color.set("#0b1119"); mat.emissive && mat.emissive.set("#070b11"); mat.shininess = 6;
    const ctr = globe.controls();
    ctr.autoRotate = !reduce; ctr.autoRotateSpeed = 0.45; ctr.enableZoom = false; ctr.enablePan = false;
    if (coarse) ctr.enableRotate = false; // keep page scroll on touch screens
    globe.pointOfView({ lat: 30, lng: -45, altitude: 1.75 }, 0);
    const size = () => globe.width(el.clientWidth).height(el.clientHeight);
    size(); new ResizeObserver(size).observe(el);
    // pause rotation while the hero is off-screen (saves battery)
    new IntersectionObserver(([e]) => { e.isIntersecting ? globe.resumeAnimation() : globe.pauseAnimation(); }).observe(el);
    updateGlobe();
  }
  function showTip(d) {
    const t = $("#globe-tip"); t.innerHTML = tipHtml(d); t.hidden = false;
    if (d.end) globe.pointOfView({ lat: d.end[0], lng: d.end[1], altitude: 2 }, 900);
    else globe.pointOfView({ lat: d.lat, lng: d.lon, altitude: 2 }, 900);
  }

  function renderExpansions() {
    const arcs = [...D.globe.arcs].sort((a, b) => b.date.localeCompare(a.date));
    $("#expansions").innerHTML = arcs.map((a) => {
      const ll = D.tracker.lead_lag.find((x) => x.company === a.company && x.city === a.city);
      const wl = D.tracker.watchlist.find((x) => x.company === a.company && x.city === a.city);
      const [cls, lbl] = arcStatus[a.status] || ["b-context", a.status];
      const meta = ll ? `${day(a.date)} · ${ll.lead_days > 0 ? "+" : ""}${ll.lead_days} d vs news`
        : wl ? `${day(a.date)} · ${wl.days_since_signal} d, no news` : day(a.date);
      return `<li class="exp" data-co="${a.company}">${logo(a.company, 18)}<div><div class="city">${esc(a.city)}</div><div class="meta">${meta}</div></div><span class="badge ${cls}">${lbl}</span></li>`;
    }).join("");
  }

  // ---------- feed ----------
  const TYPES = { signals: ["new_city", "surge", "emerging_term", "model_release", "filing"], hiring: ["new_city", "surge", "emerging_term"], models: ["model_release"], filings: ["filing"], news: ["news"] };
  const TYPE_LBL = { new_city: "new city", surge: "surge", emerging_term: "emerging term", model_release: "model", filing: "filing", news: "news" };
  const feedState = { co: "all", type: "signals", n: 12 };
  function feedItems() {
    const seen = new Set(D.signals.map((s) => s.url).filter(Boolean));
    const news = D.news.filter((n) => !seen.has(n.url)).map((n) => ({
      date: n.date, company: n.company, type: "news", confidence: "context", title: n.title,
      detail: [n.source, n.topics && n.topics.split(";").join(" · ")].filter(Boolean).join(" · "), url: n.url }));
    const all = [...D.signals, ...news].sort((a, b) => b.date.localeCompare(a.date));
    return all.filter((s) => (feedState.co === "all" || s.company.includes(feedState.co))
      && (feedState.type === "all" || TYPES[feedState.type].includes(s.type)));
  }
  function renderFilters() {
    const co = [["all", "All companies"], ...FOCUS.map((c) => [c, c])];
    const ty = [["signals", "Signals"], ["hiring", "Hiring"], ["models", "Model releases"], ["filings", "Filings"], ["news", "Newsroom"], ["all", "Everything"]];
    const chip = (g, [v, l]) => `<button type="button" class="chip ${feedState[g] === v ? "on" : ""}" data-g="${g}" data-v="${v}" aria-pressed="${feedState[g] === v}" ${FOCUS.includes(v) ? `style="--c:${color(v)}"` : ""}>${FOCUS.includes(v) ? logo(v, 13) : ""}${l}</button>`;
    $("#filters").innerHTML = co.map((x) => chip("co", x)).join("") + `<span class="sep" aria-hidden="true"></span>` + ty.map((x) => chip("type", x)).join("");
  }
  function renderFeed() {
    const items = feedItems();
    const shown = items.slice(0, feedState.n);
    $("#feed").innerHTML = shown.length ? shown.map((s) => {
      const first = FOCUS.find((c) => s.company.includes(c)) || s.company;
      const conf = s.confidence || "context";
      const title = s.url ? `<a class="title" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>` : `<span class="title">${esc(s.title)}</span>`;
      return `<li class="item" style="--c:${color(first)}"><span class="date">${dateLong(s.date)}</span>
        <span class="ico">${logo(first, 15)}</span>
        <div>${title}<div class="detail">${s.type === "news" ? "" : `${esc(s.company)} · `}${esc(s.detail || "")}</div></div>
        <span class="tags"><span class="type">${TYPE_LBL[s.type] || s.type}</span><span class="badge b-${conf}">${conf}</span></span></li>`;
    }).join("") : `<li class="empty">No signals for this filter yet.</li>`;
    const more = $("#feed-more");
    more.hidden = items.length <= feedState.n;
    more.textContent = `Show more (${items.length - shown.length})`;
  }
  function wireFeed() {
    $("#filters").addEventListener("click", (e) => {
      const b = e.target.closest(".chip"); if (!b) return;
      feedState[b.dataset.g] = b.dataset.v; feedState.n = 12; renderFilters(); renderFeed();
    });
    $("#feed-more").addEventListener("click", () => { feedState.n += 12; renderFeed(); });
  }

  // ---------- pulse ----------
  let pulseRange = 52;
  function sliceHistory(h, weeks) {
    if (!weeks || !h.length) return h;
    const end = new Date(h[h.length - 1][0]); end.setDate(end.getDate() - weeks * 7);
    const cut = end.toISOString().slice(0, 10);
    return h.filter((r) => r[0] >= cut);
  }
  function renderPulse() {
    const grid = $("#pulse-grid");
    disposeIn(grid);
    grid.innerHTML = FOCUS.map((co) => {
      const d = D.companies[co], k = d.kpi;
      const isRate = d.unit !== "open roles";
      const last = d.history[d.history.length - 1];
      const kpis = [
        [pct(k.momentum_6m), "6-month momentum", dir(k.momentum_6m)],
        [pct(k.outlook_8w), "8-week outlook", dir(k.outlook_8w)],
        [k.pay_mid ? money(k.pay_mid) : "–", "median pay midpoint", ""],
        [pct(k.tech_share, false), "technical roles", ""],
      ];
      return `<article class="panel kpi-card" style="--c:${d.color}">
        <div class="kpi-top">${logo(co, 26)}<div><div class="name">${co}</div><div class="tag">${esc(d.segment)}</div></div>
          <div class="big"><div class="v num">${fmt(last[1], isRate ? 1 : 0)}</div><div class="k">${isRate ? "new reqs / day" : "open roles"} · ${day(last[0])}</div></div></div>
        <div class="kpis">${kpis.map(([v, l, c]) => `<div class="kpi"><div class="v num ${c}">${v}</div><div class="k">${l}</div></div>`).join("")}</div>
        <div class="chart" id="pulse-${co}" style="height:200px"></div>
        <p class="sub" style="margin-top:2px;font-size:12px">${esc(d.series_label)} · forecast model: <span class="mono">${esc(k.model)}</span> · 8-wk point ${fmt(k.outlook_point, isRate ? 1 : 0)} (${fmt(k.outlook_lo, isRate ? 1 : 0)}–${fmt(k.outlook_hi, isRate ? 1 : 0)})</p>
      </article>`;
    }).join("");
    FOCUS.forEach((co) => {
      const d = D.companies[co];
      mount($(`#pulse-${co}`), {
        grid: { left: 44, right: 12, top: 10, bottom: 24 },
        tooltip: trajTooltip(d.unit),
        xAxis: xTime({ axisLabel: { ...axisCommon.axisLabel, hideOverlap: true } }),
        yAxis: yVal({ splitNumber: 3 }),
        series: trajectorySeries(co, sliceHistory(d.history, pulseRange), d.forecast),
      });
    });
    reveal(grid);
  }
  function wireRange() {
    $("#range").addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      pulseRange = +b.dataset.r;
      $("#range").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
      renderPulse();
    });
  }

  // ---------- deep dive ----------
  let active = FOCUS[0];
  function bars(rows, c, valFmt, max) {
    const m = max || Math.max(...rows.map((r) => r[1]), 1e-9);
    return `<ul class="bars">${rows.map((r) => `<li class="bar-row" style="--c:${c}"><span class="lbl" title="${esc(r[0])}">${esc(r[0])}</span><span class="val">${valFmt(r)}</span><span class="track"><span class="fill" style="width:${Math.max(2, (r[1] / m) * 100)}%"></span></span></li>`).join("")}</ul>`;
  }
  function renderTabs() {
    const el = $("#tabs");
    el.innerHTML = FOCUS.map((co) => `<button type="button" class="tab" role="tab" id="tab-${co}" aria-controls="deep" aria-selected="${co === active}" tabindex="${co === active ? 0 : -1}" data-co="${co}" style="--c:${color(co)}">${logo(co, 16)}${co}</button>`).join("");
    el.onclick = (e) => { const b = e.target.closest(".tab"); if (b) selectTab(b.dataset.co); };
    el.onkeydown = (e) => {
      if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
      const i = (FOCUS.indexOf(active) + (e.key === "ArrowRight" ? 1 : FOCUS.length - 1)) % FOCUS.length;
      selectTab(FOCUS[i]); $(`#tab-${FOCUS[i]}`).focus();
    };
  }
  function selectTab(co) {
    active = co;
    $("#tabs").querySelectorAll(".tab").forEach((b) => { const on = b.dataset.co === co; b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; });
    renderDeep();
  }
  function renderDeep() {
    const co = active, d = D.companies[co], c = d.color, k = d.kpi;
    const root = $("#deep");
    root.setAttribute("aria-labelledby", `tab-${co}`); root.setAttribute("role", "tabpanel");
    disposeIn(root);
    const fin = D.context.financials[co];
    const models = D.context.models.filter((m) => m.company === co).sort((a, b) => b.date.localeCompare(a.date));
    const hasFn = d.functions && Object.keys(d.functions).length;
    const isRate = d.unit !== "open roles";
    root.innerHTML = `
      <div class="panel span-6 deep-hero">${logo(co, 44)}<div><div class="seg-label">${esc(d.segment)} · ${fmt(k.open_postings)} open postings · ${k.min_years != null ? `median ${fmt(k.min_years)} yrs experience asked` : ""}${k.phd ? ` · PhD in ${pct(k.phd, false)}` : ""}</div><div class="tagline">${esc(d.tagline)}</div></div></div>
      <div class="panel span-4"><div class="panel-head"><h3>Trajectory and 8-week forecast</h3><p class="sub">${esc(d.series_label)}${models.length ? " · ◆ model releases (Epoch AI)" : ""}</p></div><div class="chart" id="deep-traj" style="height:300px"></div></div>
      <div class="panel span-2"><div class="panel-head"><h3>Role mix</h3><p class="sub">Share of open postings</p></div>${bars(d.role_mix, c, (r) => pct(r[1], false))}</div>
      ${hasFn ? `<div class="panel span-3"><div class="panel-head"><h3>Functions over time</h3><p class="sub">Open roles by function, 3-snapshot rolling mean</p></div><div class="chart" id="deep-fn" style="height:300px"></div></div>` : ""}
      ${fin ? `<div class="panel span-3"><div class="panel-head"><h3>Hiring vs business reality</h3><p class="sub">Fiscal-quarter revenue and R&amp;D from SEC 10-Q/10-K filings (bars) vs average hiring in the same quarter (line)</p></div><div class="chart" id="deep-fin" style="height:300px"></div></div>` : ""}
      <div class="panel span-3"><div class="panel-head"><h3>Distinctive skills</h3><p class="sub">Share of ${co} postings · lift vs the other three</p></div>${bars(d.skills.map((s) => [s[0], s[1], s[3]]), c, (r) => `${r[2].toFixed(1)}×`)}</div>
      <div class="panel span-2"><div class="panel-head"><h3>Hiring hubs</h3><p class="sub">Share of located postings</p></div>${bars(d.hubs, c, (r) => pct(r[1], false))}</div>
      <div class="panel span-2"><div class="panel-head"><h3>Nearest peers</h3><p class="sub">Hiring similarity (0–1)</p></div>${bars(d.peers, c, (r) => r[1].toFixed(2), 1)}</div>
      <div class="panel span-2"><div class="panel-head"><h3>Model releases</h3><p class="sub">${models.length ? `${models.length} notable models since 2022` : "None in Epoch AI's notable-models list"}</p></div>
        <ul class="models">${models.slice(0, 12).map((m) => `<li><span class="mono">${m.date}</span><span>${esc(m.model)}</span></li>`).join("") || `<li class="sub">–</li>`}</ul></div>
      <p class="sub span-6" style="margin:0;font-size:12px;max-width:none">Patent publications (EPO Open Patent Services, all four companies): ${esc(D.context.patents_status || "loaded")} · this company: ${fmt(D.context.patents.filter((p) => p.company === co).reduce((a, p) => a + p.publications, 0))} · California WARN layoff notices: ${D.context.warn.filter((w) => w.company === co).length || "none filed"}</p>`;

    // trajectory + model markers
    const hist = d.history;
    const ymin = Math.min(...hist.map((r) => r[1]));
    const t0 = hist[0][0];
    const mk = models.filter((m) => m.date >= t0).map((m) => [m.date, ymin, m.model]);
    mount($("#deep-traj"), {
      grid: { left: 48, right: 14, top: 12, bottom: 28 },
      tooltip: trajTooltip(d.unit), xAxis: xTime(), yAxis: yVal(),
      series: [...trajectorySeries(co, hist, d.forecast),
        { name: "Model releases", type: "scatter", data: mk, symbol: "diamond", symbolSize: 9,
          itemStyle: { color: C.text, borderColor: c, borderWidth: 1.5 }, z: 5 }],
    });
    if (hasFn) {
      const fc = { "Go-to-market": "#e3b341", Research: c, Product: "#79c0ff", Compute: "#7ee2a8", Corporate: C.muted };
      mount($("#deep-fn"), {
        grid: { left: 44, right: 12, top: 34, bottom: 26 },
        legend: { top: 0, textStyle: { color: C.text2, fontSize: 11 }, itemWidth: 10, itemHeight: 10, icon: "roundRect" },
        tooltip: tooltip({ valueFormatter: (v) => fmt(v) }), xAxis: xTime(), yAxis: yVal({ scale: false }),
        series: Object.entries(d.functions).map(([name, rows]) => ({ name, type: "line", stack: "fn", data: rows, showSymbol: false,
          smooth: 0.3, lineStyle: { width: 1, color: fc[name] }, itemStyle: { color: fc[name] }, areaStyle: { color: alpha(fc[name] || C.muted, 0.35) } })),
      });
    }
    if (fin) {
      // Fiscal quarters on a category axis; hiring averaged over the weeks inside each quarter.
      const rev = (fin.revenue || []).filter((r) => r[0] >= "2024-01-01");
      const rnd = new Map((fin.rnd_expense || []).map((r) => [r[0], r[1]]));
      const ends = rev.map((r) => r[0]);
      const lastHist = hist[hist.length - 1][0];
      if (lastHist > ends[ends.length - 1]) ends.push(lastHist); // quarter in progress: hiring only
      const avg = (from, to) => { const v = hist.filter((r) => r[0] > from && r[0] <= to).map((r) => r[1]); return v.length ? +(v.reduce((a, b) => a + b, 0) / v.length).toFixed(1) : null; };
      const hireQ = ends.map((e, i) => avg(i ? ends[i - 1] : "0000", e));
      const lbl = (s, i) => (i === rev.length ? "QTD" : `${MON[+s.slice(5, 7) - 1]} ’${s.slice(2, 4)}`);
      const B = (v) => (v == null ? null : +(v / 1e9).toFixed(2));
      mount($("#deep-fin"), {
        grid: { left: 50, right: 40, top: 34, bottom: 26 },
        legend: { top: 0, textStyle: { color: C.text2, fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
        tooltip: tooltip({ axisPointer: { type: "shadow" }, formatter: (ps) => `<div style="color:${C.muted};font:11px JetBrains Mono,monospace">quarter ending ${ends[ps[0].dataIndex]}</div>` +
          ps.filter((p) => p.value != null).map((p) => `<div>${p.marker}${p.seriesName}: <b>${p.seriesName.startsWith("Hiring") ? fmt(p.value, 1) : `$${p.value}B`}</b></div>`).join("") }),
        xAxis: { type: "category", data: ends.map(lbl), ...axisCommon, splitLine: { show: false }, axisLabel: { ...axisCommon.axisLabel, hideOverlap: true } },
        yAxis: [yVal({ scale: false, axisLabel: { ...axisCommon.axisLabel, formatter: "${value}B" } }),
          yVal({ scale: false, splitLine: { show: false } })],
        series: [
          { name: "Revenue", type: "bar", data: [...rev.map((r) => B(r[1])), null].slice(0, ends.length), barMaxWidth: 14, barGap: "10%", itemStyle: { color: alpha(c, 0.9), borderRadius: [3, 3, 0, 0] } },
          { name: "R&D", type: "bar", data: [...rev.map((r) => B(rnd.get(r[0]))), null].slice(0, ends.length), barMaxWidth: 14, itemStyle: { color: alpha(c, 0.4), borderRadius: [3, 3, 0, 0] } },
          { name: `Hiring (${isRate ? "reqs/day" : "open roles"}, qtr avg)`, type: "line", yAxisIndex: 1, data: hireQ, connectNulls: false,
            symbol: "circle", symbolSize: 6, lineStyle: { color: C.text, width: 1.5 }, itemStyle: { color: C.text } },
        ],
      });
    }
    reveal(root);
  }

  // ---------- tracker ----------
  function renderTracker() {
    const t = D.tracker;
    const cov = t.coverage80 == null ? "coverage appears once the first target weeks resolve" : `80% interval coverage so far: <b>${pct(t.coverage80, false)}</b> (target 80%)`;
    $("#tracker-sub").innerHTML = `Frozen on <b>${dateLong(t.frozen_on)}</b> and never edited: ${fmt(t.targets)} targets across 16 series, <b>${t.resolved}</b> resolved so far · ${cov}.`;
    const scored = new Map(t.scored.map((s) => [`${s.series}|${String(s.target_week).slice(0, 10)}`, s]));
    const rows = [...t.forecasts].sort((a, b) => FOCUS.indexOf(a.company) - FOCUS.indexOf(b.company) || a.h - b.h);
    const dp = (r) => (r.point < 100 ? 1 : 0);
    $("#forecast-table").innerHTML = `<thead><tr><th>Series</th><th>Week</th><th>Forecast</th><th>80% range</th><th>Actual</th></tr></thead><tbody>` +
      rows.map((r) => {
        const s = scored.get(`${r.series}|${r.target_week}`);
        const act = s ? `<span class="${s.in_80 ? "up" : "down"}">${fmt(s.actual, dp(r))} ${s.in_80 ? "✓" : "✗"}</span>` : `<span class="pending">pending</span>`;
        return `<tr><td class="name">${logo(r.company, 13)}<span>${esc(r.company)}${r.h === 1 ? "" : ""}</span></td><td>${day(r.target_week)}</td><td>${fmt(r.point, dp(r))}</td><td>${fmt(r.lo, dp(r))}–${fmt(r.hi, dp(r))}</td><td>${act}</td></tr>`;
      }).join("") + "</tbody>";

    const ll = [...t.lead_lag].sort((a, b) => a.lead_days - b.lead_days);
    mount($("#leadlag"), {
      grid: { left: 118, right: 46, top: 8, bottom: 26 },
      tooltip: { trigger: "item", backgroundColor: "rgba(22,27,34,.96)", borderColor: C.axis, textStyle: { color: C.text, fontSize: 12 }, confine: true,
        formatter: (p) => { const r = ll[p.dataIndex]; return `<b>${esc(r.company)} · ${esc(r.city)}</b><br>${esc(r.event)}<br><span style="color:${C.muted}">posting ${r.signal_date} · news ${r.event_date}</span><br><b>${r.lead_days > 0 ? "+" : ""}${r.lead_days} days</b> (${esc(r.reading)})`; } },
      xAxis: yVal({ scale: false, splitNumber: 3, axisLabel: { ...axisCommon.axisLabel, formatter: "{value} d", hideOverlap: true } }),
      yAxis: { type: "category", data: ll.map((r) => `${r.city}`), ...axisCommon, splitLine: { show: false }, axisLabel: { color: C.text2, fontSize: 12 } },
      series: [{ type: "bar", barWidth: 14, data: ll.map((r) => ({ value: r.lead_days, itemStyle: { color: color(r.company), borderRadius: 3 } })),
        label: { show: true, position: "right", color: C.text2, fontFamily: "JetBrains Mono, monospace", fontSize: 11, formatter: (p) => (p.value > 0 ? `+${p.value}` : `${p.value}`) },
        markLine: { silent: true, symbol: "none", lineStyle: { color: C.axis }, label: { show: false }, data: [{ xAxis: 0 }] } }],
    });

    $("#watchlist").innerHTML = t.watchlist.map((w) => `<li>${logo(w.company, 18)}<div><div class="city">${esc(w.city)} <span class="badge b-watch">watch</span></div><div class="meta">${esc(w.company)} · first seen ${dateLong(w.first_seen)} · ${w.postings_so_far} postings, ${w.open_now} open</div></div><div class="days">${w.days_since_signal}<small>days, no news</small></div></li>`).join("");

    const f = t.funding;
    mount($("#funding"), {
      grid: { left: 44, right: 12, top: 34, bottom: 46 },
      legend: { top: 0, textStyle: { color: C.text2, fontSize: 11 }, itemWidth: 10, itemHeight: 10,
        data: [["13 weeks before", 0.35], ["13 weeks after", 0.7], ["26 weeks after", 1]].map(([name, a]) => ({ name, itemStyle: { color: alpha(C.text, a * 0.8) } })) },
      tooltip: tooltip({ trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => `${v > 0 ? "+" : ""}${v} roles` }),
      xAxis: { type: "category", data: f.map((r) => `${r.event.split(":")[0]}\n${day(r.date)} ${r.date.slice(0, 4)}`), ...axisCommon, splitLine: { show: false }, axisLabel: { color: C.text2, fontSize: 11, lineHeight: 15 } },
      yAxis: yVal({ scale: false }),
      series: [["13 weeks before", "change_13w_before", 0.35], ["13 weeks after", "change_13w_after", 0.7], ["26 weeks after", "change_26w_after", 1]].map(([name, key, a]) => ({
        name, type: "bar", barMaxWidth: 26, data: f.map((r) => r[key]),
        itemStyle: { color: (p) => alpha(color(f[p.dataIndex].company), a), borderRadius: 3 },
        label: { show: true, position: "top", color: C.text2, fontSize: 10, fontFamily: "JetBrains Mono, monospace", formatter: (p) => (p.value > 0 ? `+${p.value}` : p.value) } })),
    });
  }

  // ---------- market ----------
  function renderMarket() {
    const m = D.market;
    const maxP = Math.max(...m.nodes.map((n) => n.postings));
    const narrow = innerWidth < 760;
    mount($("#graph"), {
      tooltip: { trigger: "item", backgroundColor: "rgba(22,27,34,.96)", borderColor: C.axis, textStyle: { color: C.text, fontSize: 12 },
        formatter: (p) => (p.dataType === "edge" ? `${esc(p.data.source)} ↔ ${esc(p.data.target)}: <b>${p.data.value.toFixed(2)}</b>`
          : `<b>${esc(p.data.name)}</b><br><span style="color:${C.muted}">${esc(p.data.segment)}</span><br>${fmt(p.data.postings)} open postings`) },
      series: [{
        type: "graph", layout: "force", roam: !narrow, draggable: true,
        force: { repulsion: narrow ? 150 : 230, edgeLength: [40, 130], gravity: 0.22, layoutAnimation: true },
        label: { show: true, position: "bottom", distance: 3, color: C.text2, fontSize: 11 }, labelLayout: { hideOverlap: true },
        emphasis: { focus: "adjacency", lineStyle: { width: 3 }, label: { color: C.text } },
        lineStyle: { color: "source", curveness: 0.12 },
        data: m.nodes.map((n) => ({ ...n, symbolSize: 8 + 30 * Math.sqrt(n.postings / maxP),
          itemStyle: { color: n.color, borderColor: n.focus ? C.text : "transparent", borderWidth: n.focus ? 1.5 : 0, opacity: n.focus ? 1 : 0.85 },
          label: { fontWeight: n.focus ? 600 : 400, color: n.focus ? C.text : C.text2 } })),
        links: m.edges.map((e) => {
          const fc = [e.source, e.target].find((n) => FOCUS.includes(n));
          return { ...e, lineStyle: { color: fc ? color(fc) : "#8b949e", width: 0.5 + 4 * Math.pow(e.value, 2), opacity: 0.2 + 0.55 * e.value } };
        }),
      }],
    });

    const p = m.pools;
    const short = (s) => { const [fam, kw] = s.split(": "); return `${fam.replace("Sales & Go-to-Market", "GTM").replace("Software Engineering", "SWE").replace("Infrastructure & SRE", "Infra/SRE").replace("Data Center & Facilities", "Data center")} · ${kw || ""}`; };
    const data = [];
    let vmax = 0;
    // colour by sqrt(share) so one dominant cell does not wash out the rest
    p.values.forEach((row, i) => row.forEach((v, j) => { data.push([j, i, Math.sqrt(v), v]); vmax = Math.max(vmax, Math.sqrt(v)); }));
    mount($("#pools"), {
      grid: { left: narrow ? 120 : 190, right: 14, top: 8, bottom: 86 },
      tooltip: { trigger: "item", backgroundColor: "rgba(22,27,34,.96)", borderColor: C.axis, textStyle: { color: C.text, fontSize: 12 },
        formatter: (q) => `<b>${esc(p.companies[q.value[0]])}</b><br>${esc(p.names[q.value[1]])}<br>${(q.value[3] * 100).toFixed(1)}% of postings` },
      xAxis: { type: "category", data: p.companies, ...axisCommon, splitLine: { show: false },
        axisLabel: { color: C.text2, fontSize: 11, rotate: 50, interval: 0, formatter: (v) => v, rich: {} } },
      yAxis: { type: "category", data: p.names.map(short), ...axisCommon, splitLine: { show: false }, axisLabel: { color: C.text2, fontSize: 11, width: narrow ? 110 : 180, overflow: "truncate" } },
      visualMap: { show: false, min: 0, max: vmax, dimension: 2, inRange: { color: [C.panel2, "#1f3a5f", "#3b82c4", "#79c0ff"] } },
      series: [{ type: "heatmap", data, itemStyle: { borderColor: C.panel, borderWidth: 2, borderRadius: 3 }, emphasis: { itemStyle: { borderColor: C.text, borderWidth: 1 } } }],
    });
  }

  // ---------- story: briefing + company chapters ----------
  const CONF_ICON = { confirmed: "✓", likely: "◐", watch: "○" };
  const KIND_LBL = { "data-center site": "data-center site", "regional hub": "regional hub", "sales office": "sales office",
    "engineering hub": "engineering hub", "mixed team": "mixed team" };
  function writer(by) {
    if (!by || by.startsWith("template")) return "Template text from the evidence rules";
    const model = by.split("/").slice(1).join("/");
    return `Written by ${esc(model)} (${esc(by.split("/")[0])}) from the evidence below · every number checked against it`;
  }
  function renderBriefing() {
    const S = D.story, el = $("#briefing");
    if (!S) return;
    const b = S.brief;
    const tops = FOCUS.map((co) => [co, (S.chapters[co].claims || [])[0]]).filter((x) => x[1]);
    el.hidden = false;
    el.innerHTML = `<div class="section-head"><p class="eyebrow">The briefing · ${dateLong(S.generated_at.slice(0, 10))}</p>
        <h2 class="story-h">${esc(b.headline)}</h2></div>
      <p class="story-lede">${esc(b.paragraph)}</p>
      <div class="brief-grid">${tops.map(([co, c]) => `
        <a class="brief-card" href="#ch-${co}" style="--c:${color(co)}">
          <span class="bc-top">${logo(co, 16)}<span>${co}</span><span class="badge b-${c.confidence}">${c.confidence}</span></span>
          <span class="bc-label">${esc(c.label)}</span>
          <span class="bc-fact num">${esc(c.key_fact)}</span>
          ${c.concentrated_in.length ? `<span class="bc-where">📍 ${c.concentrated_in.slice(0, 2).map(esc).join(" · ")}</span>` : ""}
        </a>`).join("")}</div>
      <p class="story-note">${writer(b.written_by)}. Postings show intent, not outcomes: read every claim with its confidence label.</p>`;
  }
  function chapterCounters(co, f) {
    const d = D.companies[co];
    const isRate = d.unit !== "open roles";
    const items = [[fmt(f.size.value, isRate ? 1 : 0), isRate ? "new reqs / day" : "open roles"]];
    if (f.change_6m_pct != null) items.push([`${f.change_6m_pct > 0 ? "+" : ""}${f.change_6m_pct}%`, "in 6 months"]);
    if (f.forecast_next_8_weeks_pct != null) items.push([`${f.forecast_next_8_weeks_pct > 0 ? "+" : ""}${f.forecast_next_8_weeks_pct}%`, "8-week forecast"]);
    if (f.patents && f.patents.change_pct != null) items.push([`${f.patents.change_pct > 0 ? "+" : ""}${f.patents.change_pct}%`, "patent publications, 4 qtrs"]);
    else if (f.financials) items.push([`${f.financials.revenue_yoy > 0 ? "+" : ""}${Math.round(f.financials.revenue_yoy * 100)}%`, "revenue YoY (SEC)"]);
    return `<div class="counters ch-counters">${items.slice(0, 4).map(([v, k]) => `<div class="counter"><div class="v num">${v}</div><div class="k">${k}</div></div>`).join("")}</div>`;
  }
  function evidenceCard(c, text) {
    const t = text || { title: c.label, reading: c.reading };
    const growth = c.new_13w != null && c.prior_13w != null ? `<span><b>${c.prior_13w} → ${c.new_13w}</b> new / 13 wks</span>` : "";
    const lift = c.lift_vs_peers != null ? `<span><b>${c.lift_vs_peers.toFixed(1)}×</b> peer share</span>` : "";
    return `<article class="ev-card">
      <div class="ev-top"><span class="badge b-${c.confidence}" title="${c.confidence === "confirmed" ? "A headline or event matches" : c.confidence === "likely" ? "Strong posting signal" : "Weak or early signal"}">${CONF_ICON[c.confidence] || ""} ${c.confidence}</span><span class="ev-theme">${esc(c.label)}</span></div>
      <h3 class="ev-title">${esc(t.title)}</h3>
      <p class="ev-reading">${esc(t.reading)}</p>
      <div class="ev-stats num"><span><b>${c.open_roles}</b> open roles</span>${growth}${lift}</div>
      ${c.cities.length ? `<div class="ev-where">${c.cities.map(([city, n]) => `<span class="pin">📍 ${esc(city)} <i>${n}</i></span>`).join("")}</div>` : ""}
      <details class="ev-more"><summary>Evidence</summary>
        <p class="ev-k">Example postings</p><ul>${c.examples.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
        <p class="ev-k">Why this reading</p><p>${esc(c.reading)}</p>
        ${c.corroboration.length ? `<p class="ev-k">Corroboration</p><ul>${c.corroboration.map((h) => `<li><a href="${esc(h.url)}" target="_blank" rel="noopener">${esc(h.title)}</a> <span class="mono">${esc(String(h.date).slice(0, 10))}</span></li>`).join("")}</ul>` : `<p class="ev-k">Corroboration</p><p>No matching headline or event yet.</p>`}
      </details>
    </article>`;
  }
  function renderChapters() {
    const S = D.story, root = $("#chapters");
    if (!S) return;
    root.innerHTML = FOCUS.map((co, i) => {
      const ch = S.chapters[co], t = ch.text, f = ch.facts;
      const exps = ch.expansions || [];
      return `<section class="chapter" id="ch-${co}" style="--c:${color(co)}">
        <div class="ch-head">
          <p class="eyebrow ch-eyebrow">${logo(co, 18)}<span>${String(i + 1).padStart(2, "0")} · ${co}</span><span class="ch-seg">${esc(f.segment)}</span></p>
          <h2 class="ch-h">${esc(t.headline)}</h2>
          <p class="story-lede">${esc(t.lede)}</p>
          ${chapterCounters(co, f)}
          <p class="ch-watch"><span>Watch next</span>${esc(t.watch)}</p>
        </div>
        <div class="ev-grid">${ch.claims.map((c) => evidenceCard(c, t.claims[c.id])).join("")}</div>
        ${exps.length ? `<div class="ch-cities"><p class="ev-k">New cities in 2026 and what the postings there suggest</p>
          <ul>${exps.map((e) => `<li title="${esc(e.summary)}"><b>${esc(e.city)}</b><span class="kind">${KIND_LBL[e.kind] || esc(e.kind)}</span><span class="badge ${(arcStatus[e.status] || ["b-context"])[0]}">${esc((arcStatus[e.status] || ["", e.status])[1])}</span></li>`).join("")}</ul></div>` : ""}
        <div class="ch-foot"><span class="story-note">${writer(ch.written_by)}</span>
          <button type="button" class="more ch-more" data-co="${co}">Full ${co} breakdown →</button></div>
      </section>`;
    }).join("");
    root.addEventListener("click", (e) => {
      const b = e.target.closest(".ch-more"); if (!b) return;
      selectTab(b.dataset.co); $("#companies").scrollIntoView({ behavior: "smooth" });
    });
  }

  // ---------- reveal ----------
  const io = "IntersectionObserver" in window ? new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { rootMargin: "0px 0px -8% 0px" }) : null;
  function reveal(root = document) {
    root.querySelectorAll(".section-head, .ch-head, .ev-card").forEach((el) => {
      if (!io || el.classList.contains("in")) return;
      // elements already on screen appear immediately
      const r = el.getBoundingClientRect();
      if (r.top < innerHeight) { el.classList.add("reveal", "in"); return; }
      el.classList.add("reveal"); io.observe(el);
    });
  }

  // ---------- boot ----------
  async function boot() {
    try {
      const names = ["meta", "companies", "globe", "signals", "news", "tracker", "market", "context"];
      const [vals, land] = await Promise.all([Promise.all(names.map((n) => get(`data/${n}.json`))), get("assets/land.json")]);
      names.forEach((n, i) => (D[n] = vals[i])); D.land = land;
      D.story = await get("data/story.json").catch(() => null); // optional: page works without the story layer
    } catch (err) {
      $("#status-text").textContent = "Data failed to load";
      $(".dot").style.background = "#f85149";
      console.error(err); return;
    }
    renderStatus(); renderLegend(); renderExpansions();
    try { renderBriefing(); renderChapters(); } catch (err) { console.error("story", err); }
    renderFilters(); renderFeed(); wireFeed();
    renderPulse(); wireRange();
    renderTabs(); renderDeep();
    renderTracker(); renderMarket();
    try { renderGlobe(); } catch (err) { console.error("globe", err); }
    reveal();
    // content is rendered after load, so honour #anchors once it exists
    if (location.hash) { const t = document.getElementById(location.hash.slice(1)); if (t) setTimeout(() => t.scrollIntoView(), 60); }
  }
  boot();
})();
