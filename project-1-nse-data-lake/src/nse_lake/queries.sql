-- Rolling 21-session annualized volatility per symbol.
WITH returns AS (
    SELECT
        symbol,
        date,
        ln(close / lag(close) OVER (PARTITION BY symbol ORDER BY date)) AS log_return
    FROM read_parquet('data/prices/symbol=*/part-*.parquet', hive_partitioning = true)
)
SELECT
    symbol,
    date,
    stddev_samp(log_return) OVER (
        PARTITION BY symbol
        ORDER BY date
        ROWS BETWEEN 20 PRECEDING AND CURRENT ROW
    ) * sqrt(252) AS volatility_21d
FROM returns
ORDER BY symbol, date;

-- Top 20 most volatile stocks in each calendar year.
WITH returns AS (
    SELECT
        symbol,
        date,
        ln(close / lag(close) OVER (PARTITION BY symbol ORDER BY date)) AS log_return
    FROM read_parquet('data/prices/symbol=*/part-*.parquet', hive_partitioning = true)
), annual AS (
    SELECT
        year(date) AS year,
        symbol,
        stddev_samp(log_return) * sqrt(252) AS annualized_volatility
    FROM returns
    GROUP BY year(date), symbol
), ranked AS (
    SELECT *, row_number() OVER (
        PARTITION BY year ORDER BY annualized_volatility DESC
    ) AS volatility_rank
    FROM annual
)
SELECT year, symbol, annualized_volatility, volatility_rank
FROM ranked
WHERE volatility_rank <= 20
ORDER BY year, volatility_rank;
