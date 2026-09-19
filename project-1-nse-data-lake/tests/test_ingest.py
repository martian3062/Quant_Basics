from datetime import UTC, date, datetime

import polars as pl
import pytest

from nse_lake.ingest import PRICE_SCHEMA, canonical_symbol, write_symbol_parquet


def valid_prices() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "symbol": ["TEST"],
            "source_symbol": ["TEST.NS"],
            "date": [date(2025, 1, 2)],
            "timestamp_utc": [datetime(2025, 1, 2, 10, tzinfo=UTC)],
            "open": [100.0],
            "high": [102.0],
            "low": [99.0],
            "close": [101.0],
            "adj_close": [101.0],
            "volume": [1000],
            "dividends": [0.0],
            "stock_splits": [0.0],
            "ingested_at": [datetime(2025, 1, 3, tzinfo=UTC)],
        },
        schema=PRICE_SCHEMA,
    )


def test_canonical_symbol_handles_market_aliases() -> None:
    assert canonical_symbol("RELIANCE.NS") == "RELIANCE"
    assert canonical_symbol("^NSEI") == "NIFTY50"
    assert canonical_symbol("INR=X") == "USDINR"


def test_empty_frame_never_replaces_existing_partition(tmp_path) -> None:
    destination = write_symbol_parquet(valid_prices(), tmp_path)
    original = destination.read_bytes()

    with pytest.raises(ValueError, match="empty"):
        write_symbol_parquet(pl.DataFrame(schema=PRICE_SCHEMA), tmp_path)

    assert destination.read_bytes() == original
