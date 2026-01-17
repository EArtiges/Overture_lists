SELECT id, system_id, account_name, custom_admin_level,
       division_id, division_name, overture_subtype, country,
       geometry, created_at, updated_at
FROM mappings
WHERE system_id = ?
