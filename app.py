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
Welcome to the Overture Admin Boundary Tools! This application provides two main functionalities
for working with administrative boundaries from Overture Maps Foundation data.
""")

st.write("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 List Builder")
    st.write("""
    Create and manage lists of administrative boundaries.

    **Features:**
    - Hierarchical boundary selection via cascading dropdowns
    - Interactive map visualization
    - Save and load boundary lists
    - Download lists as JSON files
    - Manage multiple saved lists

    **Use Case:** Building collections of administrative regions for analysis,
    reporting, or data processing workflows.
    """)
    st.info("👈 Navigate to **List Builder** from the sidebar to get started")

with col2:
    st.subheader("🏢 CRM Mapping")
    st.write("""
    Map Overture divisions to your CRM accounts with custom metadata.

    **Features:**
    - Select divisions using hierarchical navigation
    - Visualize boundaries on interactive map
    - Assign custom fields: System ID, Account Name, Admin Level
    - Build multiple mappings in one session
    - Export as JSON or CSV with Overture division IDs

    **Use Case:** Linking geographic territories to CRM accounts, sales regions,
    or organizational structures.
    """)
    st.info("👈 Navigate to **CRM Mapping** from the sidebar to get started")

st.write("---")

st.subheader("🚀 Getting Started")

st.write("""
1. **Choose a tool** from the sidebar navigation
2. **Select a country** and drill down through administrative divisions
3. **Visualize** boundaries on the interactive map
4. **Save or export** your work as needed

Both tools use the same data source and hierarchical navigation, but serve different purposes:
- **List Builder** is for curating collections of boundaries
- **CRM Mapping** is for linking boundaries to your business data
""")

st.write("---")

st.subheader("📊 Data Source")
st.write("""
This application uses [Overture Maps Foundation](https://overturemaps.org/) administrative divisions data.
The data includes countries and their hierarchical administrative subdivisions (regions, provinces,
districts, etc.) with accurate geometries and metadata.
""")

st.caption("Built with Streamlit • Powered by Overture Maps Foundation • Data processing via DuckDB")
