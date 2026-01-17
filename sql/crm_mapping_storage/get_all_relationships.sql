SELECT id, child_division_id, parent_division_id,
       relationship_type, notes, created_at
FROM relationships
ORDER BY created_at DESC
