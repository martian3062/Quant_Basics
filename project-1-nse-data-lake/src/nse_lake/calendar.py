from __future__ import annotations

from datetime import date

import polars as pl


def observed_nse_sessions(
    prices: pl.DataFrame,
    *,
    benchmark_symbol: str = "NIFTY50",
) -> list[date]:
    """Use published NIFTY 50 index bars as evidence that NSE held a session.

    ``exchange_calendars`` does not currently register an XNSE calendar. The benchmark
    series is therefore the safest source already present in the lake: a benchmark bar
    proves the exchange held a session without pretending the XBOM calendar is identical.
    """
    if benchmark_symbol not in prices.get_column("symbol").unique().to_list():
        raise ValueError(
            f"Missing {benchmark_symbol} benchmark partition; ingest ^NSEI before auditing "
            "missing sessions"
        )
    return (
        prices.filter(pl.col("symbol") == benchmark_symbol)
        .get_column("date")
        .drop_nulls()
        .unique()
        .sort()
        .to_list()
    )
