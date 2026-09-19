from __future__ import annotations

import polars as pl

from nse_lake.audit.schema import flags_frame


def audit_adjustment_gaps(
    prices: pl.DataFrame,
    *,
    jump_threshold: float = 0.10,
) -> pl.DataFrame:
    """Flag jumps in adjusted/raw close ratio that suggest a split or bonus."""
    candidates = (
        prices.sort("symbol", "date")
        .with_columns((pl.col("adj_close") / pl.col("close")).alias("_ratio"))
        .with_columns(
            (pl.col("_ratio") / pl.col("_ratio").shift(1).over("symbol") - 1).alias(
                "_ratio_jump"
            )
        )
        .filter(pl.col("_ratio_jump").abs() >= jump_threshold)
        .select("symbol", "date", "_ratio", "_ratio_jump", "stock_splits")
    )

    rows = []
    for row in candidates.iter_rows(named=True):
        jump = float(row["_ratio_jump"])
        reported_split = float(row["stock_splits"] or 0.0)
        severity = "critical" if abs(jump) >= 0.40 else "serious"
        rows.append(
            {
                "symbol": row["symbol"],
                "date": row["date"],
                "check_id": "adjustment_gap",
                "severity": severity,
                "detail": (
                    f"Adjusted/raw ratio moved {jump:+.1%} to {row['_ratio']:.6f}; "
                    f"vendor split field={reported_split:g}"
                ),
            }
        )
    return flags_frame(rows)
