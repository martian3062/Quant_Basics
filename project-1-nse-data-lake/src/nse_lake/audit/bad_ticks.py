from __future__ import annotations

import polars as pl

from nse_lake.audit.schema import flags_frame


def audit_bad_ticks(
    prices: pl.DataFrame,
    *,
    sigma_threshold: float = 6.0,
    lookback: int = 60,
    min_samples: int = 20,
    reversal_fraction: float = 0.50,
) -> pl.DataFrame:
    """Flag extreme daily moves followed by a large opposite-direction reversal."""
    ordered = prices.sort("symbol", "date").with_columns(
        (pl.col("close") / pl.col("close").shift(1).over("symbol"))
        .log()
        .alias("_return")
    )
    candidates = (
        ordered.with_columns(
            pl.col("_return")
            .shift(1)
            .rolling_std(window_size=lookback, min_samples=min_samples)
            .over("symbol")
            .alias("_sigma"),
            pl.col("_return").shift(-1).over("symbol").alias("_next_return"),
        )
        .filter(
            (pl.col("_sigma") > 0)
            & (pl.col("_return").abs() > sigma_threshold * pl.col("_sigma"))
            & (pl.col("_return") * pl.col("_next_return") < 0)
            & (pl.col("_next_return").abs() >= reversal_fraction * pl.col("_return").abs())
        )
        .select("symbol", "date", "_return", "_sigma", "_next_return")
    )

    rows = []
    for row in candidates.iter_rows(named=True):
        z_score = abs(float(row["_return"])) / float(row["_sigma"])
        rows.append(
            {
                "symbol": row["symbol"],
                "date": row["date"],
                "check_id": "bad_tick_reversal",
                "severity": "critical" if z_score >= 10 else "serious",
                "detail": (
                    f"Return {row['_return']:+.2%} was {z_score:.1f} sigma and next session "
                    f"reversed {row['_next_return']:+.2%}"
                ),
            }
        )
    return flags_frame(rows)
