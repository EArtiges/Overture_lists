SELECT
    l.list_id,
    l.list_type,
    l.list_name,
    l.description,
    l.created_at,
    COUNT(i.id) as boundary_count
FROM list l
LEFT JOIN list_item i ON l.id = i.list_id
GROUP BY l.id
ORDER BY l.created_at DESC
