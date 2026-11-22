"""
Tests for CRMClientStorage.

Tests JSON file loading, filtering, and validation of CRM client data.
"""
import pytest
import json
import os
import tempfile
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from crm_client_storage import CRMClientStorage


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_clients():
    """Sample client data for testing."""
    return [
        {
            'system_id': 'client1',
            'account_name': 'Acme Corp',
            'division_id': 'div1',
            'division_name': 'California',
            'country': 'US',
            'custom_admin_level': 'State'
        },
        {
            'system_id': 'client2',
            'account_name': 'British Ltd',
            'division_id': 'div2',
            'division_name': 'England',
            'country': 'GB',
            'custom_admin_level': 'Region'
        },
        {
            'system_id': 'client3',
            'account_name': 'Canadian Inc',
            'division_id': 'div3',
            'division_name': 'Ontario',
            'country': 'CA',
            'custom_admin_level': 'Province'
        },
        {
            'system_id': 'client4',
            'account_name': 'Another US Corp',
            'division_id': 'div4',
            'division_name': 'Texas',
            'country': 'US',
            'custom_admin_level': 'State'
        }
    ]


@pytest.fixture
def storage_with_data(temp_data_dir, sample_clients):
    """CRMClientStorage instance with test data."""
    clients_file = os.path.join(temp_data_dir, 'clients.json')
    with open(clients_file, 'w') as f:
        json.dump(sample_clients, f)
    return CRMClientStorage(data_dir=temp_data_dir)


class TestCRMClientStorageInit:
    """Test CRMClientStorage initialization."""

    def test_initialization(self, temp_data_dir):
        """Test storage initializes with correct paths."""
        storage = CRMClientStorage(data_dir=temp_data_dir)
        assert storage.data_dir == temp_data_dir
        assert storage.clients_file == os.path.join(temp_data_dir, 'clients.json')

    def test_default_data_dir(self):
        """Test storage uses default directory."""
        storage = CRMClientStorage()
        assert storage.data_dir == './crm_data'
        assert storage.clients_file == './crm_data/clients.json'


class TestLoadClients:
    """Test loading client data from JSON."""

    def setUp(self):
        """Clear Streamlit cache before each test."""
        try:
            import streamlit as st
            st.cache_data.clear()
        except:
            pass

    def test_load_clients_success(self, storage_with_data, sample_clients):
        """Test successfully loading clients from file."""
        self.setUp()
        clients = storage_with_data.load_clients()
        assert len(clients) == len(sample_clients)
        assert clients == sample_clients

    def test_load_clients_nonexistent_file(self, temp_data_dir):
        """Test loading when file doesn't exist returns empty list."""
        self.setUp()
        # Use unique temp dir to avoid cache collision
        unique_dir = tempfile.mkdtemp()
        storage = CRMClientStorage(data_dir=unique_dir)
        clients = storage.load_clients()
        assert clients == []
        os.rmdir(unique_dir)

    def test_load_clients_invalid_json(self, temp_data_dir):
        """Test loading invalid JSON returns empty list."""
        self.setUp()
        unique_dir = tempfile.mkdtemp()
        clients_file = os.path.join(unique_dir, 'clients.json')
        with open(clients_file, 'w') as f:
            f.write('{ invalid json }')

        storage = CRMClientStorage(data_dir=unique_dir)
        clients = storage.load_clients()
        assert clients == []

        os.remove(clients_file)
        os.rmdir(unique_dir)

    def test_load_clients_not_array(self, temp_data_dir):
        """Test loading non-array JSON returns empty list."""
        self.setUp()
        unique_dir = tempfile.mkdtemp()
        clients_file = os.path.join(unique_dir, 'clients.json')
        with open(clients_file, 'w') as f:
            json.dump({'not': 'an array'}, f)

        storage = CRMClientStorage(data_dir=unique_dir)
        clients = storage.load_clients()
        assert clients == []

        os.remove(clients_file)
        os.rmdir(unique_dir)

    def test_load_clients_empty_array(self, temp_data_dir):
        """Test loading empty array."""
        self.setUp()
        unique_dir = tempfile.mkdtemp()
        clients_file = os.path.join(unique_dir, 'clients.json')
        with open(clients_file, 'w') as f:
            json.dump([], f)

        storage = CRMClientStorage(data_dir=unique_dir)
        clients = storage.load_clients()
        assert clients == []

        os.remove(clients_file)
        os.rmdir(unique_dir)


class TestGetCountries:
    """Test extracting countries from client data."""

    def test_get_countries(self, storage_with_data, sample_clients):
        """Test extracting unique countries."""
        countries = storage_with_data.get_countries(sample_clients)
        assert countries == ['CA', 'GB', 'US']  # Sorted alphabetically

    def test_get_countries_empty_list(self, storage_with_data):
        """Test getting countries from empty list."""
        countries = storage_with_data.get_countries([])
        assert countries == []

    def test_get_countries_missing_field(self, storage_with_data):
        """Test getting countries when some clients lack country field."""
        clients = [
            {'system_id': 'c1', 'country': 'US'},
            {'system_id': 'c2'},  # Missing country
            {'system_id': 'c3', 'country': 'GB'}
        ]
        countries = storage_with_data.get_countries(clients)
        assert countries == ['GB', 'US']

    def test_get_countries_deduplication(self, storage_with_data):
        """Test that countries are deduplicated."""
        clients = [
            {'country': 'US'},
            {'country': 'US'},
            {'country': 'GB'},
            {'country': 'US'}
        ]
        countries = storage_with_data.get_countries(clients)
        assert countries == ['GB', 'US']


class TestFilterByCountry:
    """Test filtering clients by country."""

    def test_filter_by_country_us(self, storage_with_data, sample_clients):
        """Test filtering for US clients."""
        us_clients = storage_with_data.filter_by_country(sample_clients, 'US')
        assert len(us_clients) == 2
        assert all(c['country'] == 'US' for c in us_clients)

    def test_filter_by_country_gb(self, storage_with_data, sample_clients):
        """Test filtering for GB clients."""
        gb_clients = storage_with_data.filter_by_country(sample_clients, 'GB')
        assert len(gb_clients) == 1
        assert gb_clients[0]['country'] == 'GB'
        assert gb_clients[0]['account_name'] == 'British Ltd'

    def test_filter_by_country_no_matches(self, storage_with_data, sample_clients):
        """Test filtering with no matches."""
        clients = storage_with_data.filter_by_country(sample_clients, 'XX')
        assert clients == []

    def test_filter_by_country_empty_list(self, storage_with_data):
        """Test filtering empty list."""
        clients = storage_with_data.filter_by_country([], 'US')
        assert clients == []

    def test_filter_by_country_missing_field(self, storage_with_data):
        """Test filtering when some clients lack country field."""
        clients = [
            {'system_id': 'c1', 'country': 'US'},
            {'system_id': 'c2'},  # Missing country
            {'system_id': 'c3', 'country': 'US'}
        ]
        us_clients = storage_with_data.filter_by_country(clients, 'US')
        assert len(us_clients) == 2


class TestValidateClientData:
    """Test client data validation."""

    def test_validate_complete_client(self, storage_with_data):
        """Test validating a complete client record."""
        client = {
            'system_id': 'c1',
            'account_name': 'Test Corp',
            'division_id': 'd1',
            'division_name': 'Test Division',
            'country': 'US',
            'custom_admin_level': 'State'
        }
        assert storage_with_data.validate_client_data(client) is True

    def test_validate_missing_system_id(self, storage_with_data):
        """Test validation fails when system_id is missing."""
        client = {
            'account_name': 'Test Corp',
            'division_id': 'd1',
            'division_name': 'Test Division',
            'country': 'US',
            'custom_admin_level': 'State'
        }
        assert storage_with_data.validate_client_data(client) is False

    def test_validate_missing_account_name(self, storage_with_data):
        """Test validation fails when account_name is missing."""
        client = {
            'system_id': 'c1',
            'division_id': 'd1',
            'division_name': 'Test Division',
            'country': 'US',
            'custom_admin_level': 'State'
        }
        assert storage_with_data.validate_client_data(client) is False

    def test_validate_missing_division_id(self, storage_with_data):
        """Test validation fails when division_id is missing."""
        client = {
            'system_id': 'c1',
            'account_name': 'Test Corp',
            'division_name': 'Test Division',
            'country': 'US',
            'custom_admin_level': 'State'
        }
        assert storage_with_data.validate_client_data(client) is False

    def test_validate_missing_division_name(self, storage_with_data):
        """Test validation fails when division_name is missing."""
        client = {
            'system_id': 'c1',
            'account_name': 'Test Corp',
            'division_id': 'd1',
            'country': 'US',
            'custom_admin_level': 'State'
        }
        assert storage_with_data.validate_client_data(client) is False

    def test_validate_missing_country(self, storage_with_data):
        """Test validation fails when country is missing."""
        client = {
            'system_id': 'c1',
            'account_name': 'Test Corp',
            'division_id': 'd1',
            'division_name': 'Test Division',
            'custom_admin_level': 'State'
        }
        assert storage_with_data.validate_client_data(client) is False

    def test_validate_missing_custom_admin_level(self, storage_with_data):
        """Test validation fails when custom_admin_level is missing."""
        client = {
            'system_id': 'c1',
            'account_name': 'Test Corp',
            'division_id': 'd1',
            'division_name': 'Test Division',
            'country': 'US'
        }
        assert storage_with_data.validate_client_data(client) is False

    def test_validate_empty_dict(self, storage_with_data):
        """Test validation fails for empty dictionary."""
        assert storage_with_data.validate_client_data({}) is False

    def test_validate_with_extra_fields(self, storage_with_data):
        """Test validation succeeds even with extra fields."""
        client = {
            'system_id': 'c1',
            'account_name': 'Test Corp',
            'division_id': 'd1',
            'division_name': 'Test Division',
            'country': 'US',
            'custom_admin_level': 'State',
            'extra_field': 'Extra Value',
            'another_field': 123
        }
        assert storage_with_data.validate_client_data(client) is True
