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
from src.components import render_boundary_selector, render_map_section

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

    if 'crm_mappings' not in st.session_state:
        st.session_state.crm_mappings = []

    if 'parquet_path' not in st.session_state:
        st.session_state.parquet_path = os.getenv(
            'OVERTURE_PARQUET_PATH',
            's3://overturemaps-us-west-2/release/2025-12-17.0/theme=divisions/type=division/*.parquet'
        )

    if 'query_engine' not in st.session_state:
        st.session_state.query_engine = None

    if 'division_selections' not in st.session_state:
        st.session_state.division_selections = []


def render_mapping_form():
    """Render the form to add CRM account mappings."""
    st.subheader("🏢 Map to CRM Account")

    if st.session_state.selected_boundary is None:
        st.info("Select and display a boundary on the map first")
        return

    selected = st.session_state.selected_boundary

    st.write(f"**Mapping Division:** {selected['name']} ({selected['subtype']})")
    st.write(f"**Overture Division ID:** `{selected['division_id']}`")

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
            # Check if this division is already mapped
            if any(m['division_id'] == selected['division_id'] for m in st.session_state.crm_mappings):
                st.warning("This division is already mapped. Remove it first to remap.")
            else:
                # Add the mapping
                mapping = {
                    'division_id': selected['division_id'],
                    'system_id': custom_id.strip(),
                    'account_name': account_name.strip(),
                    'custom_admin_level': custom_admin_level.strip(),
                    'division_name': selected['name'],
                    'overture_subtype': selected['subtype'],
                    'country': selected['country']
                }
                st.session_state.crm_mappings.append(mapping)
                st.success(f"Added mapping for {selected['name']}")
                st.rerun()


def render_mappings_table():
    """Render the table of current CRM mappings."""
    st.subheader("📊 Current Mappings")

    if not st.session_state.crm_mappings:
        st.info("No mappings added yet. Select a division and add mapping details above.")
        return

    st.write(f"**Total Mappings:** {len(st.session_state.crm_mappings)}")

    # Create DataFrame for display
    df = pd.DataFrame(st.session_state.crm_mappings)

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

    # Display with option to delete rows
    edited_df = st.data_editor(
        df_display,
        hide_index=True,
        use_container_width=True,
        disabled=True,
        num_rows="dynamic",
        key="crm_mappings_table"
    )

    # Detect removed rows
    if len(edited_df) < len(df):
        st.session_state.crm_mappings = edited_df.to_dict('records')
        st.rerun()


def render_download_section():
    """Render the download functionality."""
    st.write("---")
    st.subheader("💾 Download Mappings")

    if not st.session_state.crm_mappings:
        st.info("No mappings to download yet.")
        return

    # Create the export dataframe with only the 4 required columns
    export_df = pd.DataFrame(st.session_state.crm_mappings)
    export_columns = ['division_id', 'system_id', 'account_name', 'custom_admin_level']
    export_df = export_df[export_columns]

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.write(f"**Ready to download {len(export_df)} mappings**")

    with col2:
        # JSON download
        json_str = export_df.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name="crm_mappings.json",
            mime="application/json",
            use_container_width=True
        )

    with col3:
        # CSV download
        csv_str = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_str,
            file_name="crm_mappings.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Clear all button
    st.write("")
    if st.button("🗑️ Clear All Mappings", use_container_width=False):
        st.session_state.crm_mappings = []
        st.session_state.selected_boundary = None
        st.session_state.division_selections = []
        st.success("All mappings cleared")
        st.rerun()


def main():
    """Main application entry point."""
    st.title(page_emoji + " " + page_title)
    st.write(
        "Map Overture administrative divisions to your CRM accounts with custom metadata. "
        "Select divisions using the hierarchical navigator, view them on the map, and assign "
        "your own IDs, account names, and admin levels."
    )

    # Initialize session state
    init_session_state()

    # Initialize query engine
    if st.session_state.query_engine is None:
        with st.spinner("Initializing query engine..."):
            st.session_state.query_engine = create_query_engine(
                st.session_state.parquet_path
            )

    # Main layout
    col1, col2 = st.columns([1, 2])

    with col1:
        render_boundary_selector(st.session_state.query_engine)

    with col2:
        render_map_section(st.session_state.query_engine, st.session_state.get('selected_boundary'))

    st.write("---")

    # Mapping form
    render_mapping_form()

    # Mappings table
    render_mappings_table()

    # Download section
    render_download_section()


if __name__ == "__main__":
    main()
