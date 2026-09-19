from nse_lake.universe import parse_nifty50_csv


def test_parse_nifty50_csv_builds_yahoo_symbols() -> None:
    rows = ["Company Name,Industry,Symbol,Series,ISIN Code"]
    rows.extend(f"Company {index},Industry,SYM{index},EQ,INE{index}" for index in range(50))

    result = parse_nifty50_csv(("\n".join(rows) + "\n").encode())

    assert result.height == 50
    assert result.row(0, named=True) == {"symbol": "SYM0", "source_symbol": "SYM0.NS"}
