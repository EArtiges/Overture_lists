
import streamlit as st
import folium
from streamlit_folium import st_folium
from typing import Optional, Dict


def create_map(geometry_data: Optional[Dict] = None) -> folium.Map:
    """
    Create a Folium map with optional boundary geometry.

    Args:
        geometry_data: Dict with 'geometry' (GeoJSON) and 'name' keys

    Returns:
        Folium Map object
    """
    if geometry_data is None:
        # Default world view
        m = folium.Map(location=[20, 0], zoom_start=2)
    else:
        # Create GeoJSON feature
        geojson_feature = {
            "type": "Feature",
            "geometry": geometry_data['geometry'],
            "properties": {"name": geometry_data['name']}
        }

        # Add to map and fit bounds
        m = folium.Map()
        geojson_layer = folium.GeoJson(
            geojson_feature,
            name=geometry_data['name'],
            style_function=lambda x: {
                'fillColor': '#3388ff',
                'color': '#0066cc',
                'weight': 2,
                'fillOpacity': 0.3
            },
            tooltip=folium.Tooltip(geometry_data['name'])
        )
        geojson_layer.add_to(m)

        # Fit map to geometry bounds
        m.fit_bounds(geojson_layer.get_bounds())

    return m


def render_boundary_selector(query_engine):
    """Render hierarchical drill-down boundary selection UI."""
    st.subheader("🔍 Hierarchical Division Selection")

    # Initialize selection state
    if 'division_selections' not in st.session_state:
        st.session_state.division_selections = []

    # Level 0: Country selection (now treated as first division level)
    countries = query_engine.get_countries()
    if not countries:
        st.warning("No countries found. Please check your Parquet data path.")
        return None

    # Create country dropdown options
    country_options = [""] + [
        f"{country['name']} ({country['country']})"
        for country in countries
    ]

    selected_country_idx = st.selectbox(
        "Level 1: Select Country",
        options=range(len(country_options)),
        format_func=lambda x: country_options[x] if country_options[x] else "Select...",
        key="country_select"
    )

    # Reset if country changes
    if 'previous_country_idx' not in st.session_state:
        st.session_state.previous_country_idx = None
    if selected_country_idx != st.session_state.previous_country_idx:
        st.session_state.previous_country_idx = selected_country_idx
        st.session_state.division_selections = []
        st.session_state.selected_boundary = None

    if selected_country_idx == 0:
        st.info("Select a country to begin")
        return None

    # Get selected country division
    country_division = countries[selected_country_idx - 1]

    # Add country to selections if not already there
    if not st.session_state.division_selections or st.session_state.division_selections[0]['division_id'] != country_division['division_id']:
        st.session_state.division_selections = [country_division]

    # Cascading division dropdowns based on parent_division_id
    level = 0
    current_parent_id = country_division['division_id']

    while True:
        # Query children of current parent (skip first iteration since we already have country)
        if level > 0:
            current_parent_id = st.session_state.division_selections[level]['division_id']

        divisions_df = query_engine.get_child_divisions(current_parent_id)

        # If no divisions at this level, stop creating dropdowns
        if divisions_df.empty:
            break

        # Create dropdown for this level
        division_options = [""] + [
            f"{row['name']} ({row['subtype']})"
            for _, row in divisions_df.iterrows()
        ]

        selected_idx = st.selectbox(
            f"Level {level + 2}: Select Division",
            options=range(len(division_options)),
            format_func=lambda x: division_options[x] if division_options[x] else "Select...",
            key=f"level_{level}_dropdown"
        )

        # If nothing selected at this level, stop
        if selected_idx == 0:
            # Truncate selections beyond this level (but keep country)
            st.session_state.division_selections = st.session_state.division_selections[:level + 1]
            break

        # Get selected division
        selected_division = divisions_df.iloc[selected_idx - 1].to_dict()

        # Update selections list
        if level + 1 < len(st.session_state.division_selections):
            # User changed selection at this level - truncate
            st.session_state.division_selections = st.session_state.division_selections[:level + 1]

        if level + 1 == len(st.session_state.division_selections):
            # New selection at this level
            st.session_state.division_selections.append(selected_division)

        # Move to next level
        level += 1

    # Show breadcrumb
    if st.session_state.division_selections:
        st.write("---")
        breadcrumb = " → ".join([
            f"{div['name']} ({div['subtype']})"
            for div in st.session_state.division_selections
        ])
        st.write(f"**Path:** {breadcrumb}")

        # Show on Map button for currently selected division
        st.write("---")
        last_selected = st.session_state.division_selections[-1]
        if st.button(f"🗺️ Show {last_selected['name']} on Map", use_container_width=True, type="primary"):
            st.session_state.selected_boundary = last_selected
            st.rerun()

    return None


def render_map_section(query_engine, selected_boundary):
    """Render the map visualization section."""
    st.subheader("🗺️ Map View")

    if selected_boundary is None:
        st.info("Select a boundary from the filters above to view it on the map")
        m = create_map()
    else:
        with st.spinner(f"Loading geometry for {selected_boundary['name']}..."):
            geometry_data = query_engine.get_geometry(selected_boundary['division_id'])
            selected_boundary["geometry"] = geometry_data

            if geometry_data is None:
                st.warning(f"Could not load geometry for {selected_boundary['name']}")
                st.info(f"Selected: **{selected_boundary['name']}** ({selected_boundary['subtype']})")
                m = create_map()
            else:
                st.success(f"Displaying: **{selected_boundary['name']}** ({selected_boundary['subtype']})")
                m = create_map(selected_boundary)

    # Render map
    st_folium(m, width=1200, height=500, key="boundary_map")


def render_crm_client_selector(clients_data: list):
    """
    Render simplified 2-level selector: Country → Client.

    Args:
        clients_data: List of client dictionaries loaded from CRM client storage
    """
    st.subheader("🏢 CRM Client Selection")

    if not clients_data:
        st.warning("No CRM clients found. Please ensure clients.json exists in crm_data/ directory.")
        return

    # Extract unique countries from client data
    countries = sorted(list(set(c.get('country') for c in clients_data if c.get('country'))))

    if not countries:
        st.warning("No countries found in client data.")
        return

    # Step 1: Country selection
    selected_country = st.selectbox(
        "Select Country",
        options=[""] + countries,
        key="crm_country_select"
    )

    # Reset selected client if country changes
    if 'previous_crm_country' not in st.session_state:
        st.session_state.previous_crm_country = None
    if selected_country != st.session_state.previous_crm_country:
        st.session_state.previous_crm_country = selected_country
        st.session_state.selected_client = None

    if not selected_country:
        st.info("Select a country to view CRM clients")
        return

    # Step 2: Filter clients by country
    country_clients = [c for c in clients_data if c.get('country') == selected_country]

    if not country_clients:
        st.warning(f"No clients found for country: {selected_country}")
        return

    # Create client options (showing account name and system ID)
    client_options = [""] + [
        f"{client['account_name']} ({client['system_id']})"
        for client in country_clients
    ]

    selected_idx = st.selectbox(
        "Select Client",
        options=range(len(client_options)),
        format_func=lambda x: client_options[x] if client_options[x] else "Select...",
        key="crm_client_select"
    )

    # If nothing selected, return
    if selected_idx == 0:
        st.session_state.selected_client = None
        return

    # Get selected client
    selected_client = country_clients[selected_idx - 1]

    # Display client details
    st.write("---")
    st.write(f"**Account Name:** {selected_client['account_name']}")
    st.write(f"**System ID:** `{selected_client['system_id']}`")
    st.write(f"**Division:** {selected_client['division_name']} ({selected_client.get('overture_subtype', 'N/A')})")
    st.write(f"**Custom Admin Level:** {selected_client['custom_admin_level']}")

    # Show on Map button
    st.write("---")
    if st.button(f"🗺️ Show {selected_client['account_name']} on Map", use_container_width=True, type="primary"):
        st.session_state.selected_client = selected_client
        st.rerun()

