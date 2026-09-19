from datetime import UTC, date, datetime, timedelta

import polars as pl

from nse_lake.audit.bad_ticks import audit_bad_ticks
from nse_lake.audit.missing import audit_missing_sessions
from nse_lake.audit.splits import audit_adjustment_gaps
from nse_lake.audit.timezone import audit_timestamps


def price_frame(
    closes: list[float],
    *,
    adjusted: list[float] | None = None,
    dates: list[date] | None = None,
) -> pl.DataFrame:
    start = date(2025, 1, 1)
    dates = dates or [start + timedelta(days=index) for index in range(len(closes))]
    adjusted = adjusted or closes
    return pl.DataFrame(
        {
            "symbol": ["TEST"] * len(closes),
            "date": dates,
            "timestamp_utc": [
                datetime.combine(value, datetime.min.time(), tzinfo=UTC)
                + timedelta(hours=10)
                for value in dates
            ],
            "close": closes,
            "adj_close": adjusted,
            "stock_splits": [0.0] * len(closes),
        }
    )


def test_adjustment_gap_finds_ratio_step() -> None:
    prices = price_frame([100, 102, 52, 53], adjusted=[50, 51, 52, 53])

    flags = audit_adjustment_gaps(prices)

    assert flags.height == 1
    assert flags.row(0, named=True)["date"] == date(2025, 1, 3)
    assert flags.row(0, named=True)["check_id"] == "adjustment_gap"


def test_bad_tick_requires_extreme_move_and_reversal() -> None:
    closes = [100.0, 101.0, 100.5, 101.5, 101.0, 102.0, 250.0, 103.0]
    prices = price_frame(closes)

    flags = audit_bad_ticks(
        prices,
        sigma_threshold=4.0,
        lookback=5,
        min_samples=4,
        reversal_fraction=0.5,
    )

    assert flags.height == 1
    assert flags.row(0, named=True)["date"] == date(2025, 1, 7)


def test_missing_session_uses_explicit_calendar() -> None:
    sessions = [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)]
    prices = price_frame([100.0, 102.0], dates=[sessions[0], sessions[2]])

    flags = audit_missing_sessions(prices, sessions)

    assert flags.height == 1
    assert flags.row(0, named=True)["date"] == sessions[1]


def test_timezone_audit_finds_off_by_one_ist_date() -> None:
    prices = price_frame([100.0])
    prices = prices.with_columns(
        pl.lit(datetime(2025, 1, 1, 20, tzinfo=UTC)).alias("timestamp_utc")
    )

    flags = audit_timestamps(prices)

    assert flags.height == 1
    assert flags.row(0, named=True)["check_id"] == "timezone_alignment"
