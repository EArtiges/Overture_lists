"""
Tests for DatabaseStorage list operations.
"""
import pytest
import hashlib


@pytest.mark.database
class TestDatabaseStorageLists:
    """Test list creation and management functionality."""

    def test_create_division_list(self, populated_test_db, sample_division_list_data):
        """Test creating a division list."""
        # Get division IDs
        divisions = populated_test_db.get_all_divisions()
        division_ids = [d['id'] for d in divisions[:2]]  # US and CA

        list_id = populated_test_db.create_list(
            name=sample_division_list_data['name'],
            list_type=sample_division_list_data['type'],
            item_ids=division_ids,
            notes=sample_division_list_data['notes']
        )

        assert list_id is not None
        assert isinstance(list_id, int)

        # Verify it was saved
        saved_list = populated_test_db.get_list(list_id)
        assert saved_list is not None
        assert saved_list['name'] == sample_division_list_data['name']
        assert saved_list['type'] == 'division'

    def test_create_client_list(self, populated_test_db, sample_client_list_data):
        """Test creating a client list."""
        # First create CRM mappings (required by FOREIGN KEY)
        divisions = populated_test_db.get_all_divisions()
        client_ids = ["CRM-001", "CRM-002", "CRM-003"]

        for i, client_id in enumerate(client_ids):
            populated_test_db.save_mapping(
                system_id=client_id,
                division_id=divisions[min(i, len(divisions)-1)]['id'],
                account_name=f"Account {i}",
                custom_admin_level="Region",
                geometry=None
            )

        list_id = populated_test_db.create_list(
            name=sample_client_list_data['name'],
            list_type=sample_client_list_data['type'],
            item_ids=client_ids,
            notes=sample_client_list_data['notes']
        )

        assert list_id is not None

        # Verify it was saved
        saved_list = populated_test_db.get_list(list_id)
        assert saved_list is not None
        assert saved_list['type'] == 'client'

    def test_get_list_by_id(self, populated_test_db, sample_division_list_data):
        """Test retrieving a list by ID."""
        divisions = populated_test_db.get_all_divisions()
        division_ids = [d['id'] for d in divisions[:1]]

        list_id = populated_test_db.create_list(
            name=sample_division_list_data['name'],
            list_type=sample_division_list_data['type'],
            notes=sample_division_list_data['notes'],
            item_ids=division_ids
        )

        retrieved = populated_test_db.get_list(list_id)
        assert retrieved['id'] == list_id
        assert retrieved['name'] == sample_division_list_data['name']
        assert 'created_at' in retrieved
        assert 'updated_at' in retrieved

    def test_get_all_lists(self, populated_test_db):
        """Test retrieving all lists."""
        divisions = populated_test_db.get_all_divisions()

        # Create two lists
        populated_test_db.create_list(
            name="List 1",
            list_type="division",
            notes="First list",
            item_ids=[divisions[0]['id']]
        )
        populated_test_db.create_list(
            name="List 2",
            list_type="division",
            notes="Second list",
            item_ids=[divisions[1]['id']]
        )

        all_lists = populated_test_db.get_all_lists()
        assert len(all_lists) == 2
        assert all(l['name'] for l in all_lists)

    def test_get_lists_by_type(self, populated_test_db):
        """Test filtering lists by type."""
        divisions = populated_test_db.get_all_divisions()

        # Create one of each type
        populated_test_db.create_list(
            name="Division List",
            list_type="division",
            notes="",
            item_ids=[divisions[0]['id']]
        )

        # Create CRM mapping for client list
        populated_test_db.save_mapping(
            system_id="CRM-001",
            division_id=divisions[0]['id'],
            account_name="Test Account",
            custom_admin_level="Region",
            geometry=None
        )

        populated_test_db.create_list(
            name="Client List",
            list_type="client",
            notes="",
            item_ids=["CRM-001"]
        )

        division_lists = populated_test_db.get_lists_by_type("division")
        client_lists = populated_test_db.get_lists_by_type("client")

        assert len(division_lists) == 1
        assert len(client_lists) == 1
        assert division_lists[0]['type'] == 'division'
        assert client_lists[0]['type'] == 'client'

    def test_hash_generation(self, populated_test_db):
        """Test that hash is correctly generated from name + type."""
        divisions = populated_test_db.get_all_divisions()
        name = "Test List"
        list_type = "division"

        expected_hash = hashlib.md5(f"{name}|{list_type}".encode()).hexdigest()

        list_id = populated_test_db.create_list(
            name=name,
            list_type=list_type,
            notes="",
            item_ids=[divisions[0]['id']]
        )

        saved_list = populated_test_db.get_list(list_id)
        assert saved_list['hash'] == expected_hash

    def test_hash_uniqueness_constraint(self, populated_test_db):
        """Test that duplicate list names (same type) are prevented."""
        divisions = populated_test_db.get_all_divisions()
        name = "Duplicate Name Test"

        # Create first list
        populated_test_db.create_list(
            name=name,
            list_type="division",
            notes="First",
            item_ids=[divisions[0]['id']]
        )

        # Try to create second list with same name and type
        with pytest.raises(Exception):  # Should raise IntegrityError
            populated_test_db.create_list(
                name=name,
                list_type="division",
                notes="Second",
                item_ids=[divisions[1]['id']]
            )

    def test_same_name_different_type_allowed(self, populated_test_db):
        """Test that same name is allowed for different types."""
        divisions = populated_test_db.get_all_divisions()
        name = "Same Name Test"

        # Create division list
        list_id1 = populated_test_db.create_list(
            name=name,
            list_type="division",
            notes="",
            item_ids=[divisions[0]['id']]
        )

        # Create CRM mapping for client list
        populated_test_db.save_mapping(
            system_id="CRM-SAME-NAME",
            division_id=divisions[1]['id'],
            account_name="Test",
            custom_admin_level="Region",
            geometry=None
        )

        # Create client list with same name (different type)
        list_id2 = populated_test_db.create_list(
            name=name,
            list_type="client",
            notes="",
            item_ids=["CRM-SAME-NAME"]
        )

        assert list_id1 != list_id2  # Different lists created

        # Verify both exist
        list1 = populated_test_db.get_list(list_id1)
        list2 = populated_test_db.get_list(list_id2)
        assert list1['hash'] != list2['hash']

    def test_delete_list_cascades_items(self, populated_test_db):
        """Test that deleting a list also deletes its items."""
        divisions = populated_test_db.get_all_divisions()
        division_ids = [d['id'] for d in divisions[:2]]

        list_id = populated_test_db.create_list(
            name="Test Cascade",
            list_type="division",
            notes="",
            item_ids=division_ids
        )

        # Verify items exist
        items = populated_test_db.get_list_items(list_id)
        assert len(items) == 2

        # Delete list
        populated_test_db.delete_list(list_id)

        # Verify list is gone
        assert populated_test_db.get_list(list_id) is None

        # Verify items are gone (CASCADE delete)
        items = populated_test_db.get_list_items(list_id)
        assert len(items) == 0

    def test_get_list_items(self, populated_test_db):
        """Test retrieving divisions for a list."""
        divisions = populated_test_db.get_all_divisions()
        division_ids = [d['id'] for d in divisions[:2]]

        list_id = populated_test_db.create_list(
            name="Test Get Divisions",
            list_type="division",
            notes="",
            item_ids=division_ids
        )

        list_divisions = populated_test_db.get_list_items(list_id)
        assert len(list_divisions) == 2
        assert all(d['system_id'] for d in list_divisions)
        assert all(d['name'] for d in list_divisions)

    def test_empty_list_validation(self, test_db):
        """Test that empty lists are not allowed."""
        # Try to create list with no items
        with pytest.raises(ValueError, match="at least one item"):
            test_db.create_list(
                name="Empty List",
                list_type="division",
                notes="",
                item_ids=[]
            )

    def test_get_nonexistent_list(self, test_db):
        """Test retrieving a list that doesn't exist."""
        result = test_db.get_list(99999)
        assert result is None

    def test_list_with_notes(self, populated_test_db):
        """Test creating list with notes field."""
        divisions = populated_test_db.get_all_divisions()
        notes = "This is a detailed note about the list"

        list_id = populated_test_db.create_list(
            name="List with Notes",
            list_type="division",
            notes=notes,
            item_ids=[divisions[0]['id']]
        )

        saved_list = populated_test_db.get_list(list_id)
        assert saved_list['notes'] == notes

    def test_list_with_empty_notes(self, populated_test_db):
        """Test creating list without notes."""
        divisions = populated_test_db.get_all_divisions()

        list_id = populated_test_db.create_list(
            name="List No Notes",
            list_type="division",
            notes="",
            item_ids=[divisions[0]['id']]
        )

        saved_list = populated_test_db.get_list(list_id)
        assert saved_list['notes'] == ""
