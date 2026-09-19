from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from nse_lake.config import SETTINGS

DEMO_FLAGS = [
    (
        "RELIANCE",
        "2017-09-07",
        "adjustment_gap",
        "critical",
        "Adjusted/raw ratio moved +100.0%; known 1:1 bonus event.",
    ),
    (
        "TCS",
        "2018-06-01",
        "adjustment_gap",
        "critical",
        "Adjusted/raw ratio moved +100.0%; known 1:1 bonus event.",
    ),
    (
        "INFY",
        "2020-03-23",
        "bad_tick_reversal",
        "serious",
        "Return was 7.2 sigma and reversed 6.4% next session.",
    ),
    (
        "HDFCBANK",
        "2024-01-22",
        "missing_session",
        "warning",
        "No bar on an observed NIFTY 50 trading session.",
    ),
    (
        "ICICIBANK",
        "2021-02-24",
        "timezone_alignment",
        "serious",
        "UTC timestamp mapped to the following IST session date.",
    ),
    (
        "SBIN",
        "2020-03-13",
        "bad_tick_reversal",
        "critical",
        "Return was 10.8 sigma and reversed 13.9% next session.",
    ),
    (
        "MARUTI",
        "2022-10-24",
        "missing_session",
        "warning",
        "Muhurat-session bar absent from the vendor response.",
    ),
    (
        "TATASTEEL",
        "2022-07-28",
        "adjustment_gap",
        "critical",
        "Adjusted/raw ratio moved +900.0%; known 10:1 split.",
    ),
    (
        "WIPRO",
        "2019-03-06",
        "adjustment_gap",
        "serious",
        "Ratio step aligns with the vendor bonus field.",
    ),
    (
        "BHARTIARTL",
        "2020-04-07",
        "bad_tick_reversal",
        "serious",
        "Return was 6.7 sigma and reversed 5.1% next session.",
    ),
    (
        "NESTLEIND",
        "2024-01-05",
        "adjustment_gap",
        "critical",
        "Adjusted/raw ratio moved +900.0%; known 10:1 split.",
    ),
    (
        "ASIANPAINT",
        "2016-11-14",
        "missing_session",
        "warning",
        "No daily bar on an observed benchmark session.",
    ),
]

DEMO_VOLATILITY = {
    2024: [
        ("ADANIENT", 0.421),
        ("TATASTEEL", 0.319),
        ("INDIGO", 0.304),
        ("TRENT", 0.291),
        ("ADANIPORTS", 0.278),
        ("BEL", 0.265),
        ("HINDALCO", 0.254),
        ("ETERNAL", 0.249),
        ("BAJFINANCE", 0.238),
        ("SBIN", 0.229),
    ],
    2025: [
        ("ADANIENT", 0.386),
        ("INDIGO", 0.331),
        ("ETERNAL", 0.318),
        ("BEL", 0.297),
        ("TATASTEEL", 0.282),
        ("TRENT", 0.276),
        ("JIOFIN", 0.268),
        ("HINDALCO", 0.251),
        ("BAJFINANCE", 0.244),
        ("SHRIRAMFIN", 0.235),
    ],
    2026: [
        ("ETERNAL", 0.354),
        ("INDIGO", 0.326),
        ("ADANIENT", 0.311),
        ("BEL", 0.293),
        ("TMPV", 0.287),
        ("TATASTEEL", 0.271),
        ("TRENT", 0.264),
        ("HINDALCO", 0.252),
        ("JIOFIN", 0.248),
        ("SHRIRAMFIN", 0.239),
    ],
}


def _month_range(start: date, end: date) -> list[date]:
    values: list[date] = []
    current = start
    while current <= end:
        values.append(current)
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return values


def _survivorship_series() -> tuple[list[dict[str, str | float]], float, float]:
    months = _month_range(date(2015, 1, 1), date(2026, 8, 1))
    biased = 100.0
    honest = 100.0
    rows: list[dict[str, str | float]] = []
    for index, month in enumerate(months):
        if index:
            common_cycle = 0.011 * math.sin(index * 0.71) + 0.006 * math.cos(index * 0.19)
            biased *= 1 + (1.148 ** (1 / 12) - 1) + common_cycle
            honest *= 1 + (1.109 ** (1 / 12) - 1) + common_cycle * 0.86
        rows.extend(
            [
                {
                    "date": month.isoformat(),
                    "series": "Today's constituents",
                    "index": round(biased, 2),
                },
                {"date": month.isoformat(), "series": "Point-in-time", "index": round(honest, 2)},
            ]
        )
    years = (months[-1].year - months[0].year) + (months[-1].month - months[0].month) / 12
    biased_cagr = (biased / 100) ** (1 / years) - 1
    honest_cagr = (honest / 100) ** (1 / years) - 1
    return rows, biased_cagr, honest_cagr


def build_demo_payload(generated_at: datetime | None = None) -> dict[str, object]:
    generated_at = generated_at or datetime.now(UTC)
    survivorship, biased_cagr, honest_cagr = _survivorship_series()
    flags = [
        {
            "symbol": symbol,
            "date": flag_date,
            "check_id": check_id,
            "severity": severity,
            "detail": detail,
        }
        for symbol, flag_date, check_id, severity, detail in DEMO_FLAGS
    ]
    counts = Counter(flag["severity"] for flag in flags)
    volatility = [
        {"year": year, "symbol": symbol, "annualized_volatility": value}
        for year, values in DEMO_VOLATILITY.items()
        for symbol, value in values
    ]
    coverage = [
        {"symbol": symbol, "expected": 2862, "observed": 2862 - missing, "missing": missing}
        for symbol, missing in [
            ("RELIANCE", 0),
            ("TCS", 0),
            ("INFY", 1),
            ("HDFCBANK", 1),
            ("ICICIBANK", 0),
            ("SBIN", 0),
            ("MARUTI", 1),
            ("TATASTEEL", 0),
        ]
    ]
    return {
        "meta": {
            "is_demo": True,
            "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
            "period_start": "2015-01-01",
            "period_end": "2026-08-31",
            "source_note": "Illustrative frontend dataset; replace after the full lake refresh.",
        },
        "hero": {
            "bias_percentage_points": round((biased_cagr - honest_cagr) * 100, 1),
            "biased_cagr": round(biased_cagr * 100, 1),
            "honest_cagr": round(honest_cagr * 100, 1),
        },
        "kpis": {
            "symbols_audited": 50,
            "trading_days": 2862,
            "flags": len(flags),
            "critical_flags": counts["critical"],
        },
        "survivorship": survivorship,
        "flags": flags,
        "severity_summary": [
            {"severity": severity, "count": counts[severity]}
            for severity in ("critical", "serious", "warning")
        ],
        "volatility": volatility,
        "coverage": coverage,
    }


def write_payload(output: Path, payload: dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_output = SETTINGS.project_root / "site" / "src" / "data" / "dashboard.json"
    parser = argparse.ArgumentParser(description="Build the static dashboard data snapshot")
    parser.add_argument("--output", type=Path, default=default_output)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    write_payload(args.output, build_demo_payload())
    print(f"Wrote illustrative dashboard snapshot to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
