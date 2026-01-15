"""
List Storage Module

Handles saving and loading admin boundary lists to/from JSON files.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import hashlib


class ListStorage:
    """Manages persistent storage of boundary lists as JSON files."""

    def __init__(self, data_dir: str = "./list_data"):
        """
        Initialize list storage.

        Args:
            data_dir: Directory where list JSON files are stored
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def generate_list_id(self, initial_gers_ids: List[str]) -> str:
        """
        Generate a unique list ID based on initial boundary IDs and timestamp.

        Args:
            initial_gers_ids: List of GERS IDs in the list

        Returns:
            MD5 hash string to use as list ID
        """
        timestamp = datetime.utcnow().isoformat()
        content = f"{','.join(sorted(initial_gers_ids))}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()

    def save_list(
        self,
        list_name: str,
        description: str,
        boundaries: List[Dict],
        list_id: Optional[str] = None
    ) -> str:
        """
        Save a boundary list to JSON file.

        Args:
            list_name: Name of the list
            description: Description of the list
            boundaries: List of boundary dicts with keys:
                        gers_id, name, admin_level, country
            list_id: Optional existing list ID (for updates)

        Returns:
            The list_id of the saved list
        """
        # Generate new list ID if not provided
        if list_id is None:
            gers_ids = [b['gers_id'] for b in boundaries]
            list_id = self.generate_list_id(gers_ids)

        list_data = {
            "list_id": list_id,
            "list_name": list_name,
            "description": description,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "boundaries": boundaries
        }

        filepath = os.path.join(self.data_dir, f"{list_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(list_data, f, indent=2, ensure_ascii=False)

        return list_id

    def load_list(self, list_id: str) -> Optional[Dict]:
        """
        Load a boundary list from JSON file.

        Args:
            list_id: ID of the list to load

        Returns:
            Dict with list data or None if not found
        """
        filepath = os.path.join(self.data_dir, f"{list_id}.json")
        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_all_lists(self) -> List[Dict]:
        """
        Get metadata for all saved lists.

        Returns:
            List of dicts with keys: list_id, list_name, description,
            created_at, boundary_count
        """
        lists = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        lists.append({
                            'list_id': data['list_id'],
                            'list_name': data['list_name'],
                            'description': data.get('description', ''),
                            'created_at': data['created_at'],
                            'boundary_count': len(data['boundaries'])
                        })
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
                    continue

        # Sort by created_at descending
        lists.sort(key=lambda x: x['created_at'], reverse=True)
        return lists

    def delete_list(self, list_id: str) -> bool:
        """
        Delete a list file.

        Args:
            list_id: ID of the list to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        filepath = os.path.join(self.data_dir, f"{list_id}.json")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception:
            return False
