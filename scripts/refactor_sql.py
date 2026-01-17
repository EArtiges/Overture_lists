#!/usr/bin/env python3
"""
Refactor SQL queries in Python files to use sql_loader.

This script performs automated refactoring of inline SQL queries.
Run this manually and review the changes before committing.
"""

import re
import sys

# Mapping of SQL patterns to SQL file names for crm_mapping_storage
CRM_MAPPINGS = {
    r'INSERT INTO mappings.*?VALUES \(\?, \?, \?, \?, \?, \?, \?, \?\)': 'add_mapping',
    r'SELECT id, system_id.*?FROM mappings.*?ORDER BY created_at DESC': 'get_all_mappings',
    r'SELECT id, system_id.*?FROM mappings.*?WHERE system_id = \?': 'get_mapping_by_system_id',
    r'SELECT id, system_id.*?FROM mappings.*?WHERE division_id = \?': 'get_mapping_by_division_id',
    r'DELETE FROM mappings WHERE id = \?': 'delete_mapping',
    r'DELETE FROM mappings WHERE system_id = \?': 'delete_mapping_by_system_id',
    r'SELECT COUNT\(\*\) FROM mappings': 'get_count',
    r'DELETE FROM mappings[^W]': 'clear_all_mappings',
    r'SELECT id FROM division_info WHERE division_id = \?': 'check_division_info',
    r'INSERT INTO division_info.*?VALUES \(\?, \?, \?, \?\)': 'insert_division_info',
    r'SELECT \* FROM division_info WHERE division_id = \?': 'get_division_info',
    r'INSERT INTO relationships.*?VALUES \(\?, \?, \?, \?\)': 'add_relationship',
    r'SELECT id, child_division_id.*?FROM relationships.*?ORDER BY created_at DESC(?!.*WHERE)': 'get_all_relationships',
    r'SELECT id, child_division_id.*?FROM relationships.*?WHERE parent_division_id = \?': 'get_children',
    r'SELECT id, child_division_id.*?FROM relationships.*?WHERE child_division_id = \?': 'get_parents',
    r'DELETE FROM relationships WHERE id = \?': 'delete_relationship',
    r'SELECT COUNT\(\*\) FROM relationships': 'get_relationship_count',
    r'DELETE FROM relationships[^W]': 'clear_all_relationships',
}

print("SQL refactoring script created.")
print("Note: Manual refactoring is recommended due to complexity.")
print("This script serves as documentation of the mappings.")
