"""
Overture Admin Boundary List Builder

A Streamlit application for creating and managing lists of administrative
boundaries from Overture Maps Foundation data.
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from typing import Optional, Dict
import os
from src.query_engine import create_query_engine
from src.database import Database
from src.components import render_boundary_selector, render_map_section
page_title = "Overture Admin Boundary List Builder"
page_emoji = "🗺️"
st.set_page_config(
    page_title=page_title,
    page_icon=page_emoji,
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
        st.session_state.current_list['list_name'] = list_name
        description = st.text_area(
            "Description",
            value=st.session_state.current_list['description'],
            placeholder="e.g., Sales territories for Q1 2026",
            key="description_input",
            height=100
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
        # Detect removed rows
        if len(edited_df) < len(df):
            st.session_state.current_list['boundaries'] = edited_df.to_dict('records')
            st.rerun()
    else:
        st.info("No boundaries added yet. Select and add boundaries using the filters above.")
def render_save_section(storage: Database):
    """Render the save functionality."""
    col1, col2, col3 = st.columns([2, 1, 1])
        st.write("### 💾 Save List")
        if st.button("🗑️ Clear List", use_container_width=True):
            st.session_state.current_list = {
                'list_name': '',
                'description': '',
                'boundaries': []
            }
            st.session_state.selected_boundary = None
            st.success("List cleared")
    with col3:
        if st.button("💾 Save List", type="primary", use_container_width=True):
            # Validation
            if not st.session_state.current_list['list_name'].strip():
                st.error("Please enter a list name")
            elif not st.session_state.current_list['boundaries']:
                st.error("Cannot save an empty list")
                # Save the list
                list_id = storage.save_list(
                    list_name=st.session_state.current_list['list_name'],
                    description=st.session_state.current_list['description'],
                    boundaries=st.session_state.current_list['boundaries']
                )
                st.success(f"List saved successfully! ID: {list_id}")
                st.rerun()
def render_saved_lists_sidebar(storage: Database):
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
def main():
    """Main application entry point."""
    init_session_state()
    # Title
    st.title(page_emoji + " " + page_title)
    st.write("Create and manage lists of administrative boundaries from Overture Maps data")
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        # Parquet path configuration
        parquet_path = st.text_input(
            "Parquet Data Path",
            value=st.session_state.parquet_path,
            help="Path or URL to Overture Maps admin boundary Parquet files"
        st.session_state.parquet_path = parquet_path
        st.write("---")
        # Initialize components
        storage = Database()
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
    # Map visualization section (uses st.session_state.selected_boundary)
    render_map_section(st.session_state.query_engine, st.session_state.get('selected_boundary'))
    # List management section
    render_list_management()
    # Save section
    render_save_section(storage)
    # Footer
    st.caption("Powered by Overture Maps Foundation • Built with Streamlit & DuckDB")
if __name__ == "__main__":
    main()
