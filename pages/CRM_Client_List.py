"""
CRM Client List Builder

Create and export lists of CRM clients based on pre-mapped divisions.
"""

import streamlit as st
import pandas as pd
import json
from typing import Optional, Dict

from src.crm_client_storage import CRMClientStorage
from src.components import render_crm_client_selector, create_map
from streamlit_folium import st_folium

page_title = "CRM Client List Builder"
page_emoji = "📋"

st.set_page_config(
    page_title=page_title,
    page_icon=page_emoji,
    layout="wide"
)


def init_session_state():
    """Initialize session state variables for CRM Client List Builder."""
    if 'crm_client_list' not in st.session_state:
        st.session_state.crm_client_list = {
            'list_name': '',
            'description': '',
            'clients': []
        }

    if 'selected_client' not in st.session_state:
        st.session_state.selected_client = None

    if 'crm_clients_data' not in st.session_state:
        st.session_state.crm_clients_data = []


def render_client_map_section():
    """Render the map visualization section for selected client."""
    st.subheader("🗺️ Client Territory Map")

    if st.session_state.selected_client is None:
        st.info("Select a client from the filters above to view their territory on the map")
        m = create_map()
    else:
        client = st.session_state.selected_client

        # Check if geometry exists
        if 'geometry' not in client or client['geometry'] is None:
            st.warning(f"No geometry available for {client['account_name']}")
            st.info(f"Selected: **{client['account_name']}** ({client['division_name']})")
            m = create_map()
        else:
            st.success(f"Displaying: **{client['account_name']}** ({client['division_name']})")
            # Prepare geometry data for map
            geometry_data = {
                'geometry': client['geometry'],
                'name': client['account_name']
            }
            m = create_map(geometry_data)

    # Render map
    st_folium(m, width=1200, height=500, key="client_map")


def render_client_list_management():
    """Render the client list management section."""
    st.subheader("📋 Client List Management")

    # List name and description
    col1, col2 = st.columns([2, 3])

    with col1:
        list_name = st.text_input(
            "List Name",
            value=st.session_state.crm_client_list['list_name'],
            placeholder="e.g., Q1 2026 Target Accounts",
            key="list_name_input"
        )
        st.session_state.crm_client_list['list_name'] = list_name

    with col2:
        description = st.text_area(
            "Description",
            value=st.session_state.crm_client_list['description'],
            placeholder="Brief description of this client list",
            height=100,
            key="list_description_input"
        )
        st.session_state.crm_client_list['description'] = description

    st.write("---")

    # Add to list button
    if st.session_state.selected_client is not None:
        selected = st.session_state.selected_client

        # Check if already in list
        already_in_list = any(
            c['system_id'] == selected['system_id']
            for c in st.session_state.crm_client_list['clients']
        )

        if already_in_list:
            st.info(f"✓ {selected['account_name']} is already in the list")
        else:
            if st.button(
                f"➕ Add {selected['account_name']} to List",
                type="primary",
                use_container_width=True
            ):
                st.session_state.crm_client_list['clients'].append(selected)
                st.success(f"Added {selected['account_name']} to list")
                st.rerun()

    # Display current list
    st.write("---")
    st.write(f"**Clients in List:** {len(st.session_state.crm_client_list['clients'])}")

    if st.session_state.crm_client_list['clients']:
        # Create DataFrame for display
        clients_df = pd.DataFrame(st.session_state.crm_client_list['clients'])

        # Select columns to display
        display_columns = [
            'system_id',
            'account_name',
            'division_name',
            'custom_admin_level',
            'country'
        ]

        # Only show columns that exist
        available_columns = [col for col in display_columns if col in clients_df.columns]
        df_display = clients_df[available_columns]

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Remove client button
        st.write("")
        remove_col1, remove_col2 = st.columns([3, 1])

        with remove_col2:
            if st.button("🗑️ Remove Selected", use_container_width=True):
                # For simplicity, just show a selectbox to choose which to remove
                st.session_state.show_remove_dialog = True

        if st.session_state.get('show_remove_dialog', False):
            client_to_remove = st.selectbox(
                "Select client to remove",
                options=[c['account_name'] for c in st.session_state.crm_client_list['clients']],
                key="remove_client_select"
            )

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Confirm Remove", type="primary", use_container_width=True):
                    # Remove the client
                    st.session_state.crm_client_list['clients'] = [
                        c for c in st.session_state.crm_client_list['clients']
                        if c['account_name'] != client_to_remove
                    ]
                    st.session_state.show_remove_dialog = False
                    st.success(f"Removed {client_to_remove}")
                    st.rerun()

            with col_b:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.show_remove_dialog = False
                    st.rerun()
    else:
        st.info("No clients in list yet. Select and add clients from above.")


def render_export_section():
    """Render export/download functionality."""
    st.write("---")
    st.subheader("💾 Export Client List")

    clients = st.session_state.crm_client_list['clients']
    list_name = st.session_state.crm_client_list['list_name']

    # Validation
    if not clients:
        st.info("Add clients to the list before exporting.")
        return

    if not list_name.strip():
        st.warning("Please provide a list name before exporting.")
        return

    # Prepare export data (CRM data only, no geometry in export)
    export_data = {
        'list_name': st.session_state.crm_client_list['list_name'],
        'description': st.session_state.crm_client_list['description'],
        'client_count': len(clients),
        'clients': [
            {
                'system_id': c['system_id'],
                'account_name': c['account_name'],
                'division_id': c['division_id'],
                'division_name': c['division_name'],
                'country': c['country'],
                'custom_admin_level': c['custom_admin_level']
            }
            for c in clients
        ]
    }

    # Export section
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.write(f"**Ready to export {len(clients)} clients**")

    with col2:
        # JSON download
        json_str = json.dumps(export_data, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"{list_name.replace(' ', '_').lower()}_clients.json",
            mime="application/json",
            use_container_width=True
        )

    with col3:
        # Clear list button
        if st.button("🗑️ Clear List", use_container_width=True):
            st.session_state.crm_client_list = {
                'list_name': '',
                'description': '',
                'clients': []
            }
            st.session_state.selected_client = None
            st.success("List cleared")
            st.rerun()


def main():
    """Main application entry point."""
    init_session_state()

    # Title
    st.title(page_emoji + " " + page_title)
    st.write(
        "Create and export lists of CRM clients based on pre-mapped administrative divisions. "
        "Select clients by country, view their territories on the map, and build targeted lists "
        "for campaigns, reporting, or analysis."
    )

    st.write("---")

    # Load CRM client data
    storage = CRMClientStorage()
    clients_data = storage.load_clients()

    if not clients_data:
        st.error(
            "No CRM client data found. Please ensure `crm_data/clients.json` exists. "
            "You can create this file by exporting mappings from the CRM Mapping page."
        )
        st.stop()

    st.session_state.crm_clients_data = clients_data

    # Main layout
    col1, col2 = st.columns([1, 2])

    with col1:
        render_crm_client_selector(clients_data)

    with col2:
        render_client_map_section()

    st.write("---")

    # Client list management
    render_client_list_management()

    # Export section
    render_export_section()

    # Footer
    st.write("---")
    st.caption("Powered by Overture Maps Foundation • Built with Streamlit & DuckDB")


if __name__ == "__main__":
    main()
