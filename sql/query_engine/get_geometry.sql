SELECT
    ST_AsGeoJSON(ST_Simplify(geometry, 0.001)) as geojson,
    division_id
FROM read_parquet('{area_path}')
WHERE division_id = ?
LIMIT 1
