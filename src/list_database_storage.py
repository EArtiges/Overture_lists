"""
List Database Storage

Manages list data using SQLite database with normalized schema.
Replaces JSON file-based storage with a relational database.
"""

import sqlite3
import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional


class ListDatabaseStorage:
    """Manages list data in SQLite database with normalized schema."""

    def __init__(self, db_path: str = "./data/lists.db"):
        """
        Initialize List Database Storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize database schema with normalized tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create lists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id TEXT NOT NULL UNIQUE,
                list_type TEXT NOT NULL CHECK(list_type IN ('boundary', 'crm_client')),
                list_name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create division_metadata table (stores all metadata with context type)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS division_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                division_id TEXT NOT NULL,
                metadata_type TEXT NOT NULL CHECK(metadata_type IN ('boundary', 'crm_client')),

                -- Common fields
                division_name TEXT,
                division_subtype TEXT,
                country TEXT,

                -- CRM-specific fields (NULL for boundaries)
                system_id TEXT,
                account_name TEXT,
                custom_admin_level TEXT,
                geometry TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create list_item junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS list_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER NOT NULL,
                metadata_id INTEGER NOT NULL,
                item_order INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (list_id) REFERENCES list(id) ON DELETE CASCADE,
                FOREIGN KEY (metadata_id) REFERENCES division_metadata(id)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_list_created_at
            ON list(created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_list_type
            ON list(list_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_list_item_list_id
            ON list_item(list_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_list_item_metadata_id
            ON list_item(metadata_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_list_item_order
            ON list_item(list_id, item_order)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_division_metadata_division_id
            ON division_metadata(division_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_division_metadata_type
            ON division_metadata(metadata_type)
        """)

        conn.commit()
        conn.close()

    def generate_list_id(self, initial_division_ids: List[str]) -> str:
        """
        Generate unique list ID using MD5 hash (same as old ListStorage).

        Args:
            initial_division_ids: List of division IDs in the list

        Returns:
            MD5 hash string
        """
        timestamp = datetime.utcnow().isoformat()
        content = f"{','.join(sorted(initial_division_ids))}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()

    def _find_or_create_metadata(self, cursor, item: Dict, metadata_type: str) -> int:
        """
        Find existing metadata or create new entry.

        Args:
            cursor: SQLite cursor
            item: Item dict with metadata fields
            metadata_type: 'boundary' or 'crm_client'

        Returns:
            metadata_id (integer primary key)
        """
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
            # For boundaries, match on division_id and type
            cursor.execute("""
                SELECT id FROM division_metadata
                WHERE division_id = ? AND metadata_type = ?
                LIMIT 1
            """, (division_id, metadata_type))
        else:
            # For CRM clients, match on division_id, system_id, and type
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
        """
        Save a list to database.

        Args:
            list_name: Name of the list
            description: Description of the list
            items: List of item dicts (boundaries or CRM clients)
            list_type: 'boundary' or 'crm_client'
            list_id: Optional existing list ID (for updates)
            boundaries: Alias for items (backward compatibility)

        Returns:
            The list_id of the saved list
        """
        # Handle backward compatibility: accept both 'items' and 'boundaries'
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

                # Delete existing list items
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
        """
        Load a list from database.

        Args:
            list_id: ID of the list to load

        Returns:
            Dict with list data in same format as JSON files, or None if not found
        """
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

            # Fetch items with metadata, ordered by item_order
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

            # Format as JSON-compatible dict (matching old format)
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
        """
        Convert database row to item dict matching old JSON format.

        Args:
            item: Dict from database row
            list_type: 'boundary' or 'crm_client'

        Returns:
            Formatted item dict
        """
        if list_type == 'boundary':
            # Format for boundary lists
            return {
                'division_id': item['division_id'],
                'name': item['division_name'],
                'subtype': item['division_subtype'],
                'country': item['country']
            }
        else:
            # Format for CRM client lists
            result = {
                'system_id': item['system_id'],
                'account_name': item['account_name'],
                'division_id': item['division_id'],
                'division_name': item['division_name'],
                'country': item['country'],
                'custom_admin_level': item['custom_admin_level'],
                'overture_subtype': item['division_subtype']
            }

            # Parse geometry from JSON
            if item['geometry']:
                try:
                    result['geometry'] = json.loads(item['geometry'])
                except (json.JSONDecodeError, TypeError):
                    result['geometry'] = None
            else:
                result['geometry'] = None

            return result

    def list_all_lists(self, list_type: Optional[str] = None) -> List[Dict]:
        """
        Get metadata for all saved lists.

        Args:
            list_type: Filter by type ('boundary' or 'crm_client'), None for all

        Returns:
            List of dicts with list metadata
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Build query with optional type filter
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
        """
        Delete a list and all its items (CASCADE).

        Args:
            list_id: ID of the list to delete

        Returns:
            True if successful, False otherwise
        """
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
        """
        Get total count of lists.

        Args:
            list_type: Filter by type, None for all

        Returns:
            Number of lists
        """
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
        """
        Update list name and/or description.

        Args:
            list_id: ID of the list
            list_name: New name (optional)
            description: New description (optional)

        Returns:
            True if successful, False otherwise
        """
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
        """
        Delete all lists (CASCADE deletes all list_items).

        Returns:
            True if successful
        """
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
        """
        Get all metadata entries for a division_id.

        Args:
            division_id: Overture division ID
            metadata_type: Filter by type ('boundary' or 'crm_client'), None for all

        Returns:
            List of metadata dicts
        """
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
