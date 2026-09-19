# Stack: building Project 1 so it deploys live on Netlify

## The one constraint that decides everything

**Netlify does not run Python.** It serves static files from a CDN, plus short-lived serverless functions (Node/Go/Rust, ~10 s, cold starts). There is no long-lived Python process.

That rules out the obvious choices:

| Tool | Runs on Netlify? | Why not |
|---|---|---|
| Streamlit | No | needs a persistent Python server |
| Dash / Panel / Voila | No | same |
| Marimo in `run` mode | No | same — it is a Python websocket server |
| FastAPI + DuckDB | No | same |
| Jupyter | No | same |

If you want Streamlit-style hosting, you need a different host — see [the appendix](#appendix-if-you-do-want-a-python-host). But for this project you do not need one.

## The thing that saves you: your data is tiny

NIFTY 50, daily bars, 2015 → today:

```
50 symbols × ~2,600 trading days × ~8 columns ≈ 1M cells
Parquet with compression ≈ 3–6 MB total
```

That is smaller than one hero image on a marketing site. **You can ship the entire data lake as static files** and query it in the browser. No database, no API, no server, no cold starts, no bill.

This only holds for daily bars. The moment you go to minute or tick data (Ch 7+), you need a real backend — but that is a later problem, and by then you will want MotherDuck or R2, not Netlify.

## Architecture: build-time Python, run-time WASM

```
GitHub Actions  (cron: nightly, 02:00 IST)
  │
  ├── uv run python -m nse_lake.ingest     yfinance + NSE bhavcopy  →  Polars
  ├── uv run python -m nse_lake.audit      5 checks                 →  audit_flags.parquet
  └── commit data/*.parquet  (or push to a release / R2 / HF)
        │
        ▼  push triggers
Netlify build   (Node only — no Python here)
  │
  └── npm run build       Observable Framework
        └── data loaders read data/*.parquet, emit dist/
              │
              ▼
Netlify CDN  →  browser
  └── DuckDB-WASM loads, HTTP-range-reads the Parquet, runs your SQL client-side
```

**The key move: keep Python out of the Netlify build.** Netlify's build image has a Python, but pinning versions, installing uv, and compiling wheels there is a reliable source of 4 a.m. build failures. Let GitHub Actions own Python and commit the Parquet artifacts. Netlify then only has to run `npm run build`, which it is very good at. It also means a broken data refresh never takes down the live site.

## The stack, layer by layer

| Layer | Pick | Why this one |
|---|---|---|
| Env + deps | **uv** | lockfile, 10–100× faster than pip, `uv run` is one line in CI |
| Ingest | **yfinance** + NSE bhavcopy | free; bhavcopy is the official second source for reconciliation |
| Corporate actions | **NSE corporate-actions feed** | turns check 1 from inference into verification — see [DATA_SOURCES.md](DATA_SOURCES.md) |
| Calendar | **exchange_calendars** (`XNSE`) | the correct answer for check 3 — do not hand-roll a holiday list |
| Transform | **Polars** | lazy frames, `scan_parquet`, genuinely faster than pandas, and the API pushes you toward correct code |
| Store (format) | **Parquet**, hive-partitioned `symbol=RELIANCE/` | columnar, compressed, readable by DuckDB over plain HTTP |
| Store (location) | **git** while under ~50 MB → **HF Datasets** after | free, versioned, HTTP range reads; one copy, two readers |
| Query (dev) | **DuckDB** (Python) | SQL straight over the Parquet glob, zero load step |
| Query (prod) | **DuckDB-WASM** | same SQL, in the browser, no server |
| Notebook | **Marimo** | reactive, stored as plain `.py`, diffs properly in git |
| Site | **Observable Framework** | static SSG whose *data loaders can be Python scripts*; DuckDB-WASM and charts are built in |
| Charts | **Observable Plot** | ships with Framework, grammar-of-graphics |
| Design | **see [FRONTEND.md](FRONTEND.md)** | validated palette, form choices, mark specs, the red/green trap |
| CI + cron | **GitHub Actions** | free cron, owns the entire Python half |
| Host | **Netlify** → **Cloudflare Pages** if bandwidth bites | free tier, deploy previews; CF has unlimited bandwidth |
| Python host | **none for this project** | HF Spaces only if you add a live app — Project 2 is where it earns its place |

**In one line:** GitHub Actions runs Python nightly and writes Parquet; Netlify builds a static Observable Framework site; DuckDB-WASM queries the Parquet in the visitor's browser. No server anywhere.

## Why Observable Framework for the site

You asked for the best stack, so here is the real comparison rather than a list.

| Option | Static? | Python at build? | Effort | Verdict |
|---|---|---|---|---|
| **Observable Framework** | yes | **yes — data loaders** | medium | **Pick this.** Your `.parquet.py` loader runs Polars/DuckDB at build time; the browser queries the output with DuckDB-WASM. All the analysis stays Python; only the page layout is JS. |
| Marimo WASM export | yes | in-browser Pyodide | lowest | `marimo export html-wasm` is one command and genuinely works. But Pyodide is a ~10–30 MB cold load, some wheels are missing, and it will feel slow. Great as a `/playground` page, weak as the front door. |
| Evidence.dev | yes | no | low | SQL + Markdown → polished BI site, DuckDB built in, first-class Netlify support. Pick this instead if you want it looking sharp in a day and you are happy writing SQL, not Python. |
| Next.js / Astro, hand-rolled | yes | no | high | Full control, and the most JS you will have to write. Not worth it here. |
| Streamlit | **no** | — | — | Not deployable to Netlify. Use HF Spaces if you want it. |

The decisive point for Framework: **data loaders let you keep writing Python.** A file at `site/src/data/audit_flags.parquet.py` that prints Parquet to stdout becomes a file the client can query. Nothing else on this list gives you that.

If the JS puts you off, ship the Marimo WASM export first to get a live URL this weekend, then migrate. The Parquet layer does not change, so the migration is cheap.

## Repo layout

```
project-1-nse-data-lake/
├── pyproject.toml              # uv
├── uv.lock
├── netlify.toml
├── .github/workflows/refresh.yml
│
├── src/nse_lake/
│   ├── universe.py             # NIFTY 50 constituents, incl. historical changes
│   ├── ingest.py               # yfinance + bhavcopy → Polars → Parquet
│   ├── calendar.py             # exchange_calendars XNSE
│   ├── audit/
│   │   ├── splits.py           # check 1  adjusted vs unadjusted
│   │   ├── bad_ticks.py        # check 2  6σ + reversal
│   │   ├── missing.py          # check 3  vs trading calendar
│   │   ├── timezone.py         # check 4  UTC store, IST display
│   │   └── survivorship.py     # check 5  index membership drift
│   └── queries.sql             # rolling vol, top-20 by year
│
├── data/                       # committed — it is only a few MB
│   ├── prices/symbol=RELIANCE/part-0.parquet
│   ├── audit_flags.parquet
│   └── universe_history.parquet
│
├── notebooks/
│   └── data_audit.py           # marimo, local exploration
│
└── site/                       # Observable Framework
    ├── observablehq.config.js
    ├── package.json
    └── src/
        ├── index.md            # the dashboard
        └── data/
            └── audit_summary.parquet.py   # build-time Python loader
```

## netlify.toml

```toml
[build]
  base    = "project-1-nse-data-lake/site"
  command = "npm ci && npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "22"

# Parquet is content-addressed by the build; cache it hard.
[[headers]]
  for = "/_file/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/*.parquet"
  [headers.values]
    Content-Type  = "application/vnd.apache.parquet"
    Cache-Control = "public, max-age=3600"
```

## Nightly refresh workflow

```yaml
# .github/workflows/refresh.yml
name: refresh-data
on:
  schedule:
    - cron: "30 20 * * 1-5"   # 02:00 IST, Tue–Sat (after the NSE close)
  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --frozen
        working-directory: project-1-nse-data-lake
      - run: |
          uv run python -m nse_lake.ingest
          uv run python -m nse_lake.audit
        working-directory: project-1-nse-data-lake
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "data: nightly refresh"
          file_pattern: "project-1-nse-data-lake/data/**"
```

The commit triggers the Netlify build. One cron, one dependency arrow, nothing to babysit.

## Gotchas that will actually bite you

1. **yfinance in CI gets rate-limited and occasionally returns empty frames.** Never overwrite good Parquet with an empty result — assert row counts before writing, and fail the job instead.
2. **`auto_adjust` changed default in yfinance.** Pull both adjusted and unadjusted explicitly; check 1 depends on having both, and a silent default flip will quietly break it.
3. **DuckDB-WASM multi-threading needs COOP/COEP headers.** Single-threaded works fine without them, and at 5 MB you will not notice. Do not fight this.
4. **Commit Parquet, not CSV, and keep files over ~50 MB out of git.** You are far under, but if you later add intraday, switch to Cloudflare R2 or a HF dataset and have the loader fetch at build time.
5. **Netlify free tier** is around 100 GB bandwidth and 300 build minutes a month at the time of writing — verify current limits. A nightly build of a static site is comfortably inside it. Turn off builds on every branch push if you get close.
6. **Timezone (check 4) will catch you in CI.** GitHub runners are UTC, your laptop is IST. That is a feature — it is exactly the bug the check exists to find. Pin `tz="UTC"` on every parse and convert only for display.

## Build order for the weekend

| Step | Output | Hours |
|---|---|---|
| 1 | `uv init`, ingest 50 symbols → `data/prices/` | 2 |
| 2 | Checks 1–3 → `audit_flags.parquet` | 3 |
| 3 | DuckDB queries, verify the <1 s target | 1 |
| 4 | Marimo notebook, both charts | 2 |
| 5 | Checks 4–5 (survivorship needs the constituent history) | 3 |
| 6 | Observable Framework site, one page | 3 |
| 7 | `netlify.toml`, first deploy, custom subdomain | 1 |
| 8 | GitHub Actions cron | 1 |

Steps 1–4 are the weekend. Steps 5–8 are the "it is live" days.

---

# Appendix: static hosts other than Netlify

## Three things differentiate them — none is developer experience

Every static host serves HTML well, so the usual comparisons are useless. This is a **data site**, and that changes which properties matter.

1. **HTTP range requests on `.parquet`.** DuckDB-WASM reads *slices* of a Parquet file — it fetches the footer, finds the row groups it needs, and pulls only those byte ranges. If the host does not return `Accept-Ranges: bytes` and honour `Range`, every query silently degrades to downloading the whole file. This is the one hard requirement.
2. **Custom response headers.** You need `Cache-Control` on the Parquet, and `COOP`/`COEP` if you ever want DuckDB-WASM's threaded build. A host that cannot set headers cannot do this.
3. **Bandwidth.** Ordinary sites ship kilobytes per visit. Yours ships megabytes. Bandwidth is the limit you will hit first, and the only one that costs money.

Build minutes barely matter — one nightly build of a static site is nothing on any free tier.

## The comparison

| Host | Bandwidth (free) | Range reqs | Custom headers | Notes |
|---|---|---|---|---|
| **Cloudflare Pages** | **unlimited** | yes | `_headers` | **The one worth switching to.** Unlimited bandwidth removes the only limit that can actually bite a Parquet site. Excellent CDN, free custom domain, ~500 builds/mo. |
| **Netlify** | ~100 GB/mo | yes | `netlify.toml` | Best DX, best deploy previews. 100 GB ≈ 20,000 visits at 5 MB each — almost certainly enough. Stay here by default. |
| **Vercel** | ~100 GB/mo | yes | `vercel.json` | Equal to Netlify technically. Hobby tier formally prohibits commercial use; a portfolio is fine. |
| **Render Static Sites** | ~100 GB/mo | yes | dashboard/config | Perfectly capable. No reason to prefer it over the three above. |
| **Cloudflare Pages + R2** | unlimited, **zero egress** | yes | yes | Where you go when the Parquet outgrows git. R2 charges nothing for egress, which is unique. |
| **GitHub Pages** | ~100 GB/mo soft | yes | **no** | **See the trap below.** |
| **Azure Static Web Apps** | ~100 GB/mo | yes | `staticwebapp.config.json` | Fine, more ceremony than it is worth. |
| **AWS S3 + CloudFront** | 12-month free tier | yes | yes | Total control, most setup, real bills afterwards. |
| **Firebase Hosting** | ~360 MB/**day** | yes | `firebase.json` | That daily cap is tight for multi-MB pages. Avoid. |
| **Surge.sh** | generous | yes | limited | Fine for a throwaway demo, not a portfolio piece. |

## The GitHub Pages trap

It is the free host everyone reaches for, and it is the wrong one here — **it cannot set custom response headers.** That means:

- No `Cache-Control` on your Parquet, so you get whatever GitHub decides.
- No COOP/COEP, so DuckDB-WASM threading is permanently off the table.
- A 1 GB repository limit, which is a real ceiling once you add intraday data.

Range requests do work, so the site will function. You just lose the levers. Use it only if you want the absolute shortest path to a URL.

## Verify range support before you trust a host

One command, on any host, against a deployed Parquet file:

```bash
curl -sI -H "Range: bytes=0-1023" https://yoursite.netlify.app/_file/prices.parquet \
  | grep -iE "^(HTTP|accept-ranges|content-range|content-length)"
```

You want `HTTP/2 206`, an `Accept-Ranges: bytes`, and a `Content-Range` showing 1024 bytes — not `200` with the full file length. A `200` means the CDN is ignoring your `Range` header and DuckDB-WASM will be pulling the entire file on every query.

## Verdict

**Stay on Netlify.** 100 GB is roughly 20,000 full page loads a month, and you will not see that.

**Switch to Cloudflare Pages if** you post the project somewhere it might actually get traffic, or you start shipping more than ~10 MB of Parquet. Unlimited bandwidth is the single feature that matters for a data-heavy static site, and Cloudflare is the only free tier that offers it.

Switching costs about ten minutes either way — the build is `npm run build` → publish `dist/` everywhere. Only the config file name changes, and the `netlify.toml` headers translate almost line-for-line into a Cloudflare `_headers` file:

```
# site/src/_headers  — Cloudflare Pages equivalent
/_file/*
  Cache-Control: public, max-age=31536000, immutable

/*.parquet
  Cache-Control: public, max-age=3600
```

Do not let the choice block you. Deploy to Netlify this weekend; move later if bandwidth ever becomes a real number rather than a hypothetical one.

---

# Appendix: if you do want a Python host

Prices and limits move fast on all of these. Verify before you commit.

## Rank them on cold start, not on price

Every free Python tier pays for itself the same way: **it stops your container when nobody is using it.** Render, Hugging Face Spaces, Fly, Koyeb, Streamlit Cloud — all of them. The first visitor after an idle period waits for a cold boot.

That is the number that matters, because of how the link gets used:

> A recruiter opens your CV, clicks the project link, sees a blank page, and closes the tab in about eight seconds.

Render's free web services sleep after roughly 15 minutes of inactivity and take **~30–60 s** to wake. Your portfolio link is idle essentially all the time, so *every real visitor* hits the cold path. A dashboard that loads in 50 seconds reads as broken, not as thrifty.

This is the whole argument for the static Netlify build. A CDN has no cold start, because there is nothing to start.

## The alternatives

| Host | Free tier | Cold start | Best for |
|---|---|---|---|
| **Hugging Face Spaces** | genuinely free, no card — ~2 vCPU / 16 GB, Docker, Gradio, Streamlit | sleeps after long idle, wakes in ~10–30 s | **Best free option.** Right audience for quant/ML, and the natural home for Project 2's Chronos and TimesFM work. |
| **Google Cloud Run** | ~2M req/mo, scale-to-zero, `asia-south1` is Mumbai | ~1–5 s from zero | **The real production answer.** Any Docker image, fast wake, cheap past free. Needs a card. |
| **Modal** | ~$30/mo credits | ~1–3 s | **Best for Project 2.** Serverless Python built for compute — Monte Carlo paths and GPU inference. Also serves web endpoints. |
| **Fly.io** | no true free tier now; small apps land ~$2–3/mo | ~1–3 s, auto stop/start | Persistent machines, `bom` (Mumbai) region. Good if you want a real always-on box cheaply. |
| **Railway** | trial credit, then ~$5/mo minimum | none if always-on | Best developer experience on the list. Pay the $5 and cold starts stop being your problem. |
| **Render** | free web services | **~30–60 s** | Fine once you are on a paid instance. The free tier is the problem, not the platform. |
| **Vercel** | Python *serverless functions* | ~1 s | Same static-first shape as Netlify, but it will run a FastAPI handler. Migrating there buys you an escape hatch Netlify does not have. |
| **Streamlit Community Cloud** | free | sleeps, slow wake | Zero-config, but Streamlit only, and it stamps your project as a toy. |
| **Oracle Cloud Always Free** | 4 ARM cores / 24 GB, genuinely free forever | none — it is a VM | Absurd value, but you run the whole box yourself and account approval is notoriously flaky. |
| **Hetzner** | none, ~€4/mo | none | Best price/performance anywhere. You manage Linux, TLS, and deploys. |
| **PythonAnywhere** | free tier | always-on | **Avoid for this project.** The free tier only allows outbound HTTP to a whitelist, so yfinance and the NSE bhavcopy download will both fail. |
| **Heroku** | none since 2022 | — | Skip. |

## What I would actually do

| Need | Host | Why |
|---|---|---|
| Project 1 dashboard | **Netlify, static** | No cold start, no bill, no ops. The data is 5 MB. |
| A live Marimo or Streamlit toy alongside it | **Hugging Face Spaces** | Free, no card, and idle-sleep is acceptable for a secondary link. |
| Project 2 simulations and foundation models | **Modal** | Built for burst compute; GPU when Chronos needs it. |
| Project 3 MCP server | **nothing hosted** | MCP runs locally over stdio. Host it only if you need remote HTTP transport, and then Cloud Run. |
| If you outgrow all of it | **Google Cloud Run** | Docker, Mumbai region, scale-to-zero, ~2 s wake. |

## Two things to get right before you split the stack

### 1. Hugging Face is not a scheduler

A Space is a server that serves an app. It is not cron. **GitHub Actions still owns the nightly refresh** in every version of this architecture — do not try to move the pipeline into a Space.

The division of labour:

| Job | Runs where | Why |
|---|---|---|
| Nightly ingest + audit | **GitHub Actions** | It is a cron with a Python runtime. That is exactly the job. |
| Storing the Parquet | **HF Datasets** (or git, while small) | Free, versioned, served over HTTP with range support. |
| The static dashboard | **Netlify** | No cold start. The front door. |
| An interactive Python app | **HF Space** | Only if you actually have one. For Project 1 you do not. |

### 2. The seam: where does the Parquet live?

The moment two hosts need the same data, you have a sync problem, and this is where split stacks rot. Do not let Netlify and a Space each build their own copy.

**One source of truth, two readers:**

```
GitHub Actions (nightly)
  └── writes Parquet ──► HF Datasets repo        ← the only copy
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
   Netlify build downloads it           HF Space reads it
   into dist/ (server-side)             natively, same infra
              │
              ▼
   browser queries same-origin
   with DuckDB-WASM
```

**Have the Netlify *build* download the Parquet, not the browser.** It costs one line in the build command and it removes cross-origin from the problem entirely — no CORS preflight, no dependency on another host's headers, no third-party outage taking your dashboard down. The file ends up in `dist/` and is served same-origin, where you already control `Cache-Control`.

If you ever do fetch Parquet cross-origin from the browser, test both properties first — a host can support ranges and still not allow them cross-origin:

```bash
curl -sI -H "Origin: https://yoursite.netlify.app" -H "Range: bytes=0-1023" \
  https://huggingface.co/datasets/<user>/<repo>/resolve/main/prices.parquet \
  | grep -iE "^(HTTP|accept-ranges|content-range|access-control-allow-origin)"
```

You need a `206`, a `Content-Range`, **and** an `Access-Control-Allow-Origin` that covers your site. Missing the third is the failure that looks like a DuckDB bug and is not.

## The hybrid worth knowing

You do not have to choose one. Keep Netlify as the front door, because it is instant, and put the one genuinely interactive page on a Python host behind a link from it. Visitors get a fast first impression; the 5% who click through to the live model accept a few seconds of wake time, because by then they have decided they are interested.
