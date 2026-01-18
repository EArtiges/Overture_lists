"""
Unified SQLite storage for all application data.
Handles divisions, lists, CRM mappings, and relationships.
"""

import sqlite3
import hashlib
import json
import os
from typing import List, Dict, Optional, Union, Any


class DatabaseStorage:
    """
    Unified SQLite storage for all application data.
    Handles divisions, lists, CRM mappings, and relationships.
    """

    def __init__(self, db_path: str = "app_data.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = self._dict_factory
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - commit or rollback."""
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.close()
        return False

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    # ============ Division Operations ============

    def save_division(
        self, system_id: str, name: str, subtype: str, country: str, geometry: dict
    ) -> int:
        """
        Cache a division from Overture. Returns division ID.
        If division already exists, returns existing ID.
        """
        # Check if already cached
        existing = self.get_division_by_system_id(system_id)
        if existing:
            return existing["id"]

        cursor = self.conn.execute(
            """
            INSERT INTO divisions (system_id, name, subtype, country, geometry_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (system_id, name, subtype, country, json.dumps(geometry)),
        )
        return cursor.lastrowid

    def get_division(self, division_id: int) -> Optional[Dict]:
        """Get cached division by internal ID."""
        result = self._execute(
            "SELECT * FROM divisions WHERE id = ?",
            (division_id,),
            fetch_one=True,
        )
        if result and result.get("geometry_json"):
            result["geometry"] = json.loads(result["geometry_json"])
        return result

    def get_division_by_system_id(self, system_id: str) -> Optional[Dict]:
        """Get cached division by Overture system_id."""
        result = self._execute(
            "SELECT * FROM divisions WHERE system_id = ?",
            (system_id,),
            fetch_one=True,
        )
        if result and result.get("geometry_json"):
            result["geometry"] = json.loads(result["geometry_json"])
        return result

    def get_all_divisions(self) -> List[Dict]:
        """Get all cached divisions."""
        results = self._execute("SELECT * FROM divisions", fetch_all=True)
        for result in results:
            if result.get("geometry_json"):
                result["geometry"] = json.loads(result["geometry_json"])
        return results

    # ============ List Operations ============

    def create_list(
        self,
        name: str,
        list_type: str,
        item_ids: List[Union[int, str]],
        notes: str = "",
    ) -> int:
        """
        Create a new list with items atomically.

        Args:
            name: List name
            list_type: 'division' or 'client'
            item_ids: List of division_ids (int) or system_ids (str). Must have at least 1 item.
            notes: Optional notes

        Returns:
            list_id: ID of created list

        Raises:
            ValueError: If item_ids is empty or duplicate list exists
        """
        if not item_ids:
            raise ValueError("List must contain at least one item")

        if list_type not in ("division", "client"):
            raise ValueError("list_type must be 'division' or 'client'")

        # Compute hash for duplicate detection
        hash_val = self._compute_hash(name, list_type)

        # Check for duplicate
        existing = self.check_duplicate_list(hash_val)
        if existing:
            raise ValueError(
                f"List '{name}' of type '{list_type}' already exists (ID: {existing})"
            )

        # Insert into lists table
        cursor = self.conn.execute(
            "INSERT INTO lists (name, type, notes, hash) VALUES (?, ?, ?, ?)",
            (name, list_type, notes, hash_val),
        )
        list_id = cursor.lastrowid

        # Insert items into appropriate junction table
        if list_type == "division":
            self.conn.executemany(
                "INSERT INTO list_divisions (list_id, division_id) VALUES (?, ?)",
                [(list_id, item_id) for item_id in item_ids],
            )
        else:  # client
            self.conn.executemany(
                "INSERT INTO list_clients (list_id, system_id) VALUES (?, ?)",
                [(list_id, item_id) for item_id in item_ids],
            )

        return list_id

    def get_list(self, list_id: int) -> Optional[Dict]:
        """Get list metadata by ID."""
        return self._execute(
            "SELECT * FROM lists WHERE id = ?",
            (list_id,),
            fetch_one=True,
        )

    def get_list_items(self, list_id: int) -> List[Dict]:
        """
        Get all items in a list (divisions or clients).
        Returns list of division or client data depending on list type.
        """
        list_data = self.get_list(list_id)
        if not list_data:
            return []

        if list_data["type"] == "division":
            # Get divisions
            return self._execute(
                """
                SELECT d.* FROM divisions d
                JOIN list_divisions ld ON d.id = ld.division_id
                WHERE ld.list_id = ?
                """,
                (list_id,),
                fetch_all=True,
            )
        else:  # client
            # Get system_ids (CRM client data loaded from clients.json separately)
            results = self._execute(
                """
                SELECT system_id FROM list_clients
                WHERE list_id = ?
                """,
                (list_id,),
                fetch_all=True,
            )
            return [r["system_id"] for r in results]

    def get_all_lists(self, list_type: Optional[str] = None) -> List[Dict]:
        """Get all lists, optionally filtered by type."""
        if list_type:
            return self._execute(
                "SELECT * FROM lists WHERE type = ? ORDER BY created_at DESC",
                (list_type,),
                fetch_all=True,
            )
        return self._execute(
            "SELECT * FROM lists ORDER BY created_at DESC",
            fetch_all=True,
        )

    def update_list(
        self, list_id: int, name: str = None, notes: str = None
    ) -> None:
        """
        Update list metadata (name and/or notes).
        If name changes, hash is recomputed and duplicate check is performed.
        """
        list_data = self.get_list(list_id)
        if not list_data:
            raise ValueError(f"List {list_id} not found")

        updates = []
        params = []

        if name is not None and name != list_data["name"]:
            # Compute new hash
            new_hash = self._compute_hash(name, list_data["type"])

            # Check for duplicate
            existing = self.check_duplicate_list(new_hash)
            if existing and existing != list_id:
                raise ValueError(
                    f"List '{name}' of type '{list_data['type']}' already exists (ID: {existing})"
                )

            updates.extend(["name = ?", "hash = ?"])
            params.extend([name, new_hash])

        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(list_id)
            self.conn.execute(
                f"UPDATE lists SET {', '.join(updates)} WHERE id = ?",
                params,
            )

    def update_list_items(
        self, list_id: int, item_ids: List[Union[int, str]]
    ) -> None:
        """
        Replace all items in a list.

        Args:
            list_id: ID of list to update
            item_ids: New list of items. Must have at least 1 item.

        Raises:
            ValueError: If item_ids is empty or list not found
        """
        if not item_ids:
            raise ValueError("List must contain at least one item")

        list_data = self.get_list(list_id)
        if not list_data:
            raise ValueError(f"List {list_id} not found")

        list_type = list_data["type"]

        # Delete old items and insert new ones
        if list_type == "division":
            self.conn.execute(
                "DELETE FROM list_divisions WHERE list_id = ?", (list_id,)
            )
            self.conn.executemany(
                "INSERT INTO list_divisions (list_id, division_id) VALUES (?, ?)",
                [(list_id, item_id) for item_id in item_ids],
            )
        else:  # client
            self.conn.execute("DELETE FROM list_clients WHERE list_id = ?", (list_id,))
            self.conn.executemany(
                "INSERT INTO list_clients (list_id, system_id) VALUES (?, ?)",
                [(list_id, item_id) for item_id in item_ids],
            )

        # Update timestamp
        self.conn.execute(
            "UPDATE lists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (list_id,),
        )

    def delete_list(self, list_id: int) -> None:
        """Delete a list and its items (CASCADE handled by foreign keys)."""
        self.conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))

    def check_duplicate_list(self, hash_val: str) -> Optional[int]:
        """Check if list with given hash exists. Returns existing list_id or None."""
        result = self._execute(
            "SELECT id FROM lists WHERE hash = ?",
            (hash_val,),
            fetch_one=True,
        )
        return result["id"] if result else None

    # ============ CRM Mapping Operations ============

    def save_mapping(
        self,
        system_id: str,
        division_id: int,
        account_name: str,
        custom_admin_level: str = None,
        division_name: str = None,
        overture_subtype: str = None,
        country: str = None,
        geometry: dict = None,
    ) -> None:
        """Save or update CRM mapping."""
        geometry_json = json.dumps(geometry) if geometry else None

        # Try insert first, update on conflict
        self.conn.execute(
            """
            INSERT INTO crm_mappings
            (system_id, division_id, account_name, custom_admin_level,
             division_name, overture_subtype, country, geometry_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(system_id) DO UPDATE SET
                division_id = excluded.division_id,
                account_name = excluded.account_name,
                custom_admin_level = excluded.custom_admin_level,
                division_name = excluded.division_name,
                overture_subtype = excluded.overture_subtype,
                country = excluded.country,
                geometry_json = excluded.geometry_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                system_id,
                division_id,
                account_name,
                custom_admin_level,
                division_name,
                overture_subtype,
                country,
                geometry_json,
            ),
        )

    def get_mapping_by_system_id(self, system_id: str) -> Optional[Dict]:
        """Get mapping by CRM system ID."""
        result = self._execute(
            "SELECT * FROM crm_mappings WHERE system_id = ?",
            (system_id,),
            fetch_one=True,
        )
        if result and result.get("geometry_json"):
            result["geometry"] = json.loads(result["geometry_json"])
        return result

    def get_mapping_by_division_id(self, division_id: int) -> Optional[Dict]:
        """Get mapping by division ID."""
        result = self._execute(
            "SELECT * FROM crm_mappings WHERE division_id = ?",
            (division_id,),
            fetch_one=True,
        )
        if result and result.get("geometry_json"):
            result["geometry"] = json.loads(result["geometry_json"])
        return result

    def get_all_mappings(self) -> List[Dict]:
        """Get all CRM mappings."""
        results = self._execute("SELECT * FROM crm_mappings", fetch_all=True)
        for result in results:
            if result.get("geometry_json"):
                result["geometry"] = json.loads(result["geometry_json"])
        return results

    def delete_mapping(self, system_id: str) -> None:
        """Delete a CRM mapping."""
        self.conn.execute("DELETE FROM crm_mappings WHERE system_id = ?", (system_id,))

    # ============ Relationship Operations ============

    def add_relationship(
        self,
        parent_division_id: int,
        child_division_id: int,
        relationship_type: str,
    ) -> None:
        """Add organizational hierarchy relationship."""
        if parent_division_id == child_division_id:
            raise ValueError("Parent and child division cannot be the same")

        self.conn.execute(
            """
            INSERT OR IGNORE INTO relationships
            (parent_division_id, child_division_id, relationship_type)
            VALUES (?, ?, ?)
            """,
            (parent_division_id, child_division_id, relationship_type),
        )

    def get_relationships(self, division_id: int = None) -> List[Dict]:
        """
        Get relationships, optionally filtered by division.
        If division_id provided, returns relationships where it's parent or child.
        """
        if division_id:
            return self._execute(
                """
                SELECT * FROM relationships
                WHERE parent_division_id = ? OR child_division_id = ?
                """,
                (division_id, division_id),
                fetch_all=True,
            )
        return self._execute("SELECT * FROM relationships", fetch_all=True)

    def get_all_relationships(self) -> List[Dict]:
        """Get all relationships."""
        return self._execute("SELECT * FROM relationships", fetch_all=True)

    def get_organizational_descendants(
        self, division_id: int, relationship_type: str = 'reports_to', max_depth: int = None
    ) -> List[int]:
        """
        Get all descendant division IDs in organizational hierarchy.

        Args:
            division_id: Parent division database ID
            relationship_type: Type of relationship to follow (default: 'reports_to')
            max_depth: Maximum depth to traverse (None for unlimited)

        Returns:
            List of descendant division database IDs
        """
        # Set depth limit (use large number for unlimited)
        depth_limit = 999 if max_depth is None else max_depth

        query = f"""
            WITH RECURSIVE org_descendants AS (
                -- Base case: direct children (depth 1)
                SELECT
                    child_division_id as division_id,
                    1 as depth
                FROM relationships
                WHERE parent_division_id = ?
                AND relationship_type = ?

                UNION ALL

                -- Recursive case: children of children
                SELECT
                    r.child_division_id,
                    od.depth + 1
                FROM relationships r
                INNER JOIN org_descendants od ON r.parent_division_id = od.division_id
                WHERE r.relationship_type = ?
                AND od.depth < {depth_limit}
            )
            SELECT DISTINCT division_id FROM org_descendants
        """

        results = self._execute(query, (division_id, relationship_type, relationship_type), fetch_all=True)
        return [r['division_id'] for r in results]

    def delete_relationship(
        self, parent_division_id: int, child_division_id: int, relationship_type: str
    ) -> None:
        """Delete a specific relationship."""
        self.conn.execute(
            """
            DELETE FROM relationships
            WHERE parent_division_id = ?
            AND child_division_id = ?
            AND relationship_type = ?
            """,
            (parent_division_id, child_division_id, relationship_type),
        )

    # ============ Helper Methods ============

    def _compute_hash(self, name: str, list_type: str) -> str:
        """Compute MD5 hash for duplicate detection based on name and type."""
        content = f"{name}|{list_type}"
        return hashlib.md5(content.encode()).hexdigest()

    def _init_db(self):
        """Create all tables if they don't exist."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "sql", "schema.sql"
        )
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        self.conn.executescript(schema_sql)
        self.conn.commit()

    def _execute(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> Any:
        """Execute SQL with automatic row factory (returns dicts)."""
        cursor = self.conn.execute(query, params)
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        return cursor

    @staticmethod
    def _dict_factory(cursor, row) -> dict:
        """Convert SQLite row to dict."""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
