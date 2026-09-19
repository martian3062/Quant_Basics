# Frontend: making it look like 2026, not like a lab report

The data work is the project. But the link on your CV gets judged in about four seconds, and a default-styled notebook export reads as "student exercise" no matter how good the Parquet underneath is. This file is the design spec.

**The governing idea: restraint reads as modern.** What dates a data site is decoration — card shadows, gradients, five accent colors, chart junk. What reads current is generous whitespace, hairline rules instead of boxes, one accent, and numbers big enough to be the design. The data is the only thing allowed to be loud.

---

## 1. The finance-specific trap: red and green

Every broker terminal on earth colors up-days green and down-days red. Copy that and you ship a chart a meaningful share of your readers cannot decode.

I measured the conventional pair (`#008000` green / `#ff0000` red) against the colorblind-separation check:

```
[WARN] CVD separation   #ff0000 ↔ #008000   ΔE 7.0 (protan)
[PASS] Normal vision    #ff0000 ↔ #008000   ΔE 38.1
```

Read those two lines together. To you, the pair is maximally distinct — ΔE 38. To a protanope, it is **7**, which is below the ΔE ≥ 8 bar and deep into "these are the same color" territory. Around 8% of men have red-green colour vision deficiency, and quant finance skews heavily male, so your actual audience is *more* affected than the population average, not less.

**The fix costs nothing.** For up/down and above/below-baseline, use the diverging pair **blue ↔ red**, with a neutral gray midpoint. Warm/cool reads as opposite to everyone, and blue↔red survives every CVD simulation. Keep green for the status palette only, where it always ships with an icon and a label beside it.

If you keep red/green anywhere for convention's sake, it is legal only with a second encoding carrying the same information — a `+`/`−` sign, an arrow, a position above/below the axis. Never hue alone.

---

## 2. The palette

Validated in both modes before being written down. Define these as custom properties once and reference them by role, so dark mode swaps in one place.

```css
:root {
  color-scheme: light;
  --surface-1:      #fcfcfb;  /* chart surface */
  --page:           #f9f9f7;  /* page plane, one step behind the surface */
  --text-primary:   #0b0b0b;
  --text-secondary: #52514e;
  --text-muted:     #898781;  /* axis labels, captions */
  --gridline:       #e1e0d9;  /* hairline, solid, never dashed */
  --baseline:       #c3c2b7;
  --hairline:       rgba(11, 11, 11, 0.10);

  --series-1:       #2a78d6;  /* blue   */
  --series-2:       #eb6834;  /* orange */
  --series-3:       #1baf7a;  /* aqua — see the relief note below */

  --diverge-pos:    #2a78d6;  /* blue  — up / above baseline */
  --diverge-neg:    #e34948;  /* red   — down / below */
  --diverge-mid:    #f0efec;

  --status-good:     #0ca30c;
  --status-warning:  #fab219;
  --status-serious:  #ec835a;
  --status-critical: #d03b3b;
}

@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface-1:      #1a1a19;
    --page:           #0d0d0d;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted:     #898781;
    --gridline:       #2c2c2a;
    --baseline:       #383835;
    --hairline:       rgba(255, 255, 255, 0.10);

    --series-1:       #3987e5;
    --series-2:       #d95926;
    --series-3:       #199e70;

    --diverge-pos:    #3987e5;
    --diverge-neg:    #e66767;
    --diverge-mid:    #383835;
  }
}

:root[data-theme="dark"] { /* repeat the dark block so a manual toggle wins */ }
```

**Dark mode is selected, not flipped.** The dark hexes are the same hues re-stepped for a dark surface — they are not `filter: invert()` and not the light values reused. An automatic inversion produces glowing, oversaturated marks. Both columns above were validated separately against their own surface.

Three slots is the working cap. Validator, all-pairs, both modes:

```
LIGHT  worst CVD ΔE 9.2  ·  worst normal-vision ΔE 24.0  →  PASS
DARK   worst CVD ΔE 9.4  ·  worst normal-vision ΔE 20.9  →  PASS
```

Past three series in a scatter or small-multiples grid, no ordering clears the floors — fold the tail into "Other" or facet instead of inventing a fourth hue.

**One relief obligation:** aqua `--series-3` sits at 2.74:1 on the light surface, below the 3:1 bar. If you use it in light mode, it must carry visible direct labels or a table view. Blue and orange are clear of this.

---

## 3. Which form for which check

Pick the form from the data's job. Sometimes the right form is not a chart.

| What you are showing | Form | Color job |
|---|---|---|
| **The headline: how much survivorship bias inflates returns** | **Hero figure**, ≥48px, exactly one per page | none — it is text |
| Symbols audited · trading days · flags by severity · last refresh | **KPI row** of stat tiles | status for the flag counts |
| Biased vs honest equal-weight returns | **2-series line**, both indexed to 100 at t0 | categorical slots 1 + 2 |
| Rolling volatility, symbol × year | **Heatmap** | sequential blue, light→dark |
| Top-20 most volatile stocks in a year | **Bar**, horizontal (long tickers) | one hue — slot 1 for every bar |
| Flagged issues per symbol | **Table** | status color + icon + label |
| Missing days vs the NSE calendar | **Coverage strip** per symbol | status: present / missing |
| Adjusted÷unadjusted ratio over time | **Line vs a baseline of 1.0** | diverging around the rule |

Two form decisions worth defending:

**The hero figure is the whole project in one number.** Something like *"Survivorship bias inflates the 2015–2026 NIFTY 50 equal-weight CAGR by 3.8 percentage points."* That is the sentence a recruiter repeats to someone else. Give it 48px+ and let it sit alone above the fold. Exactly one — a page with three hero numbers has none.

**Never color the top-20 volatility bars by their own value.** Darker-where-bigger double-encodes bar length as hue, burns your only free channel on information the chart already shows, and fails the categorical checks by design. One series, one color, every bar.

---

## 4. Marks — the specs that produce the quiet look

| Mark | Spec |
|---|---|
| Line | **2px**, round join and cap |
| Bar / column | **≤24px thick** — cap it, let the leftover band be air; 4px rounded data-end, square at the baseline |
| End marker | **≥8px** (r ≥ 4), filled with the series color, **2px ring in the surface color** |
| Area fill | series hue at **~10% opacity** — a wash, never a saturated block |
| Gridlines & axes | one step off the surface, **hairline 1px, solid** — never dashed |
| Touching fills | separated by a **2px gap in the surface color**, never by a drawn border |

**Text never wears the data color.** Values, labels, legends and axis text use the ink tokens (`--text-primary` / `--text-secondary` / `--text-muted`). Identity comes from a colored dot or line-key *beside* the text. A light hue like aqua is illegible as text on the surface.

**Label selectively.** A legend is always present for two or more series; direct labels then supplement it at the endpoint, the extreme, or the one series the story is about. A number on every data point is chaos and goes unread.

---

## 5. The survivorship chart, in Observable Plot

The money chart, built to the specs above:

```js
Plot.plot({
  width,
  height: 380,
  marginLeft: 52, marginRight: 84, marginTop: 24, marginBottom: 36,
  style: { background: "transparent", fontSize: "12px" },
  x: { label: null },
  y: {
    label: "Growth of ₹100 invested Jan 2015",
    grid: true,
    ticks: 5,
    tickFormat: ",.0f"
  },
  color: {
    domain: ["Today's constituents", "Point-in-time"],
    range: ["var(--series-2)", "var(--series-1)"],
    legend: true
  },
  marks: [
    // the honest baseline the eye measures against
    Plot.ruleY([100], { stroke: "var(--baseline)", strokeWidth: 1 }),

    Plot.line(data, {
      x: "date", y: "index", stroke: "series",
      strokeWidth: 2, strokeLinejoin: "round", strokeLinecap: "round"
    }),

    // end markers with the 2px surface ring
    Plot.dot(lastPoints, {
      x: "date", y: "index", fill: "series",
      r: 4, stroke: "var(--surface-1)", strokeWidth: 2
    }),

    // direct end labels — in ink, not in the series color
    Plot.text(lastPoints, {
      x: "date", y: "index", text: d => `₹${d.index.toFixed(0)}`,
      dx: 10, textAnchor: "start", fill: "var(--text-secondary)",
      fontWeight: 600
    }),

    Plot.tip(data, Plot.pointerX({
      x: "date", y: "index", stroke: "series",
      format: { index: d => `₹${d.toFixed(1)}`, series: true }
    }))
  ]
})
```

**Both series are indexed to 100 at t0.** This is not cosmetic — it is what lets one y-axis carry both, and it is the correct fix for the dual-axis temptation described below.

Hairline the grid with a little CSS, since Plot's default is heavier than you want:

```css
.plot svg [aria-label$="grid"] line { stroke: var(--gridline); stroke-width: 1; }
.plot svg [aria-label$="axis tick"] text { fill: var(--text-muted); }
```

---

## 6. Layout and type

| Decision | Value | Why |
|---|---|---|
| Typeface | `system-ui, -apple-system, "Segoe UI", sans-serif` | Zero network cost, renders natively correct on every OS, and looks deliberate. No Google Font is needed and no serif or display face belongs anywhere, including the hero figure. |
| Numerals | proportional by default; `font-variant-numeric: tabular-nums` **only** in table columns and axis ticks | Tabular figures give every digit the width of a `0`, so `121` looks loose at 48px |
| Page width | ~1100–1280px max, 16px side gutter on mobile | |
| Prose measure | 65–75ch | Full-width paragraphs are unreadable |
| Separation | hairline rules (`--hairline`) and whitespace | Not shadows, not boxes-within-boxes |
| Card | 1px hairline border, ~12px radius, no shadow | A shadow on every card is the single clearest 2015 tell |
| Vertical rhythm | one spacing scale — 4 / 8 / 16 / 24 / 48 | |

Page order: hero figure → KPI row → the survivorship chart → the audit table → the per-check detail. Lead with the finding, not with the methodology.

**Filters go in one row above everything they scope** — never inside a chart card, never per-chart. Every chart re-renders against the same slice. On refetch, hold the previous render at reduced opacity rather than flashing a skeleton; a layout jump is worse than a stale half-second.

---

## 7. Observable Framework specifics

```js
// observablehq.config.js
export default {
  title: "NSE Data Lake · Bias Auditor",
  theme: ["air", "near-midnight"],   // light + dark pair; Framework handles the switch
  root: "src",
  footer: "Data: yfinance + NSE bhavcopy · rebuilt nightly",
  style: "style.css"                 // your palette block from §2 goes here
};
```

Framework exposes its own theme tokens (`--theme-foreground`, `--theme-background`, `--theme-foreground-muted`, and similar) — map your palette onto those in `style.css` so the built-in components inherit it rather than fighting it. Verify the exact token names against the current Framework docs; they have moved before.

Layout comes from Framework's grid utilities:

```html
<div class="grid grid-cols-4">
  <div class="card"><h2>Symbols audited</h2><span class="big">50</span></div>
  ...
</div>
```

---

## 8. Accessibility, which is also just quality

- **Every chart has a table-view twin.** This is the honest fallback and it costs almost nothing — you already have the data in DuckDB. It is also the thing that makes the relief obligation on aqua go away.
- **Keyboard focus shows what hover shows.** A tooltip must never be the only route to a value.
- **Hit targets ≥24px.** An 8px scatter dot you have to land on dead-centre is not interactive.
- **Two or more series → a legend, always.** Identity is never carried by color alone.

---

## 9. Check the result against these before you ship

Finance dashboards fail in a small number of predictable ways.

- [ ] **No dual-axis chart anywhere.** Two y-scales on one plot is the single most common charting mistake: the alignment between the scales is arbitrary, so the chart invents a correlation that is not in the data. Price-and-volume on one plot is the classic offender. Fix with two stacked charts sharing an x-axis, or index both series to 100.
- [ ] No red/green as the sole encoding of direction (§1).
- [ ] No value-ramp coloring on nominal categories.
- [ ] No rainbow ramp for magnitude — one hue, light→dark.
- [ ] No hue at a diverging midpoint; the midpoint is neutral gray.
- [ ] No dashed gridlines.
- [ ] No number printed on every data point.
- [ ] No border drawn around marks to separate them — the 2px surface gap does that.
- [ ] No pie or donut. You have no part-to-whole story here.
- [ ] Container height includes the x-axis band, so no card gets a tiny nested scrollbar.
- [ ] Exactly one hero figure.
- [ ] **Render it and look at it.** The validator checks color, not layout. Screenshot the page at 1280px and at 390px and check for label collisions and overflow.
