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

    # Create sample data matching Overture schema
    sample_data = [
        # United States boundaries
        {
            'id': 'us_country',
            'names': {'primary': 'United States'},
            'admin_level': 2,
            'country': 'US',
            'geometry': 'POLYGON((-125 25, -125 49, -66 49, -66 25, -125 25))'
        },
        {
            'id': 'us_ca_state',
            'names': {'primary': 'California'},
            'admin_level': 4,
            'country': 'US',
            'parent_id': 'us_country',
            'geometry': 'POLYGON((-124.4 32.5, -124.4 42, -114.1 42, -114.1 32.5, -124.4 32.5))'
        },
        {
            'id': 'us_or_state',
            'names': {'primary': 'Oregon'},
            'admin_level': 4,
            'country': 'US',
            'parent_id': 'us_country',
            'geometry': 'POLYGON((-124.5 42, -124.5 46.2, -116.5 46.2, -116.5 42, -124.5 42))'
        },
        {
            'id': 'us_wa_state',
            'names': {'primary': 'Washington'},
            'admin_level': 4,
            'country': 'US',
            'parent_id': 'us_country',
            'geometry': 'POLYGON((-124.8 45.5, -124.8 49, -116.9 49, -116.9 45.5, -124.8 45.5))'
        },
        {
            'id': 'us_ca_la_county',
            'names': {'primary': 'Los Angeles County'},
            'admin_level': 6,
            'country': 'US',
            'parent_id': 'us_ca_state',
            'geometry': 'POLYGON((-118.9 33.7, -118.9 34.8, -117.6 34.8, -117.6 33.7, -118.9 33.7))'
        },
        {
            'id': 'us_ca_sf_county',
            'names': {'primary': 'San Francisco County'},
            'admin_level': 6,
            'country': 'US',
            'parent_id': 'us_ca_state',
            'geometry': 'POLYGON((-122.5 37.7, -122.5 37.8, -122.3 37.8, -122.3 37.7, -122.5 37.7))'
        },
        # United Kingdom boundaries
        {
            'id': 'gb_country',
            'names': {'primary': 'United Kingdom'},
            'admin_level': 2,
            'country': 'GB',
            'geometry': 'POLYGON((-8 50, -8 60, 2 60, 2 50, -8 50))'
        },
        {
            'id': 'gb_eng_region',
            'names': {'primary': 'England'},
            'admin_level': 4,
            'country': 'GB',
            'parent_id': 'gb_country',
            'geometry': 'POLYGON((-6 50, -6 55, 2 55, 2 50, -6 50))'
        },
        {
            'id': 'gb_sct_region',
            'names': {'primary': 'Scotland'},
            'admin_level': 4,
            'country': 'GB',
            'parent_id': 'gb_country',
            'geometry': 'POLYGON((-7 55, -7 59, 0 59, 0 55, -7 55))'
        },
        # Canada boundaries
        {
            'id': 'ca_country',
            'names': {'primary': 'Canada'},
            'admin_level': 2,
            'country': 'CA',
            'geometry': 'POLYGON((-141 42, -141 70, -52 70, -52 42, -141 42))'
        },
        {
            'id': 'ca_on_province',
            'names': {'primary': 'Ontario'},
            'admin_level': 4,
            'country': 'CA',
            'parent_id': 'ca_country',
            'geometry': 'POLYGON((-95 42, -95 57, -74 57, -74 42, -95 42))'
        },
        {
            'id': 'ca_bc_province',
            'names': {'primary': 'British Columbia'},
            'admin_level': 4,
            'country': 'CA',
            'parent_id': 'ca_country',
            'geometry': 'POLYGON((-139 48, -139 60, -114 60, -114 48, -139 48))'
        },
    ]

    # Create table with proper structure
    conn.execute("""
        CREATE TABLE boundaries (
            id VARCHAR,
            names STRUCT(primary VARCHAR),
            admin_level INTEGER,
            country VARCHAR,
            parent_id VARCHAR,
            geometry GEOMETRY
        )
    """)

    # Insert data
    for row in sample_data:
        parent_id = row.get('parent_id', None)
        conn.execute("""
            INSERT INTO boundaries VALUES (?, ?, ?, ?, ?, ST_GeomFromText(?))
        """, [
            row['id'],
            row['names'],
            row['admin_level'],
            row['country'],
            parent_id,
            row['geometry']
        ])

    # Export to Parquet
    conn.execute(f"COPY boundaries TO '{output_path}' (FORMAT PARQUET)")

    print(f"✓ Test data generated: {output_path}")
    print(f"  - {len(sample_data)} boundaries")
    print(f"  - Countries: US, GB, CA")
    print(f"  - Admin levels: 2 (country), 4 (state/province), 6 (county)")

    conn.close()


if __name__ == "__main__":
    import os
    os.makedirs("./tests", exist_ok=True)
    generate_test_parquet()
