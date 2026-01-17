# SQL Query Files

This directory contains all SQL queries used by the application, organized by module.

## Directory Structure

```
sql/
├── crm_mapping_storage/    # CRM mappings, division info, relationships
├── list_database_storage/  # Lists, division metadata, list items
└── query_engine/           # DuckDB queries for Overture Parquet data
```

## Usage

SQL files are loaded using the `sql_loader` utility:

```python
from src.sql_loader import load_sql

# Load a query
sql = load_sql('crm_mapping_storage', 'add_mapping')
cursor.execute(sql, (system_id, account_name, ...))
```

## CRM Mapping Storage (17 files)

### Schema Initialization
- `init_schema.sql` - Create all tables and indexes

### Mappings
- `add_mapping.sql` - Insert new CRM mapping
- `get_all_mappings.sql` - Get all mappings
- `get_mapping_by_system_id.sql` - Get mapping by CRM system ID
- `get_mapping_by_division_id.sql` - Get mapping by division ID
- `delete_mapping.sql` - Delete mapping by ID
- `delete_mapping_by_system_id.sql` - Delete mapping by system ID
- `get_count.sql` - Count all mappings
- `clear_all_mappings.sql` - Delete all mappings

### Division Info
- `check_division_info.sql` - Check if division info exists
- `insert_division_info.sql` - Insert division info
- `get_division_info.sql` - Get division info by division ID

### Relationships
- `add_relationship.sql` - Insert new relationship
- `get_all_relationships.sql` - Get all relationships
- `get_children.sql` - Get child divisions
- `get_parents.sql` - Get parent divisions
- `delete_relationship.sql` - Delete relationship
- `get_relationship_count.sql` - Count relationships
- `clear_all_relationships.sql` - Delete all relationships

## List Database Storage (18 files)

### Schema Initialization
- `init_schema.sql` - Create all tables and indexes

### Division Metadata
- `find_metadata_boundary.sql` - Find metadata for boundary type
- `find_metadata_crm.sql` - Find metadata for CRM type
- `update_metadata.sql` - Update existing metadata
- `insert_metadata.sql` - Insert new metadata
- `get_metadata_by_division_id.sql` - Get all metadata for division
- `get_metadata_by_division_id_filtered.sql` - Get metadata by type

### Lists
- `check_list_exists.sql` - Check if list exists
- `insert_list.sql` - Insert new list
- `update_list.sql` - Update list metadata
- `delete_list.sql` - Delete list
- `list_all_lists.sql` - Get all lists with item counts
- `list_all_lists_filtered.sql` - Get lists filtered by type
- `get_list_count.sql` - Count all lists
- `get_list_count_filtered.sql` - Count lists by type
- `clear_all_lists.sql` - Delete all lists

### List Items
- `delete_list_items.sql` - Delete all items from a list
- `insert_list_item.sql` - Insert list item
- `load_list_metadata.sql` - Load list metadata
- `load_list_items.sql` - Load all items with JOIN

## Query Engine (6 files)

DuckDB queries for querying Overture Maps Parquet files. These use placeholder formatting for dynamic paths.

- `get_countries.sql` - Get all distinct countries
- `get_country_division.sql` - Get country-level division
- `get_child_divisions.sql` - Get child divisions by parent ID
- `get_geometry.sql` - Get simplified geometry for division
- `get_division_by_id.sql` - Get division metadata by ID
- `search_boundaries.sql` - Search boundaries by name

### Placeholder Formatting

Query engine SQL files use `{parquet_path}` and `{area_path}` placeholders:

```python
sql = load_sql('query_engine', 'get_countries')
sql = sql.format(parquet_path=self.parquet_path)
conn.execute(sql)
```

## Benefits

1. **Readability** - SQL syntax highlighting in .sql files
2. **Maintainability** - Easy to update queries without touching Python
3. **Testing** - Can test SQL independently
4. **Documentation** - SQL files serve as API documentation
5. **Reusability** - Queries can be used by other tools
6. **Version Control** - Clear diffs for SQL changes

## Future Refactoring

The Python code currently has inline SQL queries that should be refactored to use these files:
- `src/crm_mapping_storage.py` - ~20 queries to refactor
- `src/list_database_storage.py` - ~22 queries to refactor
- `src/query_engine.py` - 6 queries already using string formatting

This refactoring is a gradual process as methods are updated.
