"""
Additional DatabaseStorage tests for coverage.
"""
import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database_storage import DatabaseStorage


class TestDatabaseStorageAdditional:
    """Additional tests to improve coverage."""

    def test_delete_list(self):
        """Test delete_list method for coverage."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
            db_path = f.name

        storage = DatabaseStorage(db_path)

        # Create division first
        div_id = storage.save_division(
            system_id='div1',
            name='California',
            subtype='region',
            country='US',
            geometry=None
        )

        # Create list
        list_id = storage.create_list(
            name='Test List',
            list_type='division',
            item_ids=[div_id]
        )

        # Delete list
        storage.delete_list(list_id)

        # Verify list is deleted
        retrieved = storage.get_list(list_id)
        assert retrieved is None

        storage.close()
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_update_list(self):
        """Test update_list method for coverage."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
            db_path = f.name

        storage = DatabaseStorage(db_path)

        # Create divisions
        div1 = storage.save_division(
            system_id='div1',
            name='California',
            subtype='region',
            country='US',
            geometry=None
        )
        div2 = storage.save_division(
            system_id='div2',
            name='Oregon',
            subtype='region',
            country='US',
            geometry=None
        )

        # Create list
        list_id = storage.create_list(
            name='West Coast',
            list_type='division',
            item_ids=[div1]
        )

        # Update list metadata
        storage.update_list(
            list_id=list_id,
            notes='Updated notes'
        )

        # Update list items
        storage.update_list_items(
            list_id=list_id,
            item_ids=[div1, div2]
        )

        # Verify updates
        retrieved = storage.get_list(list_id)
        assert retrieved['notes'] == 'Updated notes'

        items = storage.get_list_items(list_id)
        assert len(items) == 2

        storage.close()
        if os.path.exists(db_path):
            os.unlink(db_path)
