SELECT
    m.division_id,
    m.division_name,
    m.division_subtype,
    m.country,
    m.system_id,
    m.account_name,
    m.custom_admin_level,
    m.geometry,
    m.metadata_type
FROM list_item i
JOIN division_metadata m ON i.metadata_id = m.id
WHERE i.list_id = ?
ORDER BY i.item_order
