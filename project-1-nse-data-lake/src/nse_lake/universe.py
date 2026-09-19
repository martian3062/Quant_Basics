from __future__ import annotations

import io
import time
import urllib.request
import warnings
from pathlib import Path

import polars as pl

from nse_lake.config import SETTINGS

NIFTY50_CSV_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"
EXTRA_MARKET_SYMBOLS = ("^NSEI", "INR=X")


def parse_nifty50_csv(content: bytes) -> pl.DataFrame:
    """Parse the official Nifty Indices constituent CSV into a stable schema."""
    raw = pl.read_csv(io.BytesIO(content))
    symbol_column = next(
        (column for column in raw.columns if column.strip().casefold() == "symbol"),
        None,
    )
    if symbol_column is None:
        raise ValueError("The constituent CSV has no Symbol column")

    result = (
        raw.select(pl.col(symbol_column).cast(pl.String).str.strip_chars().alias("symbol"))
        .filter(pl.col("symbol").is_not_null() & (pl.col("symbol") != ""))
        .unique(maintain_order=True)
        .with_columns((pl.col("symbol") + ".NS").alias("source_symbol"))
    )
    if result.height < 45:
        raise ValueError(f"Expected about 50 NIFTY constituents, received {result.height}")
    return result


def fetch_current_nifty50(
    *,
    url: str = NIFTY50_CSV_URL,
    timeout_seconds: float = 30,
    attempts: int = 3,
) -> pl.DataFrame:
    """Fetch current constituents from the official Nifty Indices download."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    headers = {
        "Accept": "text/csv,*/*;q=0.8",
        "Referer": "https://www.niftyindices.com/indices/equity/broad-based-indices/nifty--50",
        "User-Agent": "Mozilla/5.0 (compatible; nse-lake/0.1)",
    }
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                return parse_nifty50_csv(response.read())
        except (OSError, TimeoutError, ValueError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    message = f"Nifty constituent download failed after {attempts} attempts"
    raise RuntimeError(message) from last_error


def load_universe(path: Path | None = None) -> pl.DataFrame:
    """Load a saved universe, or fetch the current official NIFTY 50 universe."""
    if path is None:
        try:
            return fetch_current_nifty50()
        except RuntimeError as error:
            path = SETTINGS.data_dir / "universe_current.csv"
            if not path.exists():
                raise
            warnings.warn(
                f"{error}; using cached constituent snapshot at {path}",
                RuntimeWarning,
                stacklevel=2,
            )
    frame = pl.read_csv(path)
    if "source_symbol" not in frame.columns:
        if "symbol" not in frame.columns:
            raise ValueError("Universe file must contain symbol or source_symbol")
        frame = frame.with_columns((pl.col("symbol") + ".NS").alias("source_symbol"))
    return frame.select("symbol", "source_symbol").unique(maintain_order=True)


def source_symbols(path: Path | None = None, include_market_series: bool = True) -> list[str]:
    symbols = load_universe(path).get_column("source_symbol").to_list()
    if include_market_series:
        symbols.extend(EXTRA_MARKET_SYMBOLS)
    return symbols
