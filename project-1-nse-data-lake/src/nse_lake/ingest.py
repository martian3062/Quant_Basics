from __future__ import annotations

import argparse
import os
import re
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

from nse_lake.config import SETTINGS
from nse_lake.universe import source_symbols

IST = ZoneInfo("Asia/Kolkata")
NSE_CLOSE = time(15, 30)

PRICE_SCHEMA = {
    "symbol": pl.String,
    "source_symbol": pl.String,
    "date": pl.Date,
    "timestamp_utc": pl.Datetime("us", "UTC"),
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "adj_close": pl.Float64,
    "volume": pl.Int64,
    "dividends": pl.Float64,
    "stock_splits": pl.Float64,
    "ingested_at": pl.Datetime("us", "UTC"),
}


def canonical_symbol(source_symbol: str) -> str:
    aliases = {"^NSEI": "NIFTY50", "INR=X": "USDINR"}
    value = aliases.get(source_symbol.upper(), source_symbol.upper().removesuffix(".NS"))
    value = re.sub(r"[^A-Z0-9_-]+", "_", value).strip("_")
    if not value:
        raise ValueError(f"Cannot derive a canonical symbol from {source_symbol!r}")
    return value


def _session_date(value: object) -> date:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(IST).date()
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _nse_close_utc(session_date: date) -> datetime:
    return datetime.combine(session_date, NSE_CLOSE, tzinfo=IST).astimezone(UTC)


def normalize_yfinance_frame(raw: object, source_symbol: str) -> pl.DataFrame:
    """Convert a single-symbol yfinance DataFrame into the lake's stable schema."""
    if raw is None or getattr(raw, "empty", True):
        raise ValueError(f"Empty download for {source_symbol}; existing data was not touched")

    pandas_frame = raw.reset_index().copy()
    if getattr(pandas_frame.columns, "nlevels", 1) > 1:
        pandas_frame.columns = [
            next((str(part) for part in column if str(part) == "Date"), str(column[0]))
            if isinstance(column, tuple)
            else str(column)
            for column in pandas_frame.columns
        ]
    pandas_frame.columns = [
        re.sub(r"[^a-z0-9]+", "_", str(column).strip().casefold()).strip("_")
        for column in pandas_frame.columns
    ]

    date_column = "date" if "date" in pandas_frame.columns else "datetime"
    required = {date_column, "open", "high", "low", "close", "volume"}
    missing = required.difference(pandas_frame.columns)
    if missing:
        raise ValueError(f"{source_symbol} response is missing columns: {sorted(missing)}")

    session_dates = [_session_date(value) for value in pandas_frame[date_column].tolist()]
    row_count = len(session_dates)
    adj_close = (
        pandas_frame["adj_close"].tolist()
        if "adj_close" in pandas_frame.columns
        else pandas_frame["close"].tolist()
    )
    dividends = (
        pandas_frame["dividends"].fillna(0.0).tolist()
        if "dividends" in pandas_frame.columns
        else [0.0] * row_count
    )
    stock_splits = (
        pandas_frame["stock_splits"].fillna(0.0).tolist()
        if "stock_splits" in pandas_frame.columns
        else [0.0] * row_count
    )
    ingested_at = datetime.now(UTC)

    frame = pl.DataFrame(
        {
            "symbol": [canonical_symbol(source_symbol)] * row_count,
            "source_symbol": [source_symbol] * row_count,
            "date": session_dates,
            "timestamp_utc": [_nse_close_utc(value) for value in session_dates],
            "open": pandas_frame["open"].tolist(),
            "high": pandas_frame["high"].tolist(),
            "low": pandas_frame["low"].tolist(),
            "close": pandas_frame["close"].tolist(),
            "adj_close": adj_close,
            "volume": pandas_frame["volume"].fillna(0).tolist(),
            "dividends": dividends,
            "stock_splits": stock_splits,
            "ingested_at": [ingested_at] * row_count,
        },
        schema=PRICE_SCHEMA,
        strict=False,
    )
    return frame.sort("date")


def validate_prices(frame: pl.DataFrame) -> None:
    """Reject incomplete data before any existing Parquet is replaced."""
    if frame.is_empty():
        raise ValueError("Refusing to write an empty price frame")
    missing = set(PRICE_SCHEMA).difference(frame.columns)
    if missing:
        raise ValueError(f"Price frame is missing columns: {sorted(missing)}")
    if frame.select(pl.struct("symbol", "date").is_duplicated().any()).item():
        raise ValueError("Price frame contains duplicate (symbol, date) rows")
    float_columns = ("open", "high", "low", "close", "adj_close")
    invalid_number = pl.any_horizontal(
        *(pl.col(column).is_null() | ~pl.col(column).is_finite() for column in float_columns),
        pl.col("volume").is_null(),
    )
    if frame.select(invalid_number.any()).item():
        raise ValueError("Price frame contains null or non-finite OHLCV values")
    invalid_close = pl.any_horizontal(pl.col("close") <= 0, pl.col("adj_close") <= 0)
    if frame.select(invalid_close.any()).item():
        raise ValueError("Price frame contains non-positive close values")
    invalid_ohlc = frame.filter(
        (pl.col("high") < pl.max_horizontal("open", "close", "low"))
        | (pl.col("low") > pl.min_horizontal("open", "close", "high"))
        | (pl.col("volume") < 0)
    )
    if invalid_ohlc.height:
        raise ValueError(f"Price frame contains {invalid_ohlc.height} invalid OHLCV rows")


def write_symbol_parquet(frame: pl.DataFrame, prices_dir: Path) -> Path:
    """Atomically replace one valid symbol partition."""
    validate_prices(frame)
    symbols = frame.get_column("symbol").unique().to_list()
    if len(symbols) != 1:
        raise ValueError("Each partition write must contain exactly one symbol")

    partition_dir = prices_dir / f"symbol={symbols[0]}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    destination = partition_dir / "part-0.parquet"
    temporary = partition_dir / "part-0.parquet.tmp"
    try:
        frame.write_parquet(temporary, compression="zstd", statistics=True)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def download_symbol(source_symbol: str, start: date, end: date) -> pl.DataFrame:
    """Download both raw and adjusted daily values for one Yahoo Finance symbol."""
    import yfinance as yf

    raw = yf.download(
        source_symbol,
        start=start.isoformat(),
        end=end.isoformat(),
        interval="1d",
        actions=True,
        auto_adjust=False,
        repair=False,
        keepna=False,
        ignore_tz=False,
        progress=False,
        threads=False,
        multi_level_index=False,
        timeout=30,
    )
    return normalize_yfinance_frame(raw, source_symbol)


def ingest_symbols(
    symbols: list[str],
    *,
    start: date,
    end: date,
    prices_dir: Path,
) -> list[Path]:
    written: list[Path] = []
    failures: list[str] = []
    for source_symbol in symbols:
        try:
            frame = download_symbol(source_symbol, start, end)
            written.append(write_symbol_parquet(frame, prices_dir))
        except Exception as error:  # continue the batch, then fail it visibly
            failures.append(f"{source_symbol}: {error}")
    if failures:
        raise RuntimeError("Some symbols failed ingestion:\n" + "\n".join(failures))
    return written


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest NSE daily bars into Parquet")
    parser.add_argument("--start", type=date.fromisoformat, default=SETTINGS.start_date)
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today() + timedelta(days=1),
        help="Exclusive end date (defaults to tomorrow)",
    )
    parser.add_argument("--symbol", action="append", dest="symbols")
    parser.add_argument("--universe-file", type=Path)
    parser.add_argument("--data-dir", type=Path, default=SETTINGS.data_dir)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    symbols = args.symbols or source_symbols(args.universe_file)
    written = ingest_symbols(
        symbols,
        start=args.start,
        end=args.end,
        prices_dir=args.data_dir / "prices",
    )
    print(f"Wrote {len(written)} symbol partitions to {args.data_dir / 'prices'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
