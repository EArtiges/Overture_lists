"""
CRM Client List Builder

Create and export lists of CRM clients based on pre-mapped divisions.
"""

import streamlit as st
import pandas as pd
import json

from src.database_storage import DatabaseStorage
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


def render_save_section():
    """Render save functionality for CRM client lists."""
    st.write("---")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.write("### 💾 Save Client List")

    with col2:
        if st.button("🗑️ Clear List", use_container_width=True):
            st.session_state.crm_client_list = {
                'list_name': '',
                'description': '',
                'clients': []
            }
            st.session_state.selected_client = None
            st.success("List cleared")
            st.rerun()

    with col3:
        if st.button("💾 Save List", type="primary", use_container_width=True):
            # Validation
            if not st.session_state.crm_client_list['list_name'].strip():
                st.error("Please enter a list name")
            elif not st.session_state.crm_client_list['clients']:
                st.error("Cannot save an empty list")
            else:
                try:
                    with DatabaseStorage() as db:
                        # Extract system_ids from clients
                        system_ids = [c['system_id'] for c in st.session_state.crm_client_list['clients']]

                        # Create the list
                        list_id = db.create_list(
                            name=st.session_state.crm_client_list['list_name'],
                            list_type='client',
                            item_ids=system_ids,
                            notes=st.session_state.crm_client_list['description']
                        )
                        st.success(f"Client list saved successfully! ID: {list_id}")
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Error saving list: {e}")
                else:
                    st.rerun()


def render_saved_lists_sidebar():
    """Render saved CRM client lists in sidebar."""
    st.sidebar.header("📚 Saved Client Lists")

    with DatabaseStorage() as db:
        saved_lists = db.get_all_lists(list_type='client')

    if not saved_lists:
        st.sidebar.info("No saved client lists yet")
        return

    for list_info in saved_lists:
        # Get client count
        with DatabaseStorage() as db:
            system_ids = db.get_list_items(list_info['id'])
        client_count = len(system_ids)

        with st.sidebar.expander(f"📄 {list_info['name']}"):
            st.write(f"**Clients:** {client_count}")
            st.write(f"**Created:** {list_info['created_at'][:10]}")
            if list_info.get('notes'):
                st.write(f"**Description:** {list_info['notes']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load", key=f"load_{list_info['id']}", use_container_width=True):
                    with DatabaseStorage() as db:
                        system_ids = db.get_list_items(list_info['id'])
                        # Load full client data from crm_mappings
                        clients = []
                        for sys_id in system_ids:
                            mapping = db.get_mapping_by_system_id(sys_id)
                            if mapping:
                                clients.append(mapping)

                        st.session_state.crm_client_list = {
                            'list_name': list_info['name'],
                            'description': list_info.get('notes', ''),
                            'clients': clients
                        }
                        st.success(f"Loaded: {list_info['name']}")
                        st.rerun()

            with col2:
                if st.button("Delete", key=f"delete_{list_info['id']}", use_container_width=True):
                    with DatabaseStorage() as db:
                        db.delete_list(list_info['id'])
                    st.success("Deleted")
                    st.rerun()

            # Download button
            with DatabaseStorage() as db:
                system_ids = db.get_list_items(list_info['id'])
                # Load full client data for export
                clients = []
                for sys_id in system_ids:
                    mapping = db.get_mapping_by_system_id(sys_id)
                    if mapping:
                        clients.append({
                            'system_id': mapping['system_id'],
                            'account_name': mapping['account_name'],
                            'division_id': mapping['division_id'],
                            'division_name': mapping.get('division_name', ''),
                            'country': mapping.get('country', ''),
                            'custom_admin_level': mapping.get('custom_admin_level', '')
                        })

                export_data = {
                    'list_name': list_info['name'],
                    'description': list_info.get('notes', ''),
                    'client_count': len(clients),
                    'clients': clients
                }
                json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📥 Download",
                    data=json_str,
                    file_name=f"{list_info['name'].replace(' ', '_')}.json",
                    mime="application/json",
                    key=f"download_{list_info['id']}",
                    use_container_width=True
                )


def main():
    """Main application entry point."""
    init_session_state()

    # Title
    st.title(page_emoji + " " + page_title)
    st.write(
        "Create and save lists of CRM clients based on pre-mapped administrative divisions. "
        "Select clients by country, view their territories on the map, and build targeted lists "
        "for campaigns, reporting, or analysis."
    )

    # Sidebar configuration and saved lists
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.info("CRM clients are loaded from SQLite database (CRM Mappings)")

        st.write("---")

        # Show saved lists
        render_saved_lists_sidebar()

    st.write("---")

    # Load CRM mappings (clients) from database
    with DatabaseStorage() as db:
        clients_data = db.get_all_mappings()

    if not clients_data:
        st.error(
            "No CRM mappings found in database. "
            "Please create CRM mappings first in the CRM Mapping page."
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

    # Save section
    render_save_section()

    # Footer
    st.write("---")
    st.caption("Powered by Overture Maps Foundation • Built with Streamlit & DuckDB")


if __name__ == "__main__":
    main()
