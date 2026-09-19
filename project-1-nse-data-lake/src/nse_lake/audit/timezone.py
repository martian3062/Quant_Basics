from __future__ import annotations

from datetime import UTC
from zoneinfo import ZoneInfo

import polars as pl

from nse_lake.audit.schema import flags_frame

IST = ZoneInfo("Asia/Kolkata")


def audit_timestamps(prices: pl.DataFrame) -> pl.DataFrame:
    """Assert timestamps are UTC and resolve to the stored NSE session date in IST."""
    rows = []
    for row in prices.select("symbol", "date", "timestamp_utc").iter_rows(named=True):
        timestamp = row["timestamp_utc"]
        problems: list[str] = []
        if timestamp is None:
            problems.append("timestamp is null")
        else:
            offset = timestamp.utcoffset()
            if timestamp.tzinfo is None or offset != UTC.utcoffset(timestamp):
                problems.append("timestamp is not UTC")
            elif timestamp.astimezone(IST).date() != row["date"]:
                problems.append(
                    f"UTC timestamp maps to {timestamp.astimezone(IST).date()} in IST"
                )
        if problems:
            rows.append(
                {
                    "symbol": row["symbol"],
                    "date": row["date"],
                    "check_id": "timezone_alignment",
                    "severity": "serious",
                    "detail": "; ".join(problems),
                }
            )
    return flags_frame(rows)
