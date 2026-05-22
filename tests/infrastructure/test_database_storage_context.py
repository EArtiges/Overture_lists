"""
Tests for DatabaseStorage context manager and utility methods.
"""
import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database_storage import DatabaseStorage


class TestDatabaseStorageContextManager:
    """Test context manager functionality."""

    def test_context_manager_success(self):
        """Test context manager with successful operation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
            db_path = f.name

        with DatabaseStorage(db_path) as storage:
            # Add a division
            storage.save_division(
                system_id='test123',
                name='Test',
                subtype='country',
                country='US',
                geometry=None
            )

        # Verify data was committed
        storage2 = DatabaseStorage(db_path)
        divisions = storage2.get_all_divisions()
        assert len(divisions) == 1
        assert divisions[0]['system_id'] == 'test123'
        storage2.close()

        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_context_manager_exception_rollback(self):
        """Test context manager rolls back on exception."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            with DatabaseStorage(db_path) as storage:
                # Add a division
                storage.save_division(
                    system_id='test123',
                    name='Test',
                    subtype='country',
                    country='US',
                    geometry=None
                )
                # Raise an exception to trigger rollback
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected exception

        # Verify data was NOT committed due to rollback
        storage2 = DatabaseStorage(db_path)
        divisions = storage2.get_all_divisions()
        # Division should have been rolled back
        assert len(divisions) == 0
        storage2.close()

        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_close_method(self):
        """Test explicit close() method."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
            db_path = f.name

        storage = DatabaseStorage(db_path)
        assert storage.conn is not None

        storage.close()
        # Connection should be closed (can't test directly but method should not fail)

        if os.path.exists(db_path):
            os.unlink(db_path)


class TestDatabaseStorageMiscOperations:
    """Test miscellaneous database operations for coverage."""

    def test_get_list_with_notes(self):
        """Test retrieving list with notes field."""
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

        # Create list with notes
        list_id = storage.create_list(
            name='Test List',
            list_type='division',
            item_ids=[div_id],
            notes='These are test notes'
        )

        # Retrieve list
        retrieved_list = storage.get_list(list_id)
        assert retrieved_list is not None
        assert retrieved_list['notes'] == 'These are test notes'

        storage.close()
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_get_list_with_empty_notes(self):
        """Test retrieving list with empty notes."""
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

        # Create list without notes (None)
        list_id = storage.create_list(
            name='Test List',
            list_type='division',
            item_ids=[div_id],
            notes=None
        )

        # Retrieve list
        retrieved_list = storage.get_list(list_id)
        assert retrieved_list is not None
        # notes can be None or empty string
        assert retrieved_list.get('notes') is None or retrieved_list.get('notes') == ''

        storage.close()
        if os.path.exists(db_path):
            os.unlink(db_path)
