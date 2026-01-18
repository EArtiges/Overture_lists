"""
Tests for DatabaseStorage division caching operations.
"""
import pytest
import json


@pytest.mark.database
class TestDatabaseStorageDivisions:
    """Test division caching functionality."""

    def test_save_division(self, test_db, sample_country):
        """Test caching a division."""
        division_id = test_db.save_division(
            system_id=sample_country['system_id'],
            name=sample_country['name'],
            subtype=sample_country['subtype'],
            country=sample_country['country'],
            geometry=sample_country['geometry']
        )

        assert division_id is not None
        assert isinstance(division_id, int)

        # Verify it was saved
        cached = test_db.get_division(division_id)
        assert cached is not None
        assert cached['system_id'] == sample_country['system_id']
        assert cached['name'] == sample_country['name']

    def test_save_division_with_geometry(self, test_db, sample_county):
        """Test caching a division with geometry."""
        division_id = test_db.save_division(
            system_id=sample_county['system_id'],
            name=sample_county['name'],
            subtype=sample_county['subtype'],
            country=sample_county['country'],
            geometry=sample_county['geometry']
        )

        cached = test_db.get_division(division_id)
        assert cached['geometry'] is not None
        assert cached['geometry']['type'] == 'Polygon'
        assert len(cached['geometry']['coordinates']) > 0

    def test_get_cached_division_by_id(self, test_db, sample_state):
        """Test retrieving cached division by internal ID."""
        division_id = test_db.save_division(
            system_id=sample_state['system_id'],
            name=sample_state['name'],
            subtype=sample_state['subtype'],
            country=sample_state['country'],
            geometry=sample_state['geometry']
        )

        retrieved = test_db.get_division(division_id)
        assert retrieved is not None
        assert retrieved['id'] == division_id
        assert retrieved['name'] == sample_state['name']

    def test_get_division_by_system_id(self, test_db, sample_country):
        """Test retrieving cached division by Overture system_id."""
        test_db.save_division(
            system_id=sample_country['system_id'],
            name=sample_country['name'],
            subtype=sample_country['subtype'],
            country=sample_country['country'],
            geometry=sample_country['geometry']
        )

        retrieved = test_db.get_division_by_system_id(sample_country['system_id'])
        assert retrieved is not None
        assert retrieved['system_id'] == sample_country['system_id']
        assert retrieved['name'] == sample_country['name']

    def test_system_id_uniqueness(self, test_db, sample_country):
        """Test that system_id is unique - saving same division twice returns same ID."""
        id1 = test_db.save_division(
            system_id=sample_country['system_id'],
            name=sample_country['name'],
            subtype=sample_country['subtype'],
            country=sample_country['country'],
            geometry=sample_country['geometry']
        )

        # Try to save again with same system_id
        id2 = test_db.save_division(
            system_id=sample_country['system_id'],
            name=sample_country['name'],
            subtype=sample_country['subtype'],
            country=sample_country['country'],
            geometry=sample_country['geometry']
        )

        assert id1 == id2  # Should return existing ID

    def test_get_all_divisions(self, populated_test_db):
        """Test retrieving all cached divisions."""
        all_divisions = populated_test_db.get_all_divisions()

        assert len(all_divisions) == 3  # US, CA, LA County
        assert all(d['system_id'] for d in all_divisions)
        assert all(d['name'] for d in all_divisions)

    def test_get_nonexistent_division(self, test_db):
        """Test retrieving division that doesn't exist."""
        result = test_db.get_division(99999)
        assert result is None

    def test_get_nonexistent_system_id(self, test_db):
        """Test retrieving division by nonexistent system_id."""
        result = test_db.get_division_by_system_id("nonexistent-id")
        assert result is None

    def test_division_geometry_null_handling(self, test_db, sample_country):
        """Test that divisions without geometry are handled correctly."""
        division_id = test_db.save_division(
            system_id=sample_country['system_id'],
            name=sample_country['name'],
            subtype=sample_country['subtype'],
            country=sample_country['country'],
            geometry=None
        )

        cached = test_db.get_division(division_id)
        assert cached['geometry'] is None

    def test_update_cached_geometry(self, test_db, sample_state):
        """Test updating geometry for a cached division."""
        # First save without geometry
        division_id = test_db.save_division(
            system_id=sample_state['system_id'],
            name=sample_state['name'],
            subtype=sample_state['subtype'],
            country=sample_state['country'],
            geometry=None
        )

        # Update with geometry
        new_geometry = {
            "type": "Point",
            "coordinates": [-119.4179, 36.7783]
        }

        cursor = test_db.conn.execute(
            "UPDATE divisions SET geometry_json = ? WHERE id = ?",
            (json.dumps(new_geometry), division_id)
        )
        test_db.conn.commit()

        # Verify update
        cached = test_db.get_division(division_id)
        assert cached['geometry'] is not None
        assert cached['geometry']['type'] == 'Point'
