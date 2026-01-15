"""
DuckDB Query Engine for Overture Maps Divisions

This module provides cached query functions to efficiently query
Overture Maps Foundation divisions data (administrative boundaries)
stored in Parquet format.

Note: Uses the 'divisions' theme (replaces deprecated 'admins' theme).
"""

import duckdb
import pandas as pd
import streamlit as st
from typing import List, Dict, Optional, Any
import json


class OvertureQueryEngine:
    """Stateful query engine for Overture Maps divisions data (administrative boundaries)."""

    def __init__(self, parquet_path: str):
        """
        Initialize the query engine.

        Args:
            parquet_path: Path or URL to Overture Maps divisions Parquet files
                         (supports wildcards like 's3://bucket/path/*.parquet')
                         Should point to theme=divisions/type=division files
        """
        self.parquet_path = parquet_path
        self.conn = None

    def _get_connection(self):
        """Get or create DuckDB connection."""
        if self.conn is None:
            self.conn = duckdb.connect(database=':memory:')
            # Install and load necessary extensions for remote/cloud data
            try:
                self.conn.execute("INSTALL httpfs;")
                self.conn.execute("LOAD httpfs;")
            except Exception:
                pass  # Extensions may not be needed for local files
        return self.conn

    @st.cache_data(ttl=3600)
    def get_countries(_self) -> List[str]:
        """
        Get distinct list of countries from the dataset.

        Returns:
            Sorted list of country codes
        """
        conn = _self._get_connection()
        query = f"""
            SELECT DISTINCT country
            FROM read_parquet('{_self.parquet_path}')
            WHERE country IS NOT NULL
            ORDER BY country
        """
        try:
            result = conn.execute(query).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            st.error(f"Error fetching countries: {e}")
            return []

    @st.cache_data(ttl=3600)
    def get_country_division(_self, country: str) -> Optional[Dict]:
        """
        Get the country division record for a given country code.

        Args:
            country: Country code (e.g., 'BE', 'US')

        Returns:
            Dict with country division info or None if not found
        """
        conn = _self._get_connection()
        query = f"""
            SELECT
                id as division_id,
                names.primary as name
            FROM read_parquet('{_self.parquet_path}')
            WHERE country = ?
              AND subtype = 'country'
            LIMIT 1
        """

        try:
            result = conn.execute(query, [country]).fetchdf()
            if not result.empty:
                return result.iloc[0].to_dict()
            return None
        except Exception as e:
            st.error(f"Error fetching country division: {e}")
            return None

    @st.cache_data(ttl=3600)
    def get_child_divisions(_self, parent_division_id: str) -> pd.DataFrame:
        """
        Get child divisions of a specific parent division.

        Args:
            parent_division_id: Parent division ID

        Returns:
            DataFrame with columns: division_id, name, subtype, country, parent_division_id
        """
        conn = _self._get_connection()
        query = f"""
            SELECT
                id as division_id,
                names.primary as name,
                subtype,
                country,
                parent_division_id
            FROM read_parquet('{_self.parquet_path}')
            WHERE parent_division_id = ?
            ORDER BY name
            LIMIT 1000
        """

        try:
            result = conn.execute(query, [parent_division_id]).fetchdf()
            return result
        except Exception as e:
            st.error(f"Error fetching child divisions: {e}")
            return pd.DataFrame(columns=['division_id', 'name', 'subtype', 'country', 'parent_division_id'])

    @st.cache_data(ttl=3600)
    def get_geometry(_self, gers_id: str) -> Optional[Dict[str, Any]]:
        """
        Get geometry for a specific boundary as GeoJSON.

        Args:
            gers_id: GERS ID of the boundary

        Returns:
            GeoJSON geometry dict or None if not found
        """
        conn = _self._get_connection()
        query = f"""
            SELECT
                ST_AsGeoJSON(geometry) as geojson,
                names.primary as name
            FROM read_parquet('{_self.parquet_path}')
            WHERE id = ?
            LIMIT 1
        """

        try:
            result = conn.execute(query, [gers_id]).fetchone()
            if result and result[0]:
                return {
                    'geometry': json.loads(result[0]),
                    'name': result[1]
                }
            return None
        except Exception as e:
            st.error(f"Error fetching geometry: {e}")
            return None

    @st.cache_data(ttl=3600)
    def search_boundaries(_self, country: str, search_term: str) -> pd.DataFrame:
        """
        Search for boundaries by name within a country.

        Args:
            country: Country code
            search_term: Search string for boundary names

        Returns:
            DataFrame with matching boundaries
        """
        conn = _self._get_connection()
        query = f"""
            SELECT
                id as division_id,
                names.primary as name,
                subtype,
                country,
                parent_division_id
            FROM read_parquet('{_self.parquet_path}')
            WHERE country = ?
              AND class = 'land'
              AND LOWER(names.primary) LIKE LOWER(?)
            ORDER BY name
            LIMIT 100
        """

        try:
            search_pattern = f"%{search_term}%"
            result = conn.execute(query, [country, search_pattern]).fetchdf()
            return result
        except Exception as e:
            st.error(f"Error searching boundaries: {e}")
            return pd.DataFrame(columns=['division_id', 'name', 'subtype', 'country', 'parent_division_id'])


def create_query_engine(parquet_path: str) -> OvertureQueryEngine:
    """
    Factory function to create a query engine instance.

    Args:
        parquet_path: Path to Overture Maps Parquet data

    Returns:
        OvertureQueryEngine instance
    """
    return OvertureQueryEngine(parquet_path)
