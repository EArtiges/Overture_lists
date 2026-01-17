SELECT DISTINCT country
FROM read_parquet('{parquet_path}')
WHERE country IS NOT NULL
ORDER BY country
