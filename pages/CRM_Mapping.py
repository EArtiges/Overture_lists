"""
CRM Account Mapping

Map Overture administrative divisions to CRM accounts with custom metadata.
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from typing import Optional, Dict
import os
import json

from src.query_engine import create_query_engine
from src.list_storage import ListStorage
from src.crm_mapping_storage import CRMMappingStorage
from src.components import render_boundary_selector, render_map_section
import sqlite3

page_title = "CRM Account Mapping"
page_emoji = "🏢"
st.set_page_config(
    page_title=page_title,
    page_icon=page_emoji,
    layout="wide"
)


def init_session_state():
    """Initialize session state variables for CRM mapping."""
    if 'selected_boundary' not in st.session_state:
        st.session_state.selected_boundary = None

    if 'parquet_path' not in st.session_state:
        st.session_state.parquet_path = os.getenv(
            'OVERTURE_PARQUET_PATH',
            's3://overturemaps-us-west-2/release/2025-12-17.0/theme=divisions/type=division/*.parquet'
        )

    if 'query_engine' not in st.session_state:
        st.session_state.query_engine = None

    if 'division_selections' not in st.session_state:
        st.session_state.division_selections = []


def render_mapping_form(storage: CRMMappingStorage):
    """Render the form to add CRM account mappings."""
    st.subheader("🏢 Map to CRM Account")

    if st.session_state.selected_boundary is None:
        st.info("Select and display a boundary on the map first")
        return

    selected = st.session_state.selected_boundary

    st.write(f"**Mapping Division:** {selected['name']} ({selected['subtype']})")
    st.write(f"**Overture Division ID:** `{selected['division_id']}`")

    # Check if already mapped
    existing_by_division = storage.get_mapping_by_division_id(selected['division_id'])
    if existing_by_division:
        st.warning(f"⚠️ This division is already mapped to CRM ID: **{existing_by_division['system_id']}** ({existing_by_division['account_name']})")
        if st.button("🗑️ Remove Existing Mapping", use_container_width=True):
            storage.delete_mapping(existing_by_division['id'])
            st.success("Mapping removed")
            st.rerun()
        return

    col1, col2 = st.columns(2)

    with col1:
        custom_id = st.text_input(
            "Your System ID",
            placeholder="e.g., ACC-12345",
            key="crm_custom_id",
            help="The ID from your CRM or internal system"
        )

        account_name = st.text_input(
            "Account Name",
            placeholder="e.g., Acme Corporation - West Region",
            key="crm_account_name",
            help="The name of the account in your CRM"
        )

    with col2:
        custom_admin_level = st.text_input(
            "Custom Admin Level",
            placeholder="e.g., Sales Territory, Region, District",
            key="crm_custom_admin_level",
            help="Your custom classification for this administrative level"
        )

    st.write("---")

    if st.button("➕ Add Mapping", type="primary", use_container_width=True):
        # Validation
        if not custom_id.strip():
            st.error("Please enter a System ID")
        elif not account_name.strip():
            st.error("Please enter an Account Name")
        elif not custom_admin_level.strip():
            st.error("Please enter a Custom Admin Level")
        else:
            # Try to add the mapping (DB will enforce 1:1 constraints)
            try:
                storage.add_mapping(
                    system_id=custom_id.strip(),
                    account_name=account_name.strip(),
                    custom_admin_level=custom_admin_level.strip(),
                    division_id=selected['division_id'],
                    division_name=selected['name'],
                    overture_subtype=selected['subtype'],
                    country=selected['country']
                )
                st.success(f"✅ Added mapping for {selected['name']}")
                st.rerun()
            except sqlite3.IntegrityError as e:
                error_msg = str(e)
                if 'system_id' in error_msg:
                    # Check which division this system_id is mapped to
                    existing = storage.get_mapping_by_system_id(custom_id.strip())
                    if existing:
                        st.error(f"❌ CRM ID **{custom_id.strip()}** is already mapped to division: **{existing['division_name']}** ({existing['division_id']})")
                    else:
                        st.error(f"❌ CRM ID **{custom_id.strip()}** already exists in database")
                elif 'division_id' in error_msg:
                    st.error(f"❌ Division **{selected['name']}** is already mapped to another CRM account")
                else:
                    st.error(f"❌ Cannot add mapping: {error_msg}")


def render_mappings_table(storage: CRMMappingStorage):
    """Render the table of current CRM mappings."""
    st.subheader("📊 Current Mappings")

    mappings = storage.get_all_mappings()

    if not mappings:
        st.info("No mappings added yet. Select a division and add mapping details above.")
        return

    st.write(f"**Total Mappings:** {len(mappings)}")

    # Create DataFrame for display
    df = pd.DataFrame(mappings)

    # Reorder columns for better display
    display_columns = [
        'system_id',
        'account_name',
        'custom_admin_level',
        'division_id',
        'division_name',
        'overture_subtype',
        'country'
    ]
    df_display = df[display_columns]

    # Display table
    st.dataframe(
        df_display,
        hide_index=True,
        use_container_width=True
    )

    # Delete individual mapping
    st.write("---")
    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button("🗑️ Delete Mapping", use_container_width=True):
            st.session_state.show_delete_dialog = True

    if st.session_state.get('show_delete_dialog', False):
        mapping_options = [f"{m['system_id']} - {m['account_name']}" for m in mappings]
        selected_to_delete = st.selectbox(
            "Select mapping to delete",
            options=mapping_options,
            key="delete_mapping_select"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Confirm Delete", type="primary", use_container_width=True):
                # Find the mapping to delete
                idx = mapping_options.index(selected_to_delete)
                mapping_id = mappings[idx]['id']
                storage.delete_mapping(mapping_id)
                st.session_state.show_delete_dialog = False
                st.success("Mapping deleted")
                st.rerun()

        with col_b:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_delete_dialog = False
                st.rerun()


def render_download_section(storage: CRMMappingStorage):
    """Render the download functionality."""
    st.write("---")
    st.subheader("💾 Download Mappings")

    mappings = storage.get_all_mappings()

    if not mappings:
        st.info("No mappings to download yet.")
        return

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.write(f"**Ready to download {len(mappings)} mappings**")

    with col2:
        # JSON download (without DB metadata)
        export_data = storage.export_to_json_format()
        json_str = json.dumps(export_data, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name="crm_mappings.json",
            mime="application/json",
            use_container_width=True,
            help="Export all mappings as JSON"
        )

    with col3:
        # CSV download (basic fields only)
        export_df = pd.DataFrame(export_data)
        csv_columns = ['division_id', 'system_id', 'account_name', 'custom_admin_level']
        csv_df = export_df[csv_columns]
        csv_str = csv_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_str,
            file_name="crm_mappings.csv",
            mime="text/csv",
            use_container_width=True,
            help="Basic fields only"
        )

    # Clear all button
    st.write("")
    if st.button("🗑️ Clear All Mappings", use_container_width=False):
        if storage.clear_all_mappings():
            st.session_state.selected_boundary = None
            st.session_state.division_selections = []
            st.success("All mappings cleared")
            st.rerun()


def main():
    """Main application entry point."""
    init_session_state()

    # Title
    st.title(page_emoji + " " + page_title)
    st.write(
        "Map Overture administrative divisions to your CRM accounts with custom metadata. "
        "Select divisions using the hierarchical navigator, view them on the map, and assign "
        "your own IDs, account names, and admin levels."
    )

    # Initialize CRM Mapping Storage
    mapping_storage = CRMMappingStorage(db_path="./data/crm_mappings.db")

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

        # Display mapping stats
        st.subheader("📊 Mapping Statistics")
        mapping_count = mapping_storage.get_count()
        st.metric("Total Mappings", mapping_count)

    # Initialize query engine (or recreate if path changed)
    if (st.session_state.query_engine is None or
        st.session_state.query_engine.parquet_path != st.session_state.parquet_path):
        try:
            st.session_state.query_engine = create_query_engine(st.session_state.parquet_path)
        except Exception as e:
            st.error(f"Error initializing query engine: {e}")
            st.stop()

    # Main layout
    col1, col2 = st.columns([1, 2])

    with col1:
        render_boundary_selector(st.session_state.query_engine)

    with col2:
        render_map_section(st.session_state.query_engine, st.session_state.get('selected_boundary'))

    st.write("---")

    # Mapping form
    render_mapping_form(mapping_storage)

    # Mappings table
    render_mappings_table(mapping_storage)

    # Download section
    render_download_section(mapping_storage)


if __name__ == "__main__":
    main()
