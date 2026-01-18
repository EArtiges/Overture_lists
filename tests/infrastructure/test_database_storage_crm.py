"""
Tests for DatabaseStorage CRM mapping operations.
"""
import pytest


@pytest.mark.database
class TestDatabaseStorageCRMMappings:
    """Test CRM mapping functionality."""

    def test_save_crm_mapping(self, populated_test_db, sample_crm_mapping_data):
        """Test creating a CRM mapping."""
        divisions = populated_test_db.get_all_divisions()
        division_id = divisions[1]['id']  # California

        populated_test_db.save_mapping(
            system_id=sample_crm_mapping_data['system_id'],
            division_id=division_id,
            account_name=sample_crm_mapping_data['account_name'],
            custom_admin_level=sample_crm_mapping_data['custom_admin_level'],
            geometry=divisions[1]['geometry']
        )

        # Verify it was saved
        mapping = populated_test_db.get_mapping_by_system_id(sample_crm_mapping_data['system_id'])
        assert mapping is not None
        assert mapping['system_id'] == sample_crm_mapping_data['system_id']
        assert mapping['account_name'] == sample_crm_mapping_data['account_name']
        assert mapping['custom_admin_level'] == sample_crm_mapping_data['custom_admin_level']

    def test_get_mapping_by_system_id(self, populated_test_db, sample_crm_mapping_data):
        """Test retrieving mapping by CRM system_id."""
        divisions = populated_test_db.get_all_divisions()

        populated_test_db.save_mapping(
            system_id=sample_crm_mapping_data['system_id'],
            division_id=divisions[0]['id'],
            account_name=sample_crm_mapping_data['account_name'],
            custom_admin_level=sample_crm_mapping_data['custom_admin_level'],
            geometry=None
        )

        retrieved = populated_test_db.get_mapping_by_system_id(sample_crm_mapping_data['system_id'])
        assert retrieved['system_id'] == sample_crm_mapping_data['system_id']

    def test_get_mapping_by_division_id(self, populated_test_db, sample_crm_mapping_data):
        """Test retrieving mapping by division_id."""
        divisions = populated_test_db.get_all_divisions()
        division_id = divisions[0]['id']

        populated_test_db.save_mapping(
            system_id=sample_crm_mapping_data['system_id'],
            division_id=division_id,
            account_name=sample_crm_mapping_data['account_name'],
            custom_admin_level=sample_crm_mapping_data['custom_admin_level'],
            geometry=None
        )

        retrieved = populated_test_db.get_mapping_by_system_id_by_division(division_id)
        assert retrieved is not None
        assert retrieved['division_id'] == division_id

    def test_one_to_one_constraint(self, populated_test_db):
        """Test that each division can have only one CRM mapping."""
        divisions = populated_test_db.get_all_divisions()
        division_id = divisions[0]['id']

        # Create first mapping
        populated_test_db.save_mapping(
            system_id="CRM-001",
            division_id=division_id,
            account_name="First Account",
            custom_admin_level="Office 1",
            geometry=None
        )

        # Try to create second mapping for same division (should fail)
        with pytest.raises(Exception):  # UNIQUE constraint on division_id
            populated_test_db.save_mapping(
                system_id="CRM-002",
                division_id=division_id,
                account_name="Second Account",
                custom_admin_level="Office 2",
                geometry=None
            )

    def test_system_id_uniqueness(self, populated_test_db):
        """Test that CRM system_id must be unique."""
        divisions = populated_test_db.get_all_divisions()

        # Create first mapping
        populated_test_db.save_mapping(
            system_id="CRM-UNIQUE",
            division_id=divisions[0]['id'],
            account_name="Account 1",
            custom_admin_level="Office 1",
            geometry=None
        )

        # Try to create second mapping with same system_id (should fail)
        with pytest.raises(Exception):  # PRIMARY KEY constraint
            populated_test_db.save_mapping(
                system_id="CRM-UNIQUE",
                division_id=divisions[1]['id'],
                account_name="Account 2",
                custom_admin_level="Office 2",
                geometry=None
            )

    def test_mapping_with_custom_admin_level_text(self, populated_test_db):
        """Test that custom_admin_level stores free-text labels."""
        divisions = populated_test_db.get_all_divisions()

        custom_labels = [
            "Regional Office",
            "Sales Territory",
            "District Manager",
            "Vice President Region"
        ]

        for i, label in enumerate(custom_labels):
            populated_test_db.save_mapping(
                system_id=f"CRM-{i}",
                division_id=divisions[min(i, len(divisions) - 1)]['id'],
                account_name=f"Account {i}",
                custom_admin_level=label,
                geometry=None
            )

            mapping = populated_test_db.get_mapping_by_system_id(f"CRM-{i}")
            assert mapping['custom_admin_level'] == label

    def test_mapping_geometry_caching(self, populated_test_db, sample_county):
        """Test that geometry is cached in CRM mapping."""
        # Get county division with geometry
        divisions = populated_test_db.get_all_divisions()
        county = [d for d in divisions if d['subtype'] == 'county'][0]

        populated_test_db.save_mapping(
            system_id="CRM-GEO",
            division_id=county['id'],
            account_name="Geo Account",
            custom_admin_level="Region",
            geometry=county['geometry']
        )

        mapping = populated_test_db.get_mapping_by_system_id("CRM-GEO")
        assert mapping['geometry'] is not None
        assert mapping['geometry']['type'] == 'Polygon'

    def test_update_mapping_metadata(self, populated_test_db):
        """Test updating CRM mapping metadata (upsert behavior)."""
        divisions = populated_test_db.get_all_divisions()
        system_id = "CRM-UPDATE"

        # Create initial mapping
        populated_test_db.save_mapping(
            system_id=system_id,
            division_id=divisions[0]['id'],
            account_name="Initial Name",
            custom_admin_level="Initial Level",
            geometry=None
        )

        # Update mapping (upsert)
        populated_test_db.save_mapping(
            system_id=system_id,
            division_id=divisions[0]['id'],
            account_name="Updated Name",
            custom_admin_level="Updated Level",
            geometry=None
        )

        mapping = populated_test_db.get_mapping_by_system_id(system_id)
        assert mapping['account_name'] == "Updated Name"
        assert mapping['custom_admin_level'] == "Updated Level"

    def test_delete_mapping(self, populated_test_db):
        """Test deleting a CRM mapping."""
        divisions = populated_test_db.get_all_divisions()
        system_id = "CRM-DELETE"

        populated_test_db.save_mapping(
            system_id=system_id,
            division_id=divisions[0]['id'],
            account_name="Delete Me",
            custom_admin_level="Temp",
            geometry=None
        )

        # Verify it exists
        assert populated_test_db.get_mapping_by_system_id(system_id) is not None

        # Delete it
        populated_test_db.delete_mapping(system_id)

        # Verify it's gone
        assert populated_test_db.get_mapping_by_system_id(system_id) is None

    def test_get_all_mappings(self, populated_test_db):
        """Test retrieving all CRM mappings."""
        divisions = populated_test_db.get_all_divisions()

        # Create multiple mappings
        for i in range(3):
            populated_test_db.save_mapping(
                system_id=f"CRM-ALL-{i}",
                division_id=divisions[i]['id'],
                account_name=f"Account {i}",
                custom_admin_level=f"Level {i}",
                geometry=None
            )

        all_mappings = populated_test_db.get_all_mappings()
        assert len(all_mappings) >= 3
        assert all(m['system_id'] for m in all_mappings)

    def test_delete_division_cascades_mapping(self, test_db, sample_country):
        """Test that deleting a division also deletes its CRM mapping."""
        # Save division
        division_id = test_db.save_division(
            system_id=sample_country['system_id'],
            name=sample_country['name'],
            subtype=sample_country['subtype'],
            country=sample_country['country'],
            geometry=None
        )

        # Create mapping
        test_db.save_mapping(
            system_id="CRM-CASCADE",
            division_id=division_id,
            account_name="Cascade Test",
            custom_admin_level="Region",
            geometry=None
        )

        # Verify mapping exists
        assert test_db.get_mapping_by_system_id("CRM-CASCADE") is not None

        # Delete division
        test_db.conn.execute("DELETE FROM divisions WHERE id = ?", (division_id,))
        test_db.conn.commit()

        # Verify mapping is gone (CASCADE delete)
        assert test_db.get_mapping_by_system_id("CRM-CASCADE") is None

    def test_get_nonexistent_mapping(self, test_db):
        """Test retrieving mapping that doesn't exist."""
        result = test_db.get_mapping_by_system_id("NONEXISTENT")
        assert result is None

    def test_mapping_with_null_custom_level(self, populated_test_db):
        """Test creating mapping without custom_admin_level."""
        divisions = populated_test_db.get_all_divisions()

        populated_test_db.save_mapping(
            system_id="CRM-NULL",
            division_id=divisions[0]['id'],
            account_name="No Custom Level",
            custom_admin_level=None,
            geometry=None
        )

        mapping = populated_test_db.get_mapping_by_system_id("CRM-NULL")
        assert mapping['custom_admin_level'] is None
