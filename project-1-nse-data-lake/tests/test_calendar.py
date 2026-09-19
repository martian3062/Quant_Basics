from datetime import date

import polars as pl
import pytest

from nse_lake.calendar import observed_nse_sessions


def test_observed_sessions_come_from_benchmark_rows() -> None:
    prices = pl.DataFrame(
        {
            "symbol": ["NIFTY50", "NIFTY50", "TEST"],
            "date": [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 2)],
        }
    )

    assert observed_nse_sessions(prices) == [date(2025, 1, 2), date(2025, 1, 3)]


def test_observed_sessions_require_benchmark() -> None:
    prices = pl.DataFrame({"symbol": ["TEST"], "date": [date(2025, 1, 2)]})

    with pytest.raises(ValueError, match=r"ingest \^NSEI"):
        observed_nse_sessions(prices)
