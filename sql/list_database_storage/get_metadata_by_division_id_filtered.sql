SELECT * FROM division_metadata
WHERE division_id = ? AND metadata_type = ?
ORDER BY created_at DESC
