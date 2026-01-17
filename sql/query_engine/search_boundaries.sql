SELECT
    id as division_id,
    names.primary as name,
    subtype,
    country,
    parent_division_id
FROM read_parquet('{parquet_path}')
WHERE country = ?
  AND class = 'land'
  AND LOWER(names.primary) LIKE LOWER(?)
ORDER BY name
LIMIT 100
