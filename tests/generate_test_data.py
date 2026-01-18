"""
Test Data Generator for Overture Admin Boundary List Builder

Generates sample Parquet files mimicking Overture Maps structure for local testing.
"""

import duckdb


def generate_test_parquet(output_path: str = "./tests/test_boundaries.parquet"):
    """
    Generate a sample Parquet file with test boundary data.

    Args:
        output_path: Path where to save the test Parquet file
    """
    conn = duckdb.connect(':memory:')

    # Load spatial extension for geometry support
    try:
        conn.execute("INSTALL spatial;")
        conn.execute("LOAD spatial;")
    except Exception:
        pass  # May already be installed

    # Create sample data matching Overture schema
    sample_data = [
        # United States boundaries
        {
            'id': '0858d7df-4c21-6d95-ffff-aadc92e00b0a',  # Match test fixture
            'names': {'primary': 'United States'},
            'subtype': 'country',
            'country': 'US',
            'parent_division_id': None,
            'geometry': 'POLYGON((-125 25, -125 49, -66 49, -66 25, -125 25))'
        },
        {
            'id': '0858d7e2-aa18-ae63-ffff-e4dc0fb91919',  # Match test fixture
            'names': {'primary': 'California'},
            'subtype': 'region',
            'country': 'US',
            'parent_division_id': '0858d7df-4c21-6d95-ffff-aadc92e00b0a',
            'geometry': 'POLYGON((-124.4 32.5, -124.4 42, -114.1 42, -114.1 32.5, -124.4 32.5))'
        },
        {
            'id': '0858d7e4-1234-5678-ffff-abcd12345678',  # Match test fixture
            'names': {'primary': 'Los Angeles County'},
            'subtype': 'county',
            'country': 'US',
            'parent_division_id': '0858d7e2-aa18-ae63-ffff-e4dc0fb91919',
            'geometry': 'POLYGON((-118.668 33.704, -118.155 33.704, -118.155 34.337, -118.668 34.337, -118.668 33.704))'
        },
        {
            'id': 'us_or_state',
            'names': {'primary': 'Oregon'},
            'subtype': 'region',
            'country': 'US',
            'parent_division_id': '0858d7df-4c21-6d95-ffff-aadc92e00b0a',
            'geometry': 'POLYGON((-124.5 42, -124.5 46.2, -116.5 46.2, -116.5 42, -124.5 42))'
        },
        {
            'id': 'us_wa_state',
            'names': {'primary': 'Washington'},
            'subtype': 'region',
            'country': 'US',
            'parent_division_id': '0858d7df-4c21-6d95-ffff-aadc92e00b0a',
            'geometry': 'POLYGON((-124.8 45.5, -124.8 49, -116.9 49, -116.9 45.5, -124.8 45.5))'
        },
        {
            'id': 'us_ca_sf_county',
            'names': {'primary': 'San Francisco County'},
            'subtype': 'county',
            'country': 'US',
            'parent_division_id': '0858d7e2-aa18-ae63-ffff-e4dc0fb91919',
            'geometry': 'POLYGON((-122.5 37.7, -122.5 37.8, -122.3 37.8, -122.3 37.7, -122.5 37.7))'
        },
        # United Kingdom boundaries
        {
            'id': '0858d7df-5c32-7ea6-ffff-bbdc93f01c1b',  # Match test fixture
            'names': {'primary': 'United Kingdom'},
            'subtype': 'country',
            'country': 'GB',
            'parent_division_id': None,
            'geometry': 'POLYGON((-8 50, -8 60, 2 60, 2 50, -8 50))'
        },
        {
            'id': 'gb_eng_region',
            'names': {'primary': 'England'},
            'subtype': 'region',
            'country': 'GB',
            'parent_division_id': '0858d7df-5c32-7ea6-ffff-bbdc93f01c1b',
            'geometry': 'POLYGON((-6 50, -6 55, 2 55, 2 50, -6 50))'
        },
        {
            'id': 'gb_sct_region',
            'names': {'primary': 'Scotland'},
            'subtype': 'region',
            'country': 'GB',
            'parent_division_id': '0858d7df-5c32-7ea6-ffff-bbdc93f01c1b',
            'geometry': 'POLYGON((-7 55, -7 59, 0 59, 0 55, -7 55))'
        },
        # Canada boundaries
        {
            'id': 'ca_country',
            'names': {'primary': 'Canada'},
            'subtype': 'country',
            'country': 'CA',
            'parent_division_id': None,
            'geometry': 'POLYGON((-141 42, -141 70, -52 70, -52 42, -141 42))'
        },
        {
            'id': 'ca_on_province',
            'names': {'primary': 'Ontario'},
            'subtype': 'region',
            'country': 'CA',
            'parent_division_id': 'ca_country',
            'geometry': 'POLYGON((-95 42, -95 57, -74 57, -74 42, -95 42))'
        },
        {
            'id': 'ca_bc_province',
            'names': {'primary': 'British Columbia'},
            'subtype': 'region',
            'country': 'CA',
            'parent_division_id': 'ca_country',
            'geometry': 'POLYGON((-139 48, -139 60, -114 60, -114 48, -139 48))'
        },
    ]

    # Create table with proper structure (quote reserved keyword 'primary')
    conn.execute("""
        CREATE TABLE boundaries (
            id VARCHAR,
            names STRUCT("primary" VARCHAR),
            subtype VARCHAR,
            country VARCHAR,
            parent_division_id VARCHAR,
            geometry GEOMETRY
        )
    """)

    # Insert data
    for row in sample_data:
        parent_division_id = row.get('parent_division_id', None)
        conn.execute("""
            INSERT INTO boundaries VALUES (?, ?, ?, ?, ?, ST_GeomFromText(?))
        """, [
            row['id'],
            row['names'],
            row['subtype'],
            row['country'],
            parent_division_id,
            row['geometry']
        ])

    # Export to Parquet
    conn.execute(f"COPY boundaries TO '{output_path}' (FORMAT PARQUET)")

    print(f"✓ Test data generated: {output_path}")
    print(f"  - {len(sample_data)} boundaries")
    print(f"  - Countries: US, GB, CA")
    print(f"  - Subtypes: country, region, county")
    print(f"  - Includes IDs matching test fixtures")

    conn.close()


if __name__ == "__main__":
    import os
    os.makedirs("./tests", exist_ok=True)
    generate_test_parquet()
