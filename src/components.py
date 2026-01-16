
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

    # Step 1: Country selection
    countries = query_engine.get_countries()
    if not countries:
        st.warning("No countries found. Please check your Parquet data path.")
        return None

    selected_country = st.selectbox(
        "Select Country",
        options=[""] + countries,
        key="country_select"
    )

    # Reset if country changes
    if 'previous_country' not in st.session_state:
        st.session_state.previous_country = None
    if selected_country != st.session_state.previous_country:
        st.session_state.previous_country = selected_country
        st.session_state.division_selections = []
        st.session_state.selected_boundary = None

    if not selected_country:
        st.info("Select a country to begin")
        return None

    # Get the country division_id
    country_division = query_engine.get_country_division(selected_country)
    if not country_division:
        st.error(f"Could not find country division for {selected_country}")
        return None

    # Step 2: Cascading division dropdowns based on parent_division_id
    current_parent_id = country_division['division_id']
    level = 0

    while True:
        # Query children of current parent (always using get_child_divisions)
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
            # Truncate selections beyond this level
            st.session_state.division_selections = st.session_state.division_selections[:level]
            break

        # Get selected division
        selected_division = divisions_df.iloc[selected_idx - 1].to_dict()

        # Update selections list
        if level < len(st.session_state.division_selections):
            # User changed selection at this level - truncate
            st.session_state.division_selections = st.session_state.division_selections[:level]

        if level == len(st.session_state.division_selections):
            # New selection at this level
            st.session_state.division_selections.append(selected_division)

        # Move to next level
        current_parent_id = selected_division['division_id']
        level += 1

    # Show breadcrumb
    if st.session_state.division_selections:
        st.write("---")
        breadcrumb = selected_country + " → " + " → ".join([
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

