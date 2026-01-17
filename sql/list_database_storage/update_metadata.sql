UPDATE division_metadata
SET division_name = ?,
    division_subtype = ?,
    country = ?,
    account_name = ?,
    custom_admin_level = ?,
    geometry = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE id = ?
