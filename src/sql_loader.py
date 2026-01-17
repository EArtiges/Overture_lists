"""
SQL Loader Utility

Helper functions to load SQL queries from .sql files.
"""

import os
from typing import Dict

# Cache for loaded SQL queries
_sql_cache: Dict[str, str] = {}


def load_sql(module_name: str, query_name: str) -> str:
    """
    Load SQL query from file.

    Args:
        module_name: Name of the module (e.g., 'crm_mapping_storage', 'list_database_storage')
        query_name: Name of the query file without .sql extension (e.g., 'init_schema', 'insert_mapping')

    Returns:
        SQL query string

    Raises:
        FileNotFoundError: If SQL file doesn't exist
    """
    cache_key = f"{module_name}/{query_name}"

    # Return cached query if available
    if cache_key in _sql_cache:
        return _sql_cache[cache_key]

    # Build path to SQL file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql_file_path = os.path.join(base_dir, 'sql', module_name, f'{query_name}.sql')

    # Load SQL from file
    if not os.path.exists(sql_file_path):
        raise FileNotFoundError(f"SQL file not found: {sql_file_path}")

    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Cache the query
    _sql_cache[cache_key] = sql

    return sql


def clear_cache():
    """Clear the SQL query cache. Useful for testing or hot-reloading."""
    _sql_cache.clear()
