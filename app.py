"""
Overture Admin Boundary List Builder

A Streamlit application for creating and managing lists of administrative
boundaries from Overture Maps Foundation data.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, Dict
import os
import json

from src.query_engine import create_query_engine
from src.list_storage import ListStorage


# Page configuration
st.set_page_config(
    page_title="Overture Boundary List Builder",
    page_icon="🗺️",
    layout="wide"
)


def init_session_state():
    """Initialize session state variables."""
    if 'current_list' not in st.session_state:
        st.session_state.current_list = {
            'list_name': '',
            'description': '',
            'boundaries': []
        }

    if 'selected_boundary' not in st.session_state:
        st.session_state.selected_boundary = None

    if 'parquet_path' not in st.session_state:
        # Default path - can be overridden via environment variable
        st.session_state.parquet_path = os.getenv(
            'OVERTURE_PARQUET_PATH',
            's3://overturemaps-us-west-2/release/2025-12-17.0/theme=divisions/type=division/*.parquet'
        )

    # Query engine instance (stateful)
    if 'query_engine' not in st.session_state:
        st.session_state.query_engine = None

    # UI state
    if 'show_divisions' not in st.session_state:
        st.session_state.show_divisions = False


def create_map(geometry_data: Optional[Dict] = None) -> go.Figure:
    """
    Create a Plotly Mapbox map with optional boundary geometry.

    Args:
        geometry_data: Dict with 'geometry' (GeoJSON) and 'name' keys

    Returns:
        Plotly Figure object
    """
    if geometry_data is None:
        # Default world view
        fig = go.Figure(go.Scattermapbox())
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=20, lon=0),
                zoom=1
            ),
            height=500,
            margin=dict(l=0, r=0, t=0, b=0)
        )
    else:
        # Create GeoJSON feature
        geojson_feature = {
            "type": "Feature",
            "geometry": geometry_data['geometry'],
            "properties": {"name": geometry_data['name']}
        }

        # Calculate center from geometry bounds
        coords = []
        if geometry_data['geometry']['type'] == 'Polygon':
            coords = geometry_data['geometry']['coordinates'][0]
        elif geometry_data['geometry']['type'] == 'MultiPolygon':
            for polygon in geometry_data['geometry']['coordinates']:
                coords.extend(polygon[0])

        if coords:
            lats = [c[1] for c in coords]
            lons = [c[0] for c in coords]
            center_lat = (min(lats) + max(lats)) / 2
            center_lon = (min(lons) + max(lons)) / 2

            # Calculate zoom level based on bounds
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            max_range = max(lat_range, lon_range)
            zoom = 10 - (max_range * 10)  # Simple heuristic
            zoom = max(1, min(15, zoom))  # Clamp between 1 and 15
        else:
            center_lat, center_lon, zoom = 20, 0, 2

        # Create choropleth map
        fig = go.Figure(go.Choroplethmapbox(
            geojson=geojson_feature,
            locations=[0],
            z=[1],
            colorscale=[[0, '#3388ff'], [1, '#3388ff']],
            showscale=False,
            marker=dict(opacity=0.5, line=dict(width=2, color='#0066cc')),
            hovertemplate=f"<b>{geometry_data['name']}</b><extra></extra>"
        ))

        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=zoom
            ),
            height=500,
            margin=dict(l=0, r=0, t=0, b=0)
        )

    return fig


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
        fig = create_map()
    else:
        with st.spinner(f"Loading geometry for {selected_boundary['name']}..."):
            geometry_data = query_engine.get_geometry(selected_boundary['division_id'])
            selected_boundary["geometry"] = geometry_data

            if geometry_data is None:
                st.warning(f"Could not load geometry for {selected_boundary['name']}")
                st.info(f"Selected: **{selected_boundary['name']}** ({selected_boundary['subtype']})")
                fig = create_map()
            else:
                st.success(f"Displaying: **{selected_boundary['name']}** ({selected_boundary['subtype']})")
                fig = create_map(selected_boundary)

    # Render map
    st.plotly_chart(fig, use_container_width=True)


def render_list_management():
    """Render the list management section (add button, review table)."""
    st.subheader("📋 Current List")

    col1, col2 = st.columns([3, 1])

    with col1:
        # List name and description
        list_name = st.text_input(
            "List Name",
            value=st.session_state.current_list['list_name'],
            placeholder="e.g., West Coast States",
            key="list_name_input"
        )
        st.session_state.current_list['list_name'] = list_name

        description = st.text_area(
            "Description",
            value=st.session_state.current_list['description'],
            placeholder="e.g., Sales territories for Q1 2026",
            key="description_input",
            height=100
        )
        st.session_state.current_list['description'] = description

    with col2:
        st.write("")  # Spacing
        st.write("")
        # Add to list button
        if st.button("➕ Add to List", type="primary", use_container_width=True):
            if st.session_state.selected_boundary is not None:
                # Check if already in list
                division_id = st.session_state.selected_boundary['division_id']
                if not any(b['division_id'] == division_id for b in st.session_state.current_list['boundaries']):
                    st.session_state.current_list['boundaries'].append(
                        st.session_state.selected_boundary
                    )
                    st.success(f"Added {st.session_state.selected_boundary['name']} to list")
                    st.rerun()
                else:
                    st.warning("This boundary is already in the list")
            else:
                st.warning("Please select a boundary first")

    # Display current list as table
    st.write("---")
    if st.session_state.current_list['boundaries']:
        st.write(f"**Boundaries in list:** {len(st.session_state.current_list['boundaries'])}")

        # Create DataFrame for display
        df = pd.DataFrame(st.session_state.current_list['boundaries'])

        # Add remove buttons using st.data_editor with delete option
        edited_df = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            disabled=True,
            num_rows="dynamic",
            key="boundaries_table"
        )

        # Detect removed rows
        if len(edited_df) < len(df):
            st.session_state.current_list['boundaries'] = edited_df.to_dict('records')
            st.rerun()

    else:
        st.info("No boundaries added yet. Select and add boundaries using the filters above.")


def render_save_section(storage: ListStorage):
    """Render the save functionality."""
    st.write("---")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.write("### 💾 Save List")

    with col2:
        if st.button("🗑️ Clear List", use_container_width=True):
            st.session_state.current_list = {
                'list_name': '',
                'description': '',
                'boundaries': []
            }
            st.session_state.selected_boundary = None
            st.success("List cleared")
            st.rerun()

    with col3:
        if st.button("💾 Save List", type="primary", use_container_width=True):
            # Validation
            if not st.session_state.current_list['list_name'].strip():
                st.error("Please enter a list name")
            elif not st.session_state.current_list['boundaries']:
                st.error("Cannot save an empty list")
            else:
                # Save the list
                list_id = storage.save_list(
                    list_name=st.session_state.current_list['list_name'],
                    description=st.session_state.current_list['description'],
                    boundaries=st.session_state.current_list['boundaries']
                )
                st.success(f"List saved successfully! ID: {list_id}")
                st.rerun()


def render_saved_lists_sidebar(storage: ListStorage):
    """Render saved lists in sidebar."""
    st.sidebar.header("📚 Saved Lists")

    saved_lists = storage.list_all_lists()

    if not saved_lists:
        st.sidebar.info("No saved lists yet")
        return

    for list_info in saved_lists:
        with st.sidebar.expander(f"📄 {list_info['list_name']}"):
            st.write(f"**Boundaries:** {list_info['boundary_count']}")
            st.write(f"**Created:** {list_info['created_at'][:10]}")
            if list_info['description']:
                st.write(f"**Description:** {list_info['description']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load", key=f"load_{list_info['list_id']}", use_container_width=True):
                    loaded_list = storage.load_list(list_info['list_id'])
                    if loaded_list:
                        st.session_state.current_list = {
                            'list_name': loaded_list['list_name'],
                            'description': loaded_list['description'],
                            'boundaries': loaded_list['boundaries']
                        }
                        st.success(f"Loaded: {loaded_list['list_name']}")
                        st.rerun()

            with col2:
                if st.button("Delete", key=f"delete_{list_info['list_id']}", use_container_width=True):
                    if storage.delete_list(list_info['list_id']):
                        st.success("Deleted")
                        st.rerun()

            # Download button
            loaded_list = storage.load_list(list_info['list_id'])
            if loaded_list:
                import json
                json_str = json.dumps(loaded_list, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📥 Download",
                    data=json_str,
                    file_name=f"{list_info['list_name'].replace(' ', '_')}.json",
                    mime="application/json",
                    key=f"download_{list_info['list_id']}",
                    use_container_width=True
                )


def main():
    """Main application entry point."""
    init_session_state()

    # Title
    st.title("🗺️ Overture Admin Boundary List Builder")
    st.write("Create and manage lists of administrative boundaries from Overture Maps data")

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Parquet path configuration
        parquet_path = st.text_input(
            "Parquet Data Path",
            value=st.session_state.parquet_path,
            help="Path or URL to Overture Maps admin boundary Parquet files"
        )
        st.session_state.parquet_path = parquet_path

        st.write("---")

        # Initialize components
        storage = ListStorage(data_dir="./list_data")

        # Show saved lists
        render_saved_lists_sidebar(storage)

    # Initialize query engine (or recreate if path changed)
    if (st.session_state.query_engine is None or
        st.session_state.query_engine.parquet_path != st.session_state.parquet_path):
        try:
            st.session_state.query_engine = create_query_engine(st.session_state.parquet_path)
        except Exception as e:
            st.error(f"Error initializing query engine: {e}")
            st.stop()

    # Main content
    # Boundary selection section
    render_boundary_selector(st.session_state.query_engine)

    st.write("---")

    # Map visualization section (uses st.session_state.selected_boundary)
    render_map_section(st.session_state.query_engine, st.session_state.get('selected_boundary'))

    st.write("---")

    # List management section
    render_list_management()

    # Save section
    render_save_section(storage)

    # Footer
    st.write("---")
    st.caption("Powered by Overture Maps Foundation • Built with Streamlit & DuckDB")


if __name__ == "__main__":
    main()
