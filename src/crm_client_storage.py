"""
CRM Client Storage

Manages loading and filtering of CRM client data from JSON files.
"""

import json
import os
import streamlit as st
from typing import List, Dict, Optional


class CRMClientStorage:
    """Manages CRM client data loading from JSON."""

    def __init__(self, data_dir: str = "./crm_data"):
        """
        Initialize CRM Client Storage.

        Args:
            data_dir: Directory containing CRM client data files
        """
        self.data_dir = data_dir
        self.clients_file = os.path.join(data_dir, "clients.json")

    @st.cache_data(ttl=3600)
    def load_clients(_self) -> List[Dict]:
        """
        Load all CRM clients from JSON file.

        Returns:
            List of client dictionaries
        """
        if not os.path.exists(_self.clients_file):
            return []

        try:
            with open(_self.clients_file, 'r') as f:
                clients = json.load(f)

            # Validate that it's a list
            if not isinstance(clients, list):
                st.error("Invalid clients.json format: expected a JSON array")
                return []

            return clients
        except json.JSONDecodeError as e:
            st.error(f"Error parsing clients.json: {e}")
            return []
        except Exception as e:
            st.error(f"Error loading clients.json: {e}")
            return []

    def get_countries(self, clients: List[Dict]) -> List[str]:
        """
        Extract unique countries from client data.

        Args:
            clients: List of client dictionaries

        Returns:
            Sorted list of unique country codes
        """
        countries = set()
        for client in clients:
            if 'country' in client:
                countries.add(client['country'])
        return sorted(list(countries))

    def filter_by_country(self, clients: List[Dict], country: str) -> List[Dict]:
        """
        Filter clients by country.

        Args:
            clients: List of client dictionaries
            country: Country code to filter by

        Returns:
            List of clients matching the country
        """
        return [c for c in clients if c.get('country') == country]

    def validate_client_data(self, client: Dict) -> bool:
        """
        Validate client record has required fields.

        Args:
            client: Client dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'system_id',
            'account_name',
            'division_id',
            'division_name',
            'country',
            'custom_admin_level'
        ]

        for field in required_fields:
            if field not in client:
                return False

        return True
