from __future__ import annotations

import argparse
import os
from pathlib import Path

import polars as pl

from nse_lake.audit.bad_ticks import audit_bad_ticks
from nse_lake.audit.missing import audit_missing_sessions
from nse_lake.audit.schema import empty_flags
from nse_lake.audit.splits import audit_adjustment_gaps
from nse_lake.audit.timezone import audit_timestamps
from nse_lake.calendar import observed_nse_sessions
from nse_lake.config import SETTINGS


def load_prices(prices_dir: Path) -> pl.DataFrame:
    files = sorted(prices_dir.glob("symbol=*/part-*.parquet"))
    if not files:
        raise FileNotFoundError(f"No price partitions found below {prices_dir}")
    return pl.concat([pl.read_parquet(path) for path in files], how="vertical_relaxed")


def run_audits(prices: pl.DataFrame) -> pl.DataFrame:
    if prices.is_empty():
        return empty_flags()
    expected_sessions = observed_nse_sessions(prices)
    frames = [
        audit_adjustment_gaps(prices),
        audit_bad_ticks(prices),
        audit_missing_sessions(prices, expected_sessions),
        audit_timestamps(prices),
    ]
    return pl.concat(frames, how="vertical").sort("date", "symbol", "check_id")


def write_audit_flags(flags: pl.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        flags.write_parquet(temporary, compression="zstd", statistics=True)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NSE lake data-quality audits")
    parser.add_argument("--data-dir", type=Path, default=SETTINGS.data_dir)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    prices = load_prices(args.data_dir / "prices")
    flags = run_audits(prices)
    destination = args.data_dir / "audit_flags.parquet"
    write_audit_flags(flags, destination)
    print(f"Wrote {flags.height} audit flags to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
