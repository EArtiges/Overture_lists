"""
Overture Admin Boundary Tools

Home page for Overture Maps administrative boundary tools.
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Overture Boundary Tools",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Overture Admin Boundary Tools")

st.write("""
Welcome to the Overture Admin Boundary Tools! This application provides three complementary tools
for working with administrative boundaries from Overture Maps Foundation data.
""")

st.write("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📋 List Builder")
    st.write("""
    Create and manage lists of administrative boundaries.

    **Features:**
    - Hierarchical boundary selection
    - Interactive map visualization
    - Save and load boundary lists
    - Download lists as JSON files

    **Use Case:** Building collections of administrative regions for analysis or reporting.
    """)
    st.info("👈 Navigate to **List Builder** from the sidebar")

with col2:
    st.subheader("🏢 CRM Mapping")
    st.write("""
    Map Overture divisions to your CRM accounts with custom metadata.

    **Features:**
    - Hierarchical division navigation
    - Assign System ID, Account Name, Admin Level
    - Export as JSON (with geometry) or CSV

    **Use Case:** Linking geographic territories to CRM accounts and sales regions.
    """)
    st.info("👈 Navigate to **CRM Mapping** from the sidebar")

with col3:
    st.subheader("📋 CRM Client List")
    st.write("""
    Build targeted lists from your pre-mapped CRM clients.

    **Features:**
    - Country-based client filtering
    - Territory map visualization
    - Build and export client lists
    - JSON export for downstream use

    **Use Case:** Creating targeted client lists for campaigns, analysis, or reporting.
    """)
    st.info("👈 Navigate to **CRM Client List** from the sidebar")

st.write("---")

st.subheader("🚀 Getting Started")

st.write("""
1. **Choose a tool** from the sidebar navigation
2. **Select** geographic divisions or CRM clients
3. **Visualize** territories on the interactive map
4. **Export** your work as needed

The three tools work together in a complete workflow:
- **List Builder**: Curate collections of Overture boundaries
- **CRM Mapping**: Link boundaries to your CRM accounts with custom metadata
- **CRM Client List**: Build targeted lists from your mapped clients
""")

st.write("---")

st.subheader("📊 Data Source")
st.write("""
This application uses [Overture Maps Foundation](https://overturemaps.org/) administrative divisions data.
The data includes countries and their hierarchical administrative subdivisions (regions, provinces,
districts, etc.) with accurate geometries and metadata.
""")

st.caption("Built with Streamlit • Powered by Overture Maps Foundation • Data processing via DuckDB")
