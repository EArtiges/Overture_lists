SELECT
    id as division_id,
    names.primary as name
FROM read_parquet('{parquet_path}')
WHERE country = ?
  AND subtype = 'country'
LIMIT 1
