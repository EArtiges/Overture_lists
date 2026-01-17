"""
Unified Database Management

Single database class for managing all data in the application:
- CRM mappings
- Lists and list items
- Division metadata and info
- Organizational relationships
"""

import sqlite3
import os
import json
import hashlib
from typing import List, Dict, Optional
from datetime import datetime

from .config import DB_PATH
from .sql_loader import load_sql


class Database:
    """Unified database manager for all application data."""

    def __init__(self, db_path: str = None):
        """
        Initialize Database.

        Args:
            db_path: Path to SQLite database file (defaults to shared app database)
        """
        self.db_path = db_path if db_path is not None else DB_PATH

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize database schema with all tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load and execute both schemas
        crm_schema = load_sql('crm_mapping_storage', 'init_schema')
        list_schema = load_sql('list_database_storage', 'init_schema')

        cursor.executescript(crm_schema)
        cursor.executescript(list_schema)

        # Migration: Add geometry column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(mappings)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'geometry' not in columns:
            cursor.execute("ALTER TABLE mappings ADD COLUMN geometry TEXT")

        conn.commit()
        conn.close()

    # ========== CRM Mapping Methods ==========

    def add_mapping(self, system_id: str, account_name: str, custom_admin_level: str,
                   division_id: str, division_name: str, overture_subtype: str,
                   country: str, geometry: Optional[Dict] = None) -> bool:
        """
        Add a new CRM mapping.
        Automatically stores division metadata.

        Args:
            system_id: CRM system ID
            account_name: CRM account name
            custom_admin_level: Custom admin level classification
            division_id: Overture division ID
            division_name: Division name
            overture_subtype: Overture subtype
            country: Country code
            geometry: Optional GeoJSON geometry dict

        Returns:
            True if successful, False if constraint violation

        Raises:
            sqlite3.IntegrityError: If system_id or division_id already exists
        """
        # Ensure division metadata exists
        self.ensure_division_info(
            division_id,
            division_name=division_name,
            division_subtype=overture_subtype,
            country=country
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Serialize geometry to JSON string if provided
        geometry_str = json.dumps(geometry) if geometry else None

        try:
            cursor.execute("""
                INSERT INTO mappings
                (system_id, account_name, custom_admin_level, division_id,
                 division_name, overture_subtype, country, geometry)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (system_id, account_name, custom_admin_level, division_id,
                  division_name, overture_subtype, country, geometry_str))

            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_all_mappings(self) -> List[Dict]:
        """Get all CRM mappings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, system_id, account_name, custom_admin_level,
                   division_id, division_name, overture_subtype, country,
                   geometry, created_at, updated_at
            FROM mappings
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        # Parse geometry from JSON string to dict
        mappings = []
        for row in rows:
            mapping = dict(row)
            if mapping['geometry']:
                try:
                    mapping['geometry'] = json.loads(mapping['geometry'])
                except (json.JSONDecodeError, TypeError):
                    mapping['geometry'] = None
            mappings.append(mapping)

        return mappings

    def get_mapping_by_system_id(self, system_id: str) -> Optional[Dict]:
        """Get mapping by CRM system ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, system_id, account_name, custom_admin_level,
                   division_id, division_name, overture_subtype, country,
                   geometry, created_at, updated_at
            FROM mappings
            WHERE system_id = ?
        """, (system_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            mapping = dict(row)
            if mapping['geometry']:
                try:
                    mapping['geometry'] = json.loads(mapping['geometry'])
                except (json.JSONDecodeError, TypeError):
                    mapping['geometry'] = None
            return mapping
        return None

    def get_mapping_by_division_id(self, division_id: str) -> Optional[Dict]:
        """Get mapping by Overture division ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, system_id, account_name, custom_admin_level,
                   division_id, division_name, overture_subtype, country,
                   geometry, created_at, updated_at
            FROM mappings
            WHERE division_id = ?
        """, (division_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            mapping = dict(row)
            if mapping['geometry']:
                try:
                    mapping['geometry'] = json.loads(mapping['geometry'])
                except (json.JSONDecodeError, TypeError):
                    mapping['geometry'] = None
            return mapping
        return None

    def delete_mapping(self, mapping_id: int) -> bool:
        """Delete a mapping by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM mappings WHERE id = ?", (mapping_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_mapping_by_system_id(self, system_id: str) -> bool:
        """Delete a mapping by CRM system ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM mappings WHERE system_id = ?", (system_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_mapping_count(self) -> int:
        """Get total count of mappings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM mappings")
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def clear_all_mappings(self) -> bool:
        """Delete all mappings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM mappings")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def export_mappings_to_json_format(self) -> List[Dict]:
        """Export all mappings in JSON-compatible format (without DB metadata)."""
        mappings = self.get_all_mappings()

        return [
            {
                'system_id': m['system_id'],
                'account_name': m['account_name'],
                'custom_admin_level': m['custom_admin_level'],
                'division_id': m['division_id'],
                'division_name': m['division_name'],
                'overture_subtype': m['overture_subtype'],
                'country': m['country'],
                'geometry': m.get('geometry')
            }
            for m in mappings
        ]

    # ========== Division Info Methods ==========

    def ensure_division_info(self, division_id: str, division_name: Optional[str] = None,
                            division_subtype: Optional[str] = None,
                            country: Optional[str] = None) -> bool:
        """
        Ensure division info exists in the database. If it doesn't exist, create it.
        If it exists, optionally update it with new information.

        Args:
            division_id: Overture division ID
            division_name: Name of the division (optional)
            division_subtype: Subtype of the division (optional)
            country: Country code (optional)

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if metadata exists
            cursor.execute("""
                SELECT id FROM division_info WHERE division_id = ?
            """, (division_id,))

            existing = cursor.fetchone()

            if existing:
                # Update existing metadata if new info provided
                if division_name or division_subtype or country:
                    update_fields = []
                    update_values = []

                    if division_name:
                        update_fields.append("division_name = ?")
                        update_values.append(division_name)
                    if division_subtype:
                        update_fields.append("division_subtype = ?")
                        update_values.append(division_subtype)
                    if country:
                        update_fields.append("country = ?")
                        update_values.append(country)

                    if update_fields:
                        update_fields.append("updated_at = CURRENT_TIMESTAMP")
                        update_values.append(division_id)

                        cursor.execute(f"""
                            UPDATE division_info
                            SET {', '.join(update_fields)}
                            WHERE division_id = ?
                        """, update_values)
            else:
                # Insert new metadata
                cursor.execute("""
                    INSERT INTO division_info
                    (division_id, division_name, division_subtype, country)
                    VALUES (?, ?, ?, ?)
                """, (division_id, division_name, division_subtype, country))

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_division_info(self, division_id: str) -> Optional[Dict]:
        """
        Get division info by division ID.

        Args:
            division_id: Overture division ID

        Returns:
            Info dict or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM division_info WHERE division_id = ?
        """, (division_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    # ========== Relationship Methods ==========

    def add_relationship(self, child_division_id: str, parent_division_id: str,
                        relationship_type: str = 'reports_to', notes: Optional[str] = None,
                        child_metadata: Optional[Dict] = None,
                        parent_metadata: Optional[Dict] = None) -> bool:
        """
        Add a new organizational relationship between divisions.
        Automatically stores division metadata if provided.

        Args:
            child_division_id: Overture division ID of the subordinate
            parent_division_id: Overture division ID of the supervisor
            relationship_type: Type of relationship (e.g., 'reports_to', 'coordinates_with')
            notes: Optional notes about this relationship
            child_metadata: Optional dict with keys: division_name, division_subtype, country
            parent_metadata: Optional dict with keys: division_name, division_subtype, country

        Returns:
            True if successful, False otherwise

        Raises:
            sqlite3.IntegrityError: If relationship already exists or self-reference
        """
        # Ensure division metadata exists if provided
        if child_metadata:
            self.ensure_division_info(
                child_division_id,
                division_name=child_metadata.get('division_name') or child_metadata.get('name'),
                division_subtype=child_metadata.get('division_subtype') or child_metadata.get('subtype'),
                country=child_metadata.get('country')
            )

        if parent_metadata:
            self.ensure_division_info(
                parent_division_id,
                division_name=parent_metadata.get('division_name') or parent_metadata.get('name'),
                division_subtype=parent_metadata.get('division_subtype') or parent_metadata.get('subtype'),
                country=parent_metadata.get('country')
            )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO relationships
                (child_division_id, parent_division_id, relationship_type, notes)
                VALUES (?, ?, ?, ?)
            """, (child_division_id, parent_division_id, relationship_type, notes))

            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_all_relationships(self) -> List[Dict]:
        """Get all organizational relationships."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, child_division_id, parent_division_id,
                   relationship_type, notes, created_at
            FROM relationships
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_children(self, parent_division_id: str) -> List[Dict]:
        """Get all divisions that report to the specified parent."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, child_division_id, parent_division_id,
                   relationship_type, notes, created_at
            FROM relationships
            WHERE parent_division_id = ?
            ORDER BY created_at DESC
        """, (parent_division_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_parents(self, child_division_id: str) -> List[Dict]:
        """Get all divisions that the specified child reports to."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, child_division_id, parent_division_id,
                   relationship_type, notes, created_at
            FROM relationships
            WHERE child_division_id = ?
            ORDER BY created_at DESC
        """, (child_division_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def delete_relationship(self, relationship_id: int) -> bool:
        """Delete a relationship by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM relationships WHERE id = ?", (relationship_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_relationship_count(self) -> int:
        """Get total count of relationships."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM relationships")
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def clear_all_relationships(self) -> bool:
        """Delete all relationships."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM relationships")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def export_relationships_to_json(self) -> List[Dict]:
        """Export all relationships in JSON-compatible format."""
        relationships = self.get_all_relationships()

        return [
            {
                'child_division_id': r['child_division_id'],
                'parent_division_id': r['parent_division_id'],
                'relationship_type': r['relationship_type'],
                'notes': r.get('notes')
            }
            for r in relationships
        ]

    # ========== List Methods ==========

    def generate_list_id(self, initial_division_ids: List[str]) -> str:
        """Generate unique list ID using MD5 hash."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{','.join(sorted(initial_division_ids))}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()

    def _find_or_create_metadata(self, cursor, item: Dict, metadata_type: str) -> int:
        """Find existing metadata or create new entry."""
        division_id = item.get('division_id', '')

        # Extract fields based on type
        if metadata_type == 'boundary':
            division_name = item.get('name', '')
            division_subtype = item.get('subtype', '')
            country = item.get('country', '')
            system_id = None
            account_name = None
            custom_admin_level = None
            geometry = None
        else:  # crm_client
            division_name = item.get('division_name', '')
            division_subtype = item.get('overture_subtype', '')
            country = item.get('country', '')
            system_id = item.get('system_id', '')
            account_name = item.get('account_name', '')
            custom_admin_level = item.get('custom_admin_level', '')

            # Serialize geometry if present
            if 'geometry' in item and item['geometry']:
                geometry = json.dumps(item['geometry'])
            else:
                geometry = None

        # Try to find existing metadata
        if metadata_type == 'boundary':
            cursor.execute("""
                SELECT id FROM division_metadata
                WHERE division_id = ? AND metadata_type = ?
                LIMIT 1
            """, (division_id, metadata_type))
        else:
            cursor.execute("""
                SELECT id FROM division_metadata
                WHERE division_id = ? AND system_id = ? AND metadata_type = ?
                LIMIT 1
            """, (division_id, system_id, metadata_type))

        existing = cursor.fetchone()

        if existing:
            # Update existing metadata
            metadata_id = existing[0]
            cursor.execute("""
                UPDATE division_metadata
                SET division_name = ?,
                    division_subtype = ?,
                    country = ?,
                    account_name = ?,
                    custom_admin_level = ?,
                    geometry = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (division_name, division_subtype, country,
                  account_name, custom_admin_level, geometry, metadata_id))
        else:
            # Create new metadata
            cursor.execute("""
                INSERT INTO division_metadata
                (division_id, metadata_type, division_name, division_subtype, country,
                 system_id, account_name, custom_admin_level, geometry)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (division_id, metadata_type, division_name, division_subtype, country,
                  system_id, account_name, custom_admin_level, geometry))
            metadata_id = cursor.lastrowid

        return metadata_id

    def save_list(
        self,
        list_name: str,
        description: str,
        items: Optional[List[Dict]] = None,
        list_type: str = 'boundary',
        list_id: Optional[str] = None,
        boundaries: Optional[List[Dict]] = None  # Backward compatibility alias
    ) -> str:
        """Save a list to database."""
        # Handle backward compatibility
        if items is None and boundaries is not None:
            items = boundaries
        elif items is None:
            items = []

        # Generate list_id if not provided
        if list_id is None:
            division_ids = [item.get('division_id', '') for item in items]
            list_id = self.generate_list_id(division_ids)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if list exists
            cursor.execute("SELECT id FROM list WHERE list_id = ?", (list_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing list
                list_db_id = existing[0]
                cursor.execute("""
                    UPDATE list
                    SET list_name = ?, description = ?, list_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE list_id = ?
                """, (list_name, description, list_type, list_id))

                # Delete existing items
                cursor.execute("DELETE FROM list_item WHERE list_id = ?", (list_db_id,))
            else:
                # Insert new list
                cursor.execute("""
                    INSERT INTO list (list_id, list_type, list_name, description)
                    VALUES (?, ?, ?, ?)
                """, (list_id, list_type, list_name, description))
                list_db_id = cursor.lastrowid

            # Insert all items with metadata
            for idx, item in enumerate(items):
                metadata_id = self._find_or_create_metadata(cursor, item, list_type)

                cursor.execute("""
                    INSERT INTO list_item (list_id, metadata_id, item_order)
                    VALUES (?, ?, ?)
                """, (list_db_id, metadata_id, idx))

            conn.commit()
            return list_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def load_list(self, list_id: str) -> Optional[Dict]:
        """Load a list from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Fetch list metadata
            cursor.execute("""
                SELECT id, list_id, list_type, list_name, description, created_at
                FROM list
                WHERE list_id = ?
            """, (list_id,))

            list_row = cursor.fetchone()

            if not list_row:
                return None

            # Fetch items with metadata
            cursor.execute("""
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
            """, (list_row['id'],))

            items = cursor.fetchall()

            # Format as JSON-compatible dict
            return {
                'list_id': list_row['list_id'],
                'list_name': list_row['list_name'],
                'description': list_row['description'] or '',
                'created_at': list_row['created_at'],
                'boundaries': [
                    self._format_item(dict(item), list_row['list_type'])
                    for item in items
                ]
            }

        finally:
            conn.close()

    def _format_item(self, item: Dict, list_type: str) -> Dict:
        """Convert database row to item dict matching old JSON format."""
        if list_type == 'boundary':
            return {
                'division_id': item['division_id'],
                'name': item['division_name'],
                'subtype': item['division_subtype'],
                'country': item['country']
            }
        else:
            result = {
                'system_id': item['system_id'],
                'account_name': item['account_name'],
                'division_id': item['division_id'],
                'division_name': item['division_name'],
                'country': item['country'],
                'custom_admin_level': item['custom_admin_level'],
                'overture_subtype': item['division_subtype']
            }

            if item['geometry']:
                try:
                    result['geometry'] = json.loads(item['geometry'])
                except (json.JSONDecodeError, TypeError):
                    result['geometry'] = None
            else:
                result['geometry'] = None

            return result

    def list_all_lists(self, list_type: Optional[str] = None) -> List[Dict]:
        """Get metadata for all saved lists."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if list_type:
                cursor.execute("""
                    SELECT
                        l.list_id,
                        l.list_type,
                        l.list_name,
                        l.description,
                        l.created_at,
                        COUNT(i.id) as boundary_count
                    FROM list l
                    LEFT JOIN list_item i ON l.id = i.list_id
                    WHERE l.list_type = ?
                    GROUP BY l.id
                    ORDER BY l.created_at DESC
                """, (list_type,))
            else:
                cursor.execute("""
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
                """)

            rows = cursor.fetchall()

            return [
                {
                    'list_id': row['list_id'],
                    'list_type': row['list_type'],
                    'list_name': row['list_name'],
                    'description': row['description'] or '',
                    'created_at': row['created_at'],
                    'boundary_count': row['boundary_count']
                }
                for row in rows
            ]

        finally:
            conn.close()

    def delete_list(self, list_id: str) -> bool:
        """Delete a list and all its items (CASCADE)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM list WHERE list_id = ?", (list_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_list_count(self, list_type: Optional[str] = None) -> int:
        """Get total count of lists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if list_type:
                cursor.execute("SELECT COUNT(*) FROM list WHERE list_type = ?", (list_type,))
            else:
                cursor.execute("SELECT COUNT(*) FROM list")

            count = cursor.fetchone()[0]
            return count
        finally:
            conn.close()

    def update_list_metadata(
        self,
        list_id: str,
        list_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Update list name and/or description."""
        if list_name is None and description is None:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if list_name and description is not None:
                cursor.execute("""
                    UPDATE list
                    SET list_name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE list_id = ?
                """, (list_name, description, list_id))
            elif list_name:
                cursor.execute("""
                    UPDATE list
                    SET list_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE list_id = ?
                """, (list_name, list_id))
            else:
                cursor.execute("""
                    UPDATE list
                    SET description = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE list_id = ?
                """, (description, list_id))

            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def clear_all_lists(self) -> bool:
        """Delete all lists (CASCADE deletes all list_items)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM list")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_metadata_by_division_id(self, division_id: str, metadata_type: Optional[str] = None) -> List[Dict]:
        """Get all metadata entries for a division_id."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if metadata_type:
                cursor.execute("""
                    SELECT * FROM division_metadata
                    WHERE division_id = ? AND metadata_type = ?
                    ORDER BY created_at DESC
                """, (division_id, metadata_type))
            else:
                cursor.execute("""
                    SELECT * FROM division_metadata
                    WHERE division_id = ?
                    ORDER BY created_at DESC
                """, (division_id,))

            rows = cursor.fetchall()

            results = []
            for row in rows:
                metadata = dict(row)
                # Parse geometry if present
                if metadata['geometry']:
                    try:
                        metadata['geometry'] = json.loads(metadata['geometry'])
                    except (json.JSONDecodeError, TypeError):
                        metadata['geometry'] = None
                results.append(metadata)

            return results

        finally:
            conn.close()
