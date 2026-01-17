SELECT
    id as division_id,
    names.primary as name,
    subtype,
    country,
    parent_division_id
FROM read_parquet('{parquet_path}')
WHERE parent_division_id = ?
ORDER BY name
LIMIT 1000
