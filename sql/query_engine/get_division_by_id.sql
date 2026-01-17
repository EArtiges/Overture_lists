SELECT
    id as division_id,
    names.primary as name,
    subtype,
    country
FROM read_parquet('{parquet_path}')
WHERE id = ?
LIMIT 1
