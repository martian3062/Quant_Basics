# Project 1: NSE Data Lake + Bias Auditor

**Chapters used:** Ch 3 (data quality, storage)
**2026 trend:** uv + Polars + DuckDB + Parquet replacing pandas and CSV; Marimo notebooks
**Time:** 1 weekend (2–3 more days if you ship the live site)
**Live target:** static site on Netlify, no backend

## Idea

Build a small, correct Indian-equities database, and a tool that finds the data problems from Ch 3.3 instead of hiding them.

## Scope

| Item | Detail |
|---|---|
| Universe | Current NIFTY 50 stocks (RELIANCE.NS etc. via yfinance), 2015 to today, plus NIFTY index, USD/INR, and one macro series from FRED |
| Stack | `uv` project → yfinance → Polars → Parquet (hive-partitioned by symbol) → DuckDB → Marimo locally, Observable Framework for the deployed site |
| Deploy | GitHub Actions runs the Python nightly; Netlify serves a static site that queries the Parquet in-browser with DuckDB-WASM |

No server anywhere — the whole data lake is a few MB of Parquet, so it ships as static files.

| Doc | What it covers |
|---|---|
| [STACK.md](STACK.md) | Architecture, why each tool, `netlify.toml`, the Actions workflow, gotchas, and host alternatives |
| [DATA_SOURCES.md](DATA_SOURCES.md) | ~30 live APIs — prices, corporate actions, calendars, index constituents, macro |
| [FRONTEND.md](FRONTEND.md) | Design spec — validated palette, chart forms, mark specs, and the red/green colorblindness trap |

## Build status

The first end-to-end slice is working:

- `uv` package with a locked Python 3.13 environment
- official NIFTY 50 constituent download with a committed 50-symbol fallback snapshot
- explicit raw and adjusted Yahoo Finance ingestion (`auto_adjust=False`)
- atomic hive-partitioned Parquet writes that never replace good data with an empty response
- adjustment-gap, bad-tick reversal, missing-session, and UTC/IST alignment audits
- DuckDB SQL for rolling and annual volatility
- synthetic tests plus a live RELIANCE adapter smoke test
- a responsive Observable Framework dashboard with filters, KPI cards, an interactive
  survivorship comparison, and an issue table
- a deterministic JSON exporter that lets the static frontend build without network access

The dashboard currently ships an explicitly labelled prototype survivorship series and sample audit
flags. The next slice is historical constituent membership, wiring those results into the exporter,
and the Marimo notebook.

## Run the current slice

```powershell
cd project-1-nse-data-lake
python -m pip install uv
python -m uv sync --all-groups

# Fast confidence check; no network required.
python -m uv run ruff check .
python -m uv run pytest

# Small live ingest first. The --end date is exclusive.
python -m uv run nse-lake-ingest `
  --symbol RELIANCE.NS --symbol ^NSEI `
  --start 2025-01-01 --end 2025-02-01
python -m uv run nse-lake-audit

# Regenerate the dashboard snapshot, then launch its local dev server.
python -m uv run nse-lake-site-data
Set-Location site
npm ci
npm run dev
```

Running `nse-lake-ingest` without `--symbol` targets the current NIFTY 50, the NIFTY 50 index,
and USD/INR. The official constituent endpoint is retried and falls back to
`data/universe_current.csv` when unavailable.

`exchange_calendars` does not currently expose the `XNSE` calendar named in the original plan.
For now, the missing-session audit treats each published `^NSEI` bar as proof that NSE held a
session and checks every constituent against those dates. This is stricter than substituting the
Bombay exchange calendar, but cannot detect a date missing from every Yahoo series; an official
NSE holiday snapshot will close that final gap.

## Checks to build

1. **Adjusted vs unadjusted gap:** flag days where the ratio jumps (splits and bonuses, e.g. RELIANCE's 2017 bonus).
2. **Bad ticks:** returns beyond 6σ with a same-day reversal.
3. **Missing days:** compare against the NSE trading calendar.
4. **Timezone:** store UTC, display IST, and assert no off-by-a-day bars.
5. **Survivorship:** list stocks that entered or left NIFTY 50 since 2015 and show how "today's constituents" inflates backtest returns.

Each check writes one row per `(symbol, date, check_id, severity, detail)` into a single `audit_flags.parquet`. One table, one schema — that is what makes the dashboard and the Project 3 `data_issues` tool trivial.

## Key SQL

Run directly on Parquet in DuckDB:

- Rolling daily volatility per symbol
- Top-20 most volatile stocks per year

## Deliverable

Two faces on the same data:

| Face | Tool | Audience |
|---|---|---|
| `notebooks/data_audit.py` | Marimo, local | you, while building |
| `site/` → `nse-audit.netlify.app` | Observable Framework, static | the portfolio link on your CV |

Both show: a table of flagged issues per symbol, and a chart of survivorship-biased vs honest equal-weight returns.

## Stretch

- Add the free NSE bhavcopy as a second source and reconcile vendor vs exchange close prices (the vendor restatement issue).
- Nightly audit digest emailed or posted to Discord when a new flag appears.

## Done when

- A DuckDB query on 10 years of NIFTY 50 data runs in under 1 s.
- The audit flags the known splits.
- The Netlify URL loads in under 3 s on a cold cache and the charts are interactive.

## Why it matters

Every later project, including backtests in Ch 7, reads from this store. It also answers the question interviewers ask most often: "how do you know your data is clean?" — and now you can answer it with a link.

## Feeds into

- [Project 2](../project-2-stochastic-model-arena.md): uses the cleaned NIFTY series
- [Project 3](../project-3-quant-research-mcp-server.md): `get_prices` and `data_issues` are backed by this store
