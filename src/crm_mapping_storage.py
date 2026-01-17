"""
CRM Mapping Storage

Manages CRM mapping data using SQLite database with 1:1 constraint enforcement.
"""

import sqlite3
import os
import json
from typing import List, Dict, Optional
from datetime import datetime


class CRMMappingStorage:
    """Manages CRM mapping data in SQLite database."""

    def __init__(self, db_path: str = "./data/crm_mappings.db"):
        """
        Initialize CRM Mapping Storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize database schema with constraints."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create mappings table with UNIQUE constraints for 1:1 mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system_id TEXT NOT NULL UNIQUE,
                account_name TEXT NOT NULL,
                custom_admin_level TEXT NOT NULL,
                division_id TEXT NOT NULL UNIQUE,
                division_name TEXT NOT NULL,
                overture_subtype TEXT,
                country TEXT NOT NULL,
                geometry TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: Add geometry column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(mappings)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'geometry' not in columns:
            cursor.execute("ALTER TABLE mappings ADD COLUMN geometry TEXT")

        # Create index on commonly queried fields
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_country
            ON mappings(country)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_system_id
            ON mappings(system_id)
        """)

        conn.commit()
        conn.close()

    def add_mapping(self, system_id: str, account_name: str, custom_admin_level: str,
                   division_id: str, division_name: str, overture_subtype: str,
                   country: str, geometry: Optional[Dict] = None) -> bool:
        """
        Add a new CRM mapping.

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
            # Re-raise so caller can handle the specific constraint violation
            raise e
        finally:
            conn.close()

    def get_all_mappings(self) -> List[Dict]:
        """
        Get all CRM mappings.

        Returns:
            List of mapping dictionaries with geometry parsed as dict
        """
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
        """
        Get mapping by CRM system ID.

        Args:
            system_id: CRM system ID

        Returns:
            Mapping dictionary with geometry parsed or None if not found
        """
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
        """
        Get mapping by Overture division ID.

        Args:
            division_id: Overture division ID

        Returns:
            Mapping dictionary with geometry parsed or None if not found
        """
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
        """
        Delete a mapping by ID.

        Args:
            mapping_id: Database ID of the mapping

        Returns:
            True if successful, False otherwise
        """
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
        """
        Delete a mapping by CRM system ID.

        Args:
            system_id: CRM system ID

        Returns:
            True if successful, False otherwise
        """
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

    def get_count(self) -> int:
        """
        Get total count of mappings.

        Returns:
            Number of mappings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM mappings")
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def clear_all_mappings(self) -> bool:
        """
        Delete all mappings.

        Returns:
            True if successful
        """
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

    def export_to_json_format(self) -> List[Dict]:
        """
        Export all mappings in JSON-compatible format (without DB metadata).

        Returns:
            List of mapping dictionaries without id, created_at, updated_at
        """
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
