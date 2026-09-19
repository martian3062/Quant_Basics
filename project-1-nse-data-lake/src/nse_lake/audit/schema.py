from __future__ import annotations

from datetime import date

import polars as pl

FLAG_SCHEMA = {
    "symbol": pl.String,
    "date": pl.Date,
    "check_id": pl.String,
    "severity": pl.String,
    "detail": pl.String,
}


def flags_frame(rows: list[dict[str, str | date]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=FLAG_SCHEMA, strict=False)


def empty_flags() -> pl.DataFrame:
    return flags_frame([])
