# Live APIs and services to integrate

Quotas and prices move. Everything below was true as far as I know, but check the current page before you depend on a number.

## Shortlist: most value for least effort

If you only add four things beyond yfinance, add these.

| Add | Why it is the highest-value one |
|---|---|
| **`exchange_calendars`** (`XNSE`) | Check 3 is unfalsifiable without a real trading calendar. It is a pip install, not an API. Do this first. |
| **NSE bhavcopy** | Free, official, daily. It turns check 1 from "flag a suspicious ratio" into "prove the vendor is wrong against the exchange". This is the single thing that makes the project look professional. |
| **FRED** | Free key, instant, and gives you the macro series the spec already asks for. |
| **Hugging Face Datasets** | Free Parquet hosting with HTTP range support, so the site can query data that outgrows git. |

## 1. Price history

| Source | Coverage | Auth | Cost | Notes |
|---|---|---|---|---|
| **yfinance** | NSE via `.NS`, daily back to ~1996 | none | free | Your baseline. Unofficial, rate-limited, occasionally returns empty frames. Never trust it as the only source. |
| **NSE bhavcopy** | official daily OHLCV, all listed scrips | none | free | Downloadable ZIP/CSV per day from NSE archives. The exchange's own print. Use as the reconciliation source. Be polite with request rates and set a browser-like UA. |
| **Upstox API** | historical candles, daily + intraday | account + OAuth | free tier | Cleanest of the free Indian broker APIs. Read-only endpoints are all you need. |
| **Angel One SmartAPI** | historical candles | account + key | free | Generous limits, well documented. |
| **Dhan / Fyers** | historical candles | account + key | free tier | Both fine; pick whichever broker you already have. |
| **Zerodha Kite Connect** | historical candles | account + paid subscription | paid, ~₹2k/mo range — verify | Best data quality of the broker APIs. Not worth it at this stage. |
| **Alpha Vantage** | NSE daily, adjusted | free key | free tier, low daily cap | Useful as a third opinion on split adjustment, too slow for bulk. |
| **Twelve Data** | NSE daily | free key | free tier | Same role as Alpha Vantage, a bit more generous. |
| **EODHD** | India + **corporate actions** | key | paid | The paid one actually worth it *if* you ever want clean splits/bonuses/dividends handed to you instead of inferred. |

**Recommendation:** yfinance as primary, bhavcopy as the truth source for reconciliation, one broker API (Upstox) as a free third opinion. Three sources is enough to make disagreement visible, which is the entire point of the project.

## 2. Corporate actions — the one that makes check 1 real

Check 1 currently *infers* splits and bonuses from a jump in the adjusted/unadjusted ratio. Getting an actual corporate-actions feed turns inference into verification, and lets you report precision and recall on your own detector. That is a much stronger portfolio result.

| Source | Cost | Notes |
|---|---|---|
| **NSE corporate actions** (equities → corporate actions) | free | Official, downloadable. Splits, bonuses, dividends, with ex-dates. |
| **BSE corporate actions** | free | Second source; cross-check ex-dates. |
| `yfinance` `.actions` / `.splits` | free | Convenient, but it is the same vendor you are auditing, so it cannot referee itself. |
| **Financial Modeling Prep** | free tier | Splits and dividends calendar, decent India coverage. |
| **EODHD** | paid | The most complete if you want to stop fighting this. |

Build it as: detector → NSE corporate-actions list → confusion matrix. "My 6σ detector caught 23 of 25 real corporate actions with 3 false positives" is a sentence that gets you an interview.

## 3. Trading calendar

| Source | Notes |
|---|---|
| **`exchange_calendars`** — `XNSE` | The right answer. Holidays, half-days, session times, historical changes. |
| `pandas_market_calendars` | Wraps the same data; use whichever API you prefer. |
| NSE holiday circular page | Free, and the authority when the library lags a newly announced holiday. |

## 4. Index constituents — the survivorship check

This is the hardest free data to get, and it is what makes check 5 honest.

| Source | Notes |
|---|---|
| **niftyindices.com** | Official. Current constituents as CSV, plus index-reconstitution press releases going back years. The releases are the primary record of who entered and left. |
| **NSE index circulars** | The announcements themselves, with effective dates. |
| **Wikipedia page history for "NIFTY 50"** | An underrated free hack: the article's revision history is a crowd-maintained time series of constituents. Scrape revisions via the MediaWiki API, take the table at each date. Not authoritative, but excellent for bootstrapping, and easy to reconcile against the official circulars afterwards. |

Semi-annual reconstitution means roughly 40–60 changes since 2015. Getting this right is a few hours of careful work and is the part of the project nobody else's portfolio has.

## 5. Macro and FX

| Source | Auth | Notes |
|---|---|---|
| **FRED** | free key | India CPI, policy rate, INR/USD. The spec's macro series. `fredapi` or plain REST. |
| **data.gov.in** | free key | Official Indian government datasets — CPI, IIP, and more. |
| **World Bank API** | none | No key at all, good for annual series. |
| **RBI DBIE** | none | Authoritative Indian macro, but the site is awkward; scrape carefully. |
| **exchangerate.host / Frankfurter** | none | Free daily FX if you want USD/INR without a key. |

## 6. Infrastructure APIs worth wiring in

These are what make it a *product* rather than a notebook.

| Service | Role | Free tier | Worth it? |
|---|---|---|---|
| **GitHub Actions** | the nightly scheduler | yes | Essential. This is your cron. |
| **Netlify** | static host, deploy previews | yes | Already decided. |
| **Hugging Face Datasets** | Parquet hosting, HTTP range reads, auto DuckDB endpoint | yes | **Yes** — the natural home once `data/` outgrows git, and a public dataset is itself a portfolio artifact. |
| **Cloudflare R2** | object store, zero egress fees | 10 GB-ish | Yes, if you go intraday later. S3 API, DuckDB reads it directly. |
| **MotherDuck** | hosted DuckDB, shareable databases | yes | Nice-to-have. Lets you share a live query endpoint and connect from DuckDB-WASM. Do it after the static version works. |
| **Resend** | email the nightly audit digest | ~3k emails/mo | Yes — 20 lines, and "it emails me when the data breaks" is a real ops story. |
| **Discord / Slack webhook** | post new audit flags | free | Cheaper than Resend and even faster to build. Pick one, not both. |
| **Sentry** | catch build/loader failures | yes | Optional. |
| **Upstash Redis** | cache for a Netlify function | yes | Skip it. You have no functions. |
| **Neon / Supabase** | hosted Postgres | yes | **Skip.** You have Parquet and DuckDB. Adding Postgres here is strictly worse. |

## What to deliberately skip

- **Any paid data feed**, until you have hit a wall the free sources cannot get past. You have not.
- **A real-time websocket feed.** The project is daily bars. Live ticks add operational pain and zero marks.
- **Postgres, or any OLTP database.** Wrong shape for this workload.
- **A backend API of your own.** The whole point of the architecture in [STACK.md](STACK.md) is that you do not need one.

## Credential hygiene

Every key above goes in one place: GitHub Actions secrets, read via `os.environ`. Never in `.env` committed, never in the Netlify build, never in the Parquet, never in the browser bundle. The site is static — it ships to the public, so anything the client can read is public. All the authenticated calls happen in Actions, and only their *output* is published.
