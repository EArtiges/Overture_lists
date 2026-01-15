"""
Overture Admin Boundary List Builder

A Streamlit application for creating and managing lists of administrative
boundaries from Overture Maps Foundation data.
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from typing import Optional, Dict
import os

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
    if 'show_final_dropdown' not in st.session_state:
        st.session_state.show_final_dropdown = False

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
    # TODO get the country division_id

    # Reset if country changes
    if 'previous_country' not in st.session_state:
        st.session_state.previous_country = None
    if selected_country != st.session_state.previous_country:
        st.session_state.previous_country = selected_country
        st.session_state.division_selections = []
        st.session_state.show_final_dropdown = False

    if not selected_country:
        st.info("Select a country to begin")
        return None

    # Step 2: Cascading division dropdowns based on parent_division_id
    current_parent_id = None  # TODO that should be the country id found above
    level = 0

    while True:
        # Query children of current parent
        # TODO this is now always the same function call: query_engine.get_child_divisions(current_parent_id)
        if current_parent_id is None:
            # Get top-level divisions for country
            divisions_df = query_engine.get_top_level_divisions(selected_country)
        else:
            # Get children of selected parent
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

    # Step 3: "Query all at this level" button
    st.write("---")
    if st.button("🔍 Query All at This Level", use_container_width=True, type="primary"):
        st.session_state.show_final_dropdown = True
        st.rerun()

    # Step 4: Final selection dropdown (created by button)
    if st.session_state.show_final_dropdown:
        # Query divisions at current level
        if not st.session_state.division_selections:
            # At country level - show top-level divisions
            final_divisions = query_engine.get_top_level_divisions(selected_country)
        else:
            # Show children of last selected division
            last_division = st.session_state.division_selections[-1]
            final_divisions = query_engine.get_child_divisions(last_division['division_id'])

        if final_divisions.empty:
            st.info("No divisions at this level")
        else:
            st.write("---")
            st.write(f"**Select a division to view ({len(final_divisions)} available):**")

            final_options = [""] + [
                f"{row['name']} ({row['subtype']})"
                for _, row in final_divisions.iterrows()
            ]

            final_idx = st.selectbox(
                "Pick a division",
                options=range(len(final_options)),
                format_func=lambda x: final_options[x] if final_options[x] else "Select...",
                key="final_division_select"
            )

            if final_idx > 0:
                selected_for_map = final_divisions.iloc[final_idx - 1].to_dict()

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📍 View on Map", use_container_width=True):
                        st.session_state.show_final_dropdown = False
                        return selected_for_map

                with col2:
                    if st.button("⬇️ Drill Into This", use_container_width=True):
                        # Add to selections and hide final dropdown
                        st.session_state.division_selections.append(selected_for_map)
                        st.session_state.show_final_dropdown = False
                        st.rerun()

    return None


def render_map_section(query_engine, selected_boundary):
    """Render the map visualization section."""
    st.subheader("🗺️ Map View")

    if selected_boundary is None:
        st.info("Select a boundary from the filters above to view it on the map")
        m = create_map()
    else:
        # Note: Geometry display temporarily disabled - division type doesn't include geometry
        # Would need to query division_area type separately
        st.info(f"Selected: **{selected_boundary['name']}** ({selected_boundary['subtype']})")
        st.session_state.selected_boundary = selected_boundary
        m = create_map()

    # Render map
    st_folium(m, width=1200, height=500, key="boundary_map")


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
    selected_boundary = render_boundary_selector(st.session_state.query_engine)

    st.write("---")

    # Map visualization section
    render_map_section(st.session_state.query_engine, selected_boundary)

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
