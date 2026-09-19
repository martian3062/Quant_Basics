from __future__ import annotations

from collections.abc import Iterable
from datetime import date

import polars as pl

from nse_lake.audit.schema import flags_frame


def audit_missing_sessions(
    prices: pl.DataFrame,
    expected_sessions: Iterable[date],
) -> pl.DataFrame:
    """Flag absent rows against an explicit exchange-session calendar."""
    expected = set(expected_sessions)
    rows = []
    for symbol in prices.get_column("symbol").unique(maintain_order=True).to_list():
        actual = set(
            prices.filter(pl.col("symbol") == symbol).get_column("date").drop_nulls().to_list()
        )
        for missing_date in sorted(expected.difference(actual)):
            rows.append(
                {
                    "symbol": symbol,
                    "date": missing_date,
                    "check_id": "missing_session",
                    "severity": "warning",
                    "detail": "No daily bar for an expected XNSE trading session",
                }
            )
    return flags_frame(rows)
