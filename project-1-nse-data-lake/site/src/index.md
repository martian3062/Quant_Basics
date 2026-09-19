---
title: Bias Auditor
toc: false
---

```js
const dashboard = await FileAttachment("data/dashboard.json").json();
const number = new Intl.NumberFormat("en-IN");
const oneDecimal = new Intl.NumberFormat("en-IN", {minimumFractionDigits: 1, maximumFractionDigits: 1});
const percent = new Intl.NumberFormat("en-IN", {style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1});
const refreshDate = new Intl.DateTimeFormat("en-IN", {dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata"}).format(new Date(dashboard.meta.generated_at));
const survivorship = dashboard.survivorship.map((d) => ({...d, date: new Date(`${d.date}T00:00:00Z`)}));
const symbols = ["All symbols", ...Array.from(new Set(dashboard.flags.map((d) => d.symbol))).sort(d3.ascending)];
const years = Array.from(new Set(dashboard.volatility.map((d) => d.year))).sort(d3.descending);
```

```js
const filteredFlags = dashboard.flags.filter((d) =>
  (filters.symbol === "All symbols" || d.symbol === filters.symbol) &&
  (filters.severity === "All severities" || d.severity === filters.severity)
);
const severityOrder = ["critical", "serious", "warning"];
const filteredSummary = severityOrder.map((severity) => ({
  severity,
  count: filteredFlags.filter((d) => d.severity === severity).length
}));
const selectedVolatility = dashboard.volatility.filter((d) => d.year === Number(filters.year));
```

```js
function survivorshipPlot(data, {width}) {
  const lastPoints = Array.from(
    d3.group(data, (d) => d.series),
    ([, values]) => d3.greatest(values, (d) => d.date)
  );
  return Plot.plot({
    width,
    height: width < 520 ? 310 : 390,
    marginTop: 18,
    marginRight: width < 520 ? 20 : 88,
    marginBottom: 38,
    marginLeft: 58,
    style: {background: "transparent", color: "var(--text-muted)", fontSize: "11px"},
    x: {label: null, ticks: width < 520 ? 4 : 7, tickFormat: d3.utcFormat("%Y")},
    y: {label: "Growth of ₹100", grid: true, ticks: 5, tickFormat: ",.0f"},
    color: {
      domain: ["Today's constituents", "Point-in-time"],
      range: ["var(--series-2)", "var(--series-1)"]
    },
    marks: [
      Plot.ruleY([100], {stroke: "var(--baseline)", strokeWidth: 1}),
      Plot.lineY(data, {x: "date", y: "index", stroke: "series", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round"}),
      Plot.dot(lastPoints, {x: "date", y: "index", fill: "series", r: 4, stroke: "var(--surface-1)", strokeWidth: 2}),
      width >= 620 ? Plot.text(lastPoints, {x: "date", y: "index", text: (d) => `₹${d.index.toFixed(0)}`, dx: 10, textAnchor: "start", fill: "var(--text-secondary)", fontWeight: 650}) : null,
      Plot.tip(data, Plot.pointerX({x: "date", y: "index", stroke: "series", format: {date: "%b %Y", index: (d) => `₹${d.toFixed(1)}`, series: true}}))
    ].filter(Boolean),
    ariaLabel: "Growth of 100 rupees using today's constituents compared with point-in-time constituents"
  });
}

function severityPlot(data, {width}) {
  const colors = {critical: "var(--status-critical)", serious: "var(--status-serious)", warning: "var(--status-warning)"};
  return Plot.plot({
    width,
    height: 238,
    marginTop: 8,
    marginRight: 30,
    marginBottom: 30,
    marginLeft: 72,
    style: {background: "transparent", color: "var(--text-muted)", fontSize: "11px"},
    x: {label: "Flags", grid: true, ticks: 4},
    y: {label: null, domain: severityOrder},
    marks: [
      Plot.barX(data, {x: "count", y: "severity", fill: (d) => colors[d.severity], insetTop: 9, insetBottom: 9, rx: 4}),
      Plot.text(data, {x: "count", y: "severity", text: "count", dx: 7, textAnchor: "start", fill: "var(--text-secondary)", fontWeight: 650}),
      Plot.ruleX([0], {stroke: "var(--baseline)"})
    ],
    ariaLabel: "Audit flags grouped by severity"
  });
}

function volatilityPlot(data, {width}) {
  return Plot.plot({
    width,
    height: 330,
    marginTop: 8,
    marginRight: 28,
    marginBottom: 36,
    marginLeft: 88,
    style: {background: "transparent", color: "var(--text-muted)", fontSize: "11px"},
    x: {label: "Annualized volatility", grid: true, tickFormat: ".0%"},
    y: {label: null, domain: data.map((d) => d.symbol)},
    marks: [
      Plot.barX(data, {x: "annualized_volatility", y: "symbol", fill: "var(--series-1)", insetTop: 5, insetBottom: 5, rx: 4}),
      Plot.ruleX([0], {stroke: "var(--baseline)"}),
      Plot.tip(data, Plot.pointerY({x: "annualized_volatility", y: "symbol", format: {annualized_volatility: ".1%"}}))
    ],
    ariaLabel: `Most volatile NIFTY 50 symbols in ${filters.year}`
  });
}

function auditTable(rows) {
  if (!rows.length) return html`<div class="empty-state">No flags match the current filters.</div>`;
  return html`<div class="table-scroll"><table class="audit-table" aria-label="Filtered audit flags">
    <thead><tr><th>Symbol</th><th>Date</th><th>Severity</th><th>Check</th><th>Detail</th></tr></thead>
    <tbody>${rows.slice(0, 12).map((d) => html`<tr>
      <td>${d.symbol}</td>
      <td>${d.date}</td>
      <td><span class=${`severity-chip severity-${d.severity}`}>${d.severity}</span></td>
      <td><span class="check-chip">${d.check_id.replaceAll("_", " ")}</span></td>
      <td>${d.detail}</td>
    </tr>`)}</tbody>
  </table></div>`;
}

function seriesTable(data) {
  const grouped = d3.group(data, (d) => d.date.toISOString().slice(0, 10));
  const rows = Array.from(grouped, ([date, values]) => ({
    date,
    biased: values.find((d) => d.series === "Today's constituents")?.index,
    honest: values.find((d) => d.series === "Point-in-time")?.index
  })).filter((_, index) => index % 12 === 0 || index === grouped.size - 1);
  return html`<div class="table-scroll"><table class="fallback-table" aria-label="Annual survivorship series values">
    <thead><tr><th>Date</th><th>Today's constituents</th><th>Point-in-time</th></tr></thead>
    <tbody>${rows.map((d) => html`<tr><td>${d.date}</td><td>₹${oneDecimal.format(d.biased)}</td><td>₹${oneDecimal.format(d.honest)}</td></tr>`)}</tbody>
  </table></div>`;
}
```

<header class="masthead">
  <div class="brand-lockup">
    <div class="brand-mark" aria-hidden="true">NL</div>
    <div>
      <div class="brand-name">NSE Data Lake</div>
      <div class="brand-subtitle">Bias Auditor · India equities</div>
    </div>
  </div>
  <div class="status-chip"><span class="status-dot"></span>${dashboard.meta.is_demo ? "Prototype data" : "Lake current"}</div>
</header>

<main>
  <section class="hero" aria-labelledby="hero-title">
    <div>
      <div class="eyebrow">Survivorship bias · ${dashboard.meta.period_start.slice(0, 4)}–${dashboard.meta.period_end.slice(0, 4)}</div>
      <h1 id="hero-title">Today’s winners make yesterday’s market look better than it was.</h1>
    </div>
    <div class="hero-number-wrap">
      <div class="hero-number">+${oneDecimal.format(dashboard.hero.bias_percentage_points)}<span class="hero-unit">pp</span></div>
      <p class="hero-caption">CAGR inflation when the current NIFTY 50 membership is projected backward: ${oneDecimal.format(dashboard.hero.biased_cagr)}% vs ${oneDecimal.format(dashboard.hero.honest_cagr)}%.</p>
    </div>
  </section>

  ${dashboard.meta.is_demo ? html`<div class="notice"><span aria-hidden="true">◌</span><span><strong>Frontend prototype.</strong> ${dashboard.meta.source_note} Every illustrative value is labelled here so it cannot be mistaken for a completed research result.</span></div>` : null}

  <div class="kpi-grid" aria-label="Audit summary">
    <div class="kpi"><div class="kpi-label">Symbols audited</div><div class="kpi-value">${number.format(dashboard.kpis.symbols_audited)}</div><div class="kpi-detail">Current NIFTY 50 universe</div></div>
    <div class="kpi"><div class="kpi-label">Trading sessions</div><div class="kpi-value">${number.format(dashboard.kpis.trading_days)}</div><div class="kpi-detail">Benchmark-observed sessions</div></div>
    <div class="kpi"><div class="kpi-label">Audit flags</div><div class="kpi-value">${number.format(dashboard.kpis.flags)}</div><div class="kpi-detail">${dashboard.kpis.critical_flags} critical · icon + label encoded</div></div>
    <div class="kpi"><div class="kpi-label">Snapshot generated</div><div class="kpi-value">${dashboard.meta.period_end.slice(0, 4)}</div><div class="kpi-detail">${refreshDate} IST</div></div>
  </div>

  <div class="section-heading">
    <div><div class="section-kicker">Research result</div><h2>One universe. Two histories.</h2></div>
    <p class="section-copy">Both paths begin at ₹100. The orange line uses today’s constituents; the blue line respects membership at each point in time.</p>
  </div>

  <section class="panel" aria-label="Survivorship comparison">
    <div class="panel-header">
      <h3 class="panel-title">Equal-weight NIFTY 50 growth</h3>
      <div class="legend" aria-label="Chart legend">
        <span class="legend-item"><span class="legend-line" style="--legend-color: var(--series-2)"></span>Today’s constituents</span>
        <span class="legend-item"><span class="legend-line" style="--legend-color: var(--series-1)"></span>Point-in-time</span>
      </div>
    </div>
    <div class="plot-wrap">${resize((width) => survivorshipPlot(survivorship, {width}))}</div>
    <details class="data-fallback"><summary>View annual values as a table</summary>${seriesTable(survivorship)}</details>
  </section>

  <div class="section-heading">
    <div><div class="section-kicker">Quality control</div><h2>Every exception stays visible.</h2></div>
    <p class="section-copy">The controls below scope both the issue table and summary chart. Filters preserve the previous layout—nothing jumps while the view updates.</p>
  </div>

```js
const filters = view(Inputs.form({
  symbol: Inputs.select(symbols, {label: "Symbol", value: "All symbols"}),
  severity: Inputs.select(["All severities", "critical", "serious", "warning"], {label: "Severity", value: "All severities", format: (d) => d[0].toUpperCase() + d.slice(1)}),
  year: Inputs.select(years, {label: "Volatility year", value: d3.max(years), format: String})
}, {
  template: (inputs) => html`<div class="filter-grid">${inputs.symbol}${inputs.severity}${inputs.year}</div>`
}));
```

  <div class="split-grid">
    <section class="panel" aria-label="Audit issue table">
      <div class="panel-header"><h3 class="panel-title">Flagged issues</h3><span class="muted">${filteredFlags.length} matching</span></div>
      ${auditTable(filteredFlags)}
    </section>
    <section class="panel" aria-label="Flags by severity">
      <div class="panel-header"><h3 class="panel-title">Severity mix</h3><span class="muted">Selected slice</span></div>
      <div class="plot-wrap" style="min-height: 238px">${resize((width) => severityPlot(filteredSummary, {width}))}</div>
      <details class="data-fallback"><summary>View severity counts as a table</summary>
        <table class="fallback-table"><thead><tr><th>Severity</th><th>Flags</th></tr></thead><tbody>${filteredSummary.map((d) => html`<tr><td>${d.severity}</td><td>${d.count}</td></tr>`)}</tbody></table>
      </details>
    </section>
  </div>

  <div class="section-heading">
    <div><div class="section-kicker">Per-check detail</div><h2>Coverage and volatility.</h2></div>
    <p class="section-copy">Coverage exposes absent observations; volatility highlights where a price anomaly can create the most analytical damage.</p>
  </div>

  <div class="split-grid">
    <section class="panel">
      <div class="panel-header"><h3 class="panel-title">Top volatility · ${filters.year}</h3><span class="muted">Annualized</span></div>
      <div class="plot-wrap" style="min-height: 330px">${resize((width) => volatilityPlot(selectedVolatility, {width}))}</div>
      <details class="data-fallback"><summary>View volatility as a table</summary>
        <table class="fallback-table"><thead><tr><th>Symbol</th><th>Volatility</th></tr></thead><tbody>${selectedVolatility.map((d) => html`<tr><td>${d.symbol}</td><td>${percent.format(d.annualized_volatility)}</td></tr>`)}</tbody></table>
      </details>
    </section>
    <section class="panel">
      <div class="panel-header"><h3 class="panel-title">Session coverage</h3><span class="muted">Selected symbols</span></div>
      <div class="panel-pad coverage-list">
        ${dashboard.coverage.map((d) => html`<div class="coverage-row">
          <span class="coverage-symbol">${d.symbol}</span>
          <div class="coverage-track" role="progressbar" aria-label=${`${d.symbol} session coverage`} aria-valuemin="0" aria-valuemax="100" aria-valuenow=${(d.observed / d.expected * 100).toFixed(2)}><div class="coverage-fill" style=${`width: ${d.observed / d.expected * 100}%`}></div></div>
          <span class="coverage-value">${d.missing ? `${d.missing} missing` : "Complete"}</span>
        </div>`)}
      </div>
      <details class="data-fallback"><summary>View coverage counts as a table</summary>
        <table class="fallback-table"><thead><tr><th>Symbol</th><th>Observed</th><th>Expected</th><th>Missing</th></tr></thead><tbody>${dashboard.coverage.map((d) => html`<tr><td>${d.symbol}</td><td>${d.observed}</td><td>${d.expected}</td><td>${d.missing}</td></tr>`)}</tbody></table>
      </details>
    </section>
  </div>

  <aside class="method-note">
    <div class="section-kicker">Method note</div>
    <p>Raw and adjusted closes are ingested separately, timestamps are stored in UTC, and symbol-level gaps are compared with observed NIFTY 50 sessions. The final survivorship result will be published only after historical index membership is reconstructed and reconciled against NSE reconstitution notices.</p>
  </aside>
</main>
