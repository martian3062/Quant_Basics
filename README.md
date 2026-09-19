# Quant Projects (Chapters 1–3)

Three projects built only on Chapters 1–3 (quant roles, probability and stochastic processes, time series, and the market data stack). Each uses a current 2026 tool. They are ordered so that each one feeds the next.

## Overview

| # | Project | Chapters used | 2026 trend it hits | Time |
|---|---|---|---|---|
| 1 | [NSE Data Lake + Bias Auditor](project-1-nse-data-lake-bias-auditor.md) | Ch 3 (data quality, storage) | uv + Polars + DuckDB + Parquet replacing pandas and CSV; Marimo notebooks | 1 weekend |
| 2 | [Stochastic Model Arena: GBM vs Jump vs Foundation Models](project-2-stochastic-model-arena.md) | Ch 2 (distributions, GBM, OU, Merton, GARCH, ADF) | Zero-shot time-series foundation models (TimesFM, Chronos) | 1–1.5 weeks |
| 3 | [Quant Research MCP Server](project-3-quant-research-mcp-server.md) | Ch 2 + 3, plus a light preview of Ch 13 | MCP as the standard way to plug tools into agents | 3–4 days |

## Suggested build order

| Week | Task | Done when |
|---|---|---|
| 1 | Project 1 | DuckDB query on 10 years of NIFTY 50 data runs in under 1 s, and the audit flags the known splits |
| 2–3 | Project 2 | Leaderboard is filled in and the GARCH vs Chronos result is written up |
| 3–4 | Project 3 | Claude answers 15 of 15 evaluation questions correctly through your tools |
| Then | Publish | One GitHub repo `quant-lab` with 3 folders, a README with results tables, and a portfolio entry |

> **Note:** All three are research and analysis only. Nothing places trades, which is the right boundary until Ch 7–8 (backtesting and execution).

# Quant_Basics
