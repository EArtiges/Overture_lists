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
                self.conn.execute("INSTALL spatial;")
                self.conn.execute("LOAD spatial;")
            except Exception:
                pass  # Extensions may not be needed for local files
        return self.conn

    @st.cache_data(ttl=3600)
    def get_countries(_self) -> List[Dict]:
        """
        Get list of country divisions from the dataset.

        Returns:
            List of dicts with country division info (division_id, name, subtype, country)
        """
        conn = _self._get_connection()
        query = f"""
            SELECT DISTINCT
                id as division_id,
                names.primary as name,
                subtype,
                country
            FROM read_parquet('{_self.parquet_path}')
            WHERE subtype = 'country'
            ORDER BY country
        """
        try:
            result = conn.execute(query).fetchdf()
            return result.to_dict('records')
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
    def get_descendants(_self, parent_division_id: str, max_depth: int = None) -> pd.DataFrame:
        """
        Get all descendant divisions up to max_depth levels deep using recursive query.

        Args:
            parent_division_id: Parent division ID
            max_depth: Maximum depth to traverse (None for unlimited, going all the way down)

        Returns:
            DataFrame with columns: division_id, name, subtype, country, parent_division_id, depth
        """
        conn = _self._get_connection()

        # Set depth limit (use large number for unlimited)
        depth_limit = 999 if max_depth is None else max_depth

        query = f"""
            WITH RECURSIVE descendants AS (
                -- Base case: direct children (depth 1)
                SELECT
                    id as division_id,
                    names.primary as name,
                    subtype,
                    country,
                    parent_division_id,
                    1 as depth
                FROM read_parquet('{_self.parquet_path}')
                WHERE parent_division_id = ?

                UNION ALL

                -- Recursive case: children of children
                SELECT
                    d.id as division_id,
                    d.names.primary as name,
                    d.subtype,
                    d.country,
                    d.parent_division_id,
                    desc.depth + 1 as depth
                FROM read_parquet('{_self.parquet_path}') d
                INNER JOIN descendants desc ON d.parent_division_id = desc.division_id
                WHERE desc.depth < {depth_limit}
            )
            SELECT DISTINCT
                division_id, name, subtype, country, parent_division_id, depth
            FROM descendants
            ORDER BY depth, name
            LIMIT 10000
        """

        try:
            result = conn.execute(query, [parent_division_id]).fetchdf()
            return result
        except Exception as e:
            st.error(f"Error fetching descendant divisions: {e}")
            return pd.DataFrame(columns=['division_id', 'name', 'subtype', 'country', 'parent_division_id', 'depth'])

    @st.cache_data(ttl=3600)
    def get_geometry(_self, division_id: str) -> Optional[Dict[str, Any]]:
        """
        Get geometry for a specific division from division_area dataset.

        Args:
            division_id: Division ID

        Returns:
            GeoJSON geometry dict with geometry and name, or None if not found
        """
        conn = _self._get_connection()

        # Convert path from type=division to type=division_area
        area_path = _self.parquet_path.replace('type=division', 'type=division_area')

        query = f"""
            SELECT
                ST_AsGeoJSON(ST_Simplify(geometry, 0.001)) as geojson,
                division_id
            FROM read_parquet('{area_path}')
            WHERE division_id = ?
            LIMIT 1
        """

        try:
            result = conn.execute(query, [division_id]).fetchone()
            if result and result[0]:
                return json.loads(result[0])
            return None
        except Exception as e:
            st.error(f"Error fetching geometry: {e}")
            return None

    @st.cache_data(ttl=3600)
    def get_division_by_id(_self, division_id: str) -> Optional[Dict]:
        """
        Get division metadata by division ID.

        Args:
            division_id: Overture division ID

        Returns:
            Dict with division info (division_id, name, subtype, country) or None if not found
        """
        conn = _self._get_connection()
        query = f"""
            SELECT
                id as division_id,
                names.primary as name,
                subtype,
                country
            FROM read_parquet('{_self.parquet_path}')
            WHERE id = ?
            LIMIT 1
        """

        try:
            result = conn.execute(query, [division_id]).fetchdf()
            if not result.empty:
                return result.iloc[0].to_dict()
            return None
        except Exception as e:
            st.error(f"Error fetching division by ID: {e}")
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
