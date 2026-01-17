"""
List Visualizer

Visualize saved boundary and client lists on interactive maps.
View all items from a list simultaneously with color-coded layers.
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import os
from typing import List, Dict, Optional

from src.list_database_storage import ListDatabaseStorage
from src.query_engine import create_query_engine

# Constants
page_title = "List Visualizer"
page_emoji = "🗺️"
MAX_ITEMS_ON_MAP = 50
ITEM_COLORS = [
    '#3388ff', '#ff6633', '#33cc33', '#cc33ff',
    '#ffcc00', '#00ccff', '#ff3366', '#66ff33'
]

st.set_page_config(
    page_title=page_title,
    page_icon=page_emoji,
    layout="wide"
)


def init_session_state():
    """Initialize session state variables."""
    if 'selected_list_id' not in st.session_state:
        st.session_state.selected_list_id = None

    if 'selected_list_source' not in st.session_state:
        st.session_state.selected_list_source = None

    if 'loaded_list_data' not in st.session_state:
        st.session_state.loaded_list_data = None

    if 'items_with_geometry' not in st.session_state:
        st.session_state.items_with_geometry = []

    if 'visible_items' not in st.session_state:
        st.session_state.visible_items = set()

    if 'parquet_path' not in st.session_state:
        st.session_state.parquet_path = os.getenv(
            'OVERTURE_PARQUET_PATH',
            's3://overturemaps-us-west-2/release/2025-12-17.0/theme=divisions/type=division/*.parquet'
        )

    if 'query_engine' not in st.session_state:
        st.session_state.query_engine = None


def discover_all_lists() -> List[Dict]:
    """
    Discover lists from database.

    Returns:
        List of dicts with list metadata including source information
    """
    all_lists = []

    try:
        # Get all lists from database
        db_storage = ListDatabaseStorage(db_path="./data/lists.db")
        lists = db_storage.list_all_lists()

        # Add source labels based on list_type
        for lst in lists:
            lst['source_label'] = (
                'Boundary Lists' if lst['list_type'] == 'boundary'
                else 'CRM Client Lists'
            )
            all_lists.append(lst)
    except Exception as e:
        st.error(f"Error loading lists from database: {e}")

    return all_lists


def create_multi_item_map(items_with_geometry: List[Dict]) -> folium.Map:
    """
    Create a Folium map with multiple colored layers.

    Args:
        items_with_geometry: List of dicts with 'geometry', 'name', 'color'

    Returns:
        Folium Map object
    """
    m = folium.Map()

    all_bounds = []
    has_valid_geometry = False

    for item in items_with_geometry:
        if item.get('geometry') is None:
            continue

        has_valid_geometry = True
        color = item.get('color', '#3388ff')

        geojson_feature = {
            "type": "Feature",
            "geometry": item['geometry'],
            "properties": {"name": item['name']}
        }

        geojson_layer = folium.GeoJson(
            geojson_feature,
            name=item['name'],
            style_function=lambda x, c=color: {
                'fillColor': c,
                'color': c,
                'weight': 2,
                'fillOpacity': 0.3
            },
            tooltip=folium.Tooltip(item['name'])
        )
        geojson_layer.add_to(m)

        # Collect bounds
        try:
            bounds = geojson_layer.get_bounds()
            all_bounds.extend([[bounds[0][0], bounds[0][1]],
                              [bounds[1][0], bounds[1][1]]])
        except:
            pass

    # Fit map to all geometries
    if all_bounds:
        m.fit_bounds(all_bounds)
    elif not has_valid_geometry:
        # Default world view if no geometries
        m = folium.Map(location=[20, 0], zoom_start=2)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m


def load_geometries_for_items(items: List[Dict], query_engine, visible_item_indices: set) -> List[Dict]:
    """
    Load geometry data for list items with progress tracking.

    Args:
        items: List of boundary items from the list
        query_engine: Query engine instance
        visible_item_indices: Set of indices of items to load geometry for

    Returns:
        List of items with geometry and color information
    """
    items_with_geometry = []

    # Filter to only visible items
    items_to_load = [items[i] for i in sorted(visible_item_indices) if i < len(items)]

    if not items_to_load:
        return []

    # Progress bar
    progress_text = f"Loading geometry for {len(items_to_load)} items..."
    progress_bar = st.progress(0, text=progress_text)

    for idx, item in enumerate(items_to_load):
        # Get geometry
        division_id = item.get('division_id')
        if division_id:
            geometry = query_engine.get_geometry(division_id)
        else:
            geometry = None

        # Assign color
        color = ITEM_COLORS[idx % len(ITEM_COLORS)]

        items_with_geometry.append({
            'name': item.get('name', 'Unknown'),
            'geometry': geometry,
            'color': color,
            'item': item
        })

        # Update progress
        progress = (idx + 1) / len(items_to_load)
        progress_bar.progress(progress, text=f"{progress_text} ({idx + 1}/{len(items_to_load)})")

    progress_bar.empty()
    return items_with_geometry


def render_list_selector_sidebar():
    """Render list selection interface in sidebar."""
    all_lists = discover_all_lists()

    if not all_lists:
        st.info("No saved lists found. Create lists in List Builder or CRM Client List pages.")
        return

    # Group lists by source
    boundary_lists = [l for l in all_lists if l['source_label'] == 'Boundary Lists']
    crm_lists = [l for l in all_lists if l['source_label'] == 'CRM Client Lists']

    # Create selection options
    list_options = []
    list_map = {}

    if boundary_lists:
        list_options.append("--- Boundary Lists ---")
        for lst in boundary_lists:
            key = f"{lst['source_dir']}|{lst['list_id']}"
            label = f"{lst['list_name']} ({lst['boundary_count']} items)"
            list_options.append(label)
            list_map[label] = lst

    if crm_lists:
        list_options.append("--- CRM Client Lists ---")
        for lst in crm_lists:
            key = f"{lst['source_dir']}|{lst['list_id']}"
            label = f"{lst['list_name']} ({lst['boundary_count']} items)"
            list_options.append(label)
            list_map[label] = lst

    # Selection dropdown
    selected_option = st.selectbox(
        "Select a list to visualize",
        options=[""] + list_options,
        key="list_selector"
    )

    if selected_option and not selected_option.startswith("---") and selected_option in list_map:
        selected_list = list_map[selected_option]

        # Check if selection changed
        if st.session_state.selected_list_id != selected_list['list_id']:

            # Load the list from database
            storage = ListDatabaseStorage(db_path="./data/lists.db")
            loaded_list = storage.load_list(selected_list['list_id'])

            if loaded_list:
                st.session_state.selected_list_id = selected_list['list_id']
                st.session_state.loaded_list_data = loaded_list

                # Initialize all items as visible
                st.session_state.visible_items = set(range(len(loaded_list['boundaries'])))

                # Clear cached geometries
                st.session_state.items_with_geometry = []
                st.rerun()

    elif not selected_option or selected_option.startswith("---"):
        # Clear selection
        if st.session_state.selected_list_id is not None:
            st.session_state.selected_list_id = None
            st.session_state.selected_list_source = None
            st.session_state.loaded_list_data = None
            st.session_state.items_with_geometry = []
            st.session_state.visible_items = set()
            st.rerun()

    # Show list metadata if selected
    if st.session_state.loaded_list_data:
        st.write("---")
        st.write("**List Information**")
        st.write(f"**Name:** {st.session_state.loaded_list_data['list_name']}")
        st.write(f"**Items:** {len(st.session_state.loaded_list_data['boundaries'])}")
        st.write(f"**Created:** {st.session_state.loaded_list_data['created_at'][:10]}")
        if st.session_state.loaded_list_data.get('description'):
            st.write(f"**Description:** {st.session_state.loaded_list_data['description']}")

        # Clear button
        if st.button("Clear Selection", use_container_width=True):
            st.session_state.selected_list_id = None
            st.session_state.selected_list_source = None
            st.session_state.loaded_list_data = None
            st.session_state.items_with_geometry = []
            st.session_state.visible_items = set()
            st.rerun()


def render_item_selection_table():
    """Render interactive table for selecting which items to display."""
    if not st.session_state.loaded_list_data:
        return

    boundaries = st.session_state.loaded_list_data['boundaries']

    if not boundaries:
        st.info("This list is empty.")
        return

    st.subheader("📋 List Items")

    # Create DataFrame
    df_data = []
    for idx, boundary in enumerate(boundaries):
        df_data.append({
            'Show': idx in st.session_state.visible_items,
            'Name': boundary.get('name', 'Unknown'),
            'Type': boundary.get('subtype', 'N/A'),
            'Country': boundary.get('country', 'N/A')
        })

    df = pd.DataFrame(df_data)

    # Show warning if too many items
    if len(boundaries) > MAX_ITEMS_ON_MAP:
        st.warning(f"⚠️ This list has {len(boundaries)} items. Only the first {MAX_ITEMS_ON_MAP} can be displayed on the map for performance reasons.")
        # Limit visible items
        st.session_state.visible_items = set(range(min(MAX_ITEMS_ON_MAP, len(boundaries))))
        df = df.head(MAX_ITEMS_ON_MAP)

    # Interactive table
    edited_df = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        disabled=['Name', 'Type', 'Country'],
        key="items_table"
    )

    # Update visible items based on checkboxes
    new_visible = set()
    for idx, row in edited_df.iterrows():
        if row['Show']:
            new_visible.add(idx)

    # If selection changed, clear geometry cache
    if new_visible != st.session_state.visible_items:
        st.session_state.visible_items = new_visible
        st.session_state.items_with_geometry = []
        st.rerun()

    # Show count
    st.write(f"**Selected:** {len(st.session_state.visible_items)} items")


def render_map_visualization(query_engine):
    """Render the multi-item map visualization."""
    if not st.session_state.loaded_list_data:
        st.info("Select a list from the sidebar to visualize")
        m = folium.Map(location=[20, 0], zoom_start=2)
        st_folium(m, width=1200, height=600, key="visualizer_map")
        return

    boundaries = st.session_state.loaded_list_data['boundaries']

    if not boundaries:
        st.info("This list has no items")
        m = folium.Map(location=[20, 0], zoom_start=2)
        st_folium(m, width=1200, height=600, key="visualizer_map")
        return

    if not st.session_state.visible_items:
        st.info("No items selected. Check items in the table to display them on the map.")
        m = folium.Map(location=[20, 0], zoom_start=2)
        st_folium(m, width=1200, height=600, key="visualizer_map")
        return

    st.subheader("🗺️ Map Visualization")

    # Load geometries if not cached
    if not st.session_state.items_with_geometry:
        with st.spinner("Loading map data..."):
            st.session_state.items_with_geometry = load_geometries_for_items(
                boundaries,
                query_engine,
                st.session_state.visible_items
            )

    # Check for missing geometries
    missing_count = sum(1 for item in st.session_state.items_with_geometry if item['geometry'] is None)
    valid_count = len(st.session_state.items_with_geometry) - missing_count

    if missing_count > 0:
        st.warning(f"⚠️ {missing_count} item(s) have no geometry data and will not appear on the map.")

    if valid_count > 0:
        st.success(f"✓ Displaying {valid_count} item(s) on the map")

    # Create and render map
    m = create_multi_item_map(st.session_state.items_with_geometry)
    st_folium(m, width=1200, height=600, key="visualizer_map")

    # Show legend
    if st.session_state.items_with_geometry:
        with st.expander("🎨 Color Legend", expanded=False):
            for item in st.session_state.items_with_geometry:
                if item['geometry'] is not None:
                    st.markdown(
                        f"<span style='color:{item['color']}'>●</span> {item['name']}",
                        unsafe_allow_html=True
                    )


def main():
    """Main application entry point."""
    init_session_state()

    st.title(f"{page_emoji} {page_title}")
    st.write("Visualize and explore your saved boundary and client lists on interactive maps.")

    # Sidebar
    with st.sidebar:
        st.header("📚 Select List")
        render_list_selector_sidebar()

    # Initialize query engine
    if (st.session_state.query_engine is None or
        st.session_state.query_engine.parquet_path != st.session_state.parquet_path):
        try:
            st.session_state.query_engine = create_query_engine(st.session_state.parquet_path)
        except Exception as e:
            st.error(f"Error initializing query engine: {e}")
            st.stop()

    # Main content
    if st.session_state.selected_list_id is None:
        st.info("👈 Select a list from the sidebar to begin")

        # Show example map
        m = folium.Map(location=[20, 0], zoom_start=2)
        st_folium(m, width=1200, height=400, key="empty_map")

        # Show stats about available lists
        all_lists = discover_all_lists()
        if all_lists:
            st.write("---")
            st.write(f"**Available Lists:** {len(all_lists)}")
            boundary_count = sum(1 for l in all_lists if l['source_label'] == 'Boundary Lists')
            crm_count = sum(1 for l in all_lists if l['source_label'] == 'CRM Client Lists')
            st.write(f"- Boundary Lists: {boundary_count}")
            st.write(f"- CRM Client Lists: {crm_count}")
    else:
        col1, col2 = st.columns([1, 2])

        with col1:
            render_item_selection_table()

        with col2:
            render_map_visualization(st.session_state.query_engine)

    # Footer
    st.write("---")
    st.caption("Powered by Overture Maps Foundation • Built with Streamlit & Folium")


if __name__ == "__main__":
    main()
