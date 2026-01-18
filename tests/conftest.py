"""
Shared pytest configuration and fixtures for all tests.
"""
import pytest
import sys
import tempfile
import os
import json
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database_storage import DatabaseStorage


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name

    storage = DatabaseStorage(db_path)
    yield storage

    storage.close()
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def populated_test_db(test_db, sample_divisions):
    """Test database pre-populated with sample divisions."""
    for division in sample_divisions:
        test_db.save_division(
            system_id=division['system_id'],
            name=division['name'],
            subtype=division['subtype'],
            country=division['country'],
            geometry=division.get('geometry')
        )
    test_db.conn.commit()
    return test_db


# ============ Sample Division Data ============

@pytest.fixture
def sample_country():
    """US country division."""
    return {
        'system_id': "0858d7df-4c21-6d95-ffff-aadc92e00b0a",
        'name': "United States",
        'subtype': "country",
        'country': "US",
        'geometry': None
    }


@pytest.fixture
def sample_state():
    """California state division."""
    return {
        'system_id': "0858d7e2-aa18-ae63-ffff-e4dc0fb91919",
        'name': "California",
        'subtype': "region",
        'country': "US",
        'geometry': None
    }


@pytest.fixture
def sample_county():
    """LA County division with geometry."""
    return {
        'system_id': "0858d7e4-1234-5678-ffff-abcd12345678",
        'name': "Los Angeles County",
        'subtype': "county",
        'country': "US",
        'geometry': {
            "type": "Polygon",
            "coordinates": [[
                [-118.668, 33.704],
                [-118.155, 33.704],
                [-118.155, 34.337],
                [-118.668, 34.337],
                [-118.668, 33.704]
            ]]
        }
    }


@pytest.fixture
def sample_divisions(sample_country, sample_state, sample_county):
    """Returns list of sample divisions for testing."""
    return [sample_country, sample_state, sample_county]


@pytest.fixture
def sample_uk_country():
    """UK country division."""
    return {
        'system_id': "0858d7df-5c32-7ea6-ffff-bbdc93f01c1b",
        'name': "United Kingdom",
        'subtype': "country",
        'country': "GB",
        'geometry': None
    }


# ============ Sample List Data ============

@pytest.fixture
def sample_division_list_data():
    """Sample division list metadata."""
    return {
        'name': "West Coast Territories",
        'type': "division",
        'notes': "Primary sales territories"
    }


@pytest.fixture
def sample_client_list_data():
    """Sample client list metadata."""
    return {
        'name': "Enterprise Clients Q1",
        'type': "client",
        'notes': "Target list for Q1 campaign"
    }


# ============ Sample CRM Mapping Data ============

@pytest.fixture
def sample_crm_mapping_data():
    """Sample CRM mapping metadata."""
    return {
        'system_id': "CRM-WEST-001",
        'account_name': "California Sales Territory",
        'custom_admin_level': "Regional Office"
    }


# ============ Sample Relationship Data ============

@pytest.fixture
def sample_relationship_data():
    """Sample relationship metadata."""
    return {
        'relationship_type': "reports_to"
    }
