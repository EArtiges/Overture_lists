"""
Organizational Hierarchy

Define administrative reporting relationships between Overture divisions.
"""

import streamlit as st
import pandas as pd
import json
import os
import sqlite3
from typing import Optional

from src.query_engine import create_query_engine
from src.crm_mapping_storage import CRMMappingStorage
from src.components import create_map
from streamlit_folium import st_folium

page_title = "Organizational Hierarchy"
page_emoji = "🏗️"

st.set_page_config(
    page_title=page_title,
    page_icon=page_emoji,
    layout="wide"
)


def init_session_state():
    """Initialize session state variables."""
    if 'child_boundary' not in st.session_state:
        st.session_state.child_boundary = None

    if 'parent_boundary' not in st.session_state:
        st.session_state.parent_boundary = None

    if 'parquet_path' not in st.session_state:
        st.session_state.parquet_path = os.getenv(
            'OVERTURE_PARQUET_PATH',
            's3://overturemaps-us-west-2/release/2025-12-17.0/theme=divisions/type=division/*.parquet'
        )

    if 'query_engine' not in st.session_state:
        st.session_state.query_engine = None

    if 'child_selections' not in st.session_state:
        st.session_state.child_selections = []

    if 'parent_selections' not in st.session_state:
        st.session_state.parent_selections = []


def render_division_selector(query_engine, prefix: str, label: str):
    """
    Render hierarchical division selector.

    Args:
        query_engine: OvertureQueryEngine instance
        prefix: Prefix for session state keys ('child' or 'parent')
        label: Label to display for this selector
    """
    st.subheader(f"🔍 {label}")

    # Initialize selection state
    selections_key = f'{prefix}_selections'
    if selections_key not in st.session_state:
        st.session_state[selections_key] = []

    # Step 1: Country selection
    countries = query_engine.get_countries()
    if not countries:
        st.warning("No countries found. Please check your Parquet data path.")
        return None

    selected_country = st.selectbox(
        "Select Country",
        options=[""] + countries,
        key=f"{prefix}_country_select"
    )

    # Reset if country changes
    prev_country_key = f'{prefix}_previous_country'
    if prev_country_key not in st.session_state:
        st.session_state[prev_country_key] = None
    if selected_country != st.session_state[prev_country_key]:
        st.session_state[prev_country_key] = selected_country
        st.session_state[selections_key] = []
        st.session_state[f'{prefix}_boundary'] = None

    if not selected_country:
        st.info("Select a country to begin")
        return None

    # Get the country division_id
    country_division = query_engine.get_country_division(selected_country)
    if not country_division:
        st.error(f"Could not find country division for {selected_country}")
        return None

    # Step 2: Cascading division dropdowns
    current_parent_id = country_division['division_id']
    level = 0

    while True:
        # Query children of current parent
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
            key=f"{prefix}_level_{level}_dropdown"
        )

        # If nothing selected at this level, stop
        if selected_idx == 0:
            # Truncate selections beyond this level
            st.session_state[selections_key] = st.session_state[selections_key][:level]
            break

        # Get selected division
        selected_division = divisions_df.iloc[selected_idx - 1].to_dict()

        # Update selections list
        if level < len(st.session_state[selections_key]):
            # User changed selection at this level - truncate
            st.session_state[selections_key] = st.session_state[selections_key][:level]

        if level == len(st.session_state[selections_key]):
            # New selection at this level
            st.session_state[selections_key].append(selected_division)

        # Move to next level
        current_parent_id = selected_division['division_id']
        level += 1

    # Show breadcrumb
    if st.session_state[selections_key]:
        st.write("---")
        breadcrumb = selected_country + " → " + " → ".join([
            f"{div['name']} ({div['subtype']})"
            for div in st.session_state[selections_key]
        ])
        st.write(f"**Path:** {breadcrumb}")

        # Select button for currently selected division
        st.write("---")
        last_selected = st.session_state[selections_key][-1]
        if st.button(f"✓ Select {last_selected['name']}", use_container_width=True, type="primary", key=f"{prefix}_select_btn"):
            st.session_state[f'{prefix}_boundary'] = last_selected
            st.success(f"Selected: {last_selected['name']}")
            st.rerun()

    return None


def render_relationship_form(storage: CRMMappingStorage, query_engine):
    """Render the form to add organizational relationships."""
    st.subheader("🔗 Define Relationship")

    if st.session_state.child_boundary is None or st.session_state.parent_boundary is None:
        st.info("Select both a child division and a parent division to define a relationship")
        return

    child = st.session_state.child_boundary
    parent = st.session_state.parent_boundary

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Child Division (Subordinate):**")
        st.write(f"{child['name']} ({child['subtype']})")
        st.caption(f"Division ID: {child['division_id']}")

    with col2:
        st.write("**Parent Division (Supervisor):**")
        st.write(f"{parent['name']} ({parent['subtype']})")
        st.caption(f"Division ID: {parent['division_id']}")

    st.write("---")

    # Relationship type dropdown
    relationship_type = st.selectbox(
        "Relationship Type",
        options=[
            "reports_to",
            "coordinates_with",
            "oversees",
            "managed_by",
            "collaborates_with",
            "delegates_to",
            "advises",
            "custom"
        ],
        key="relationship_type",
        help="Select the type of organizational relationship"
    )

    # Custom relationship type if selected
    if relationship_type == "custom":
        relationship_type = st.text_input(
            "Custom Relationship Type",
            placeholder="e.g., audits, monitors",
            key="custom_relationship_type"
        )

    # Optional notes
    notes = st.text_area(
        "Notes (Optional)",
        placeholder="Add any context or details about this relationship",
        key="relationship_notes",
        height=100
    )

    st.write("---")

    if st.button("➕ Add Relationship", type="primary", use_container_width=True):
        if not relationship_type or (relationship_type == "custom" and not relationship_type.strip()):
            st.error("Please specify a relationship type")
        else:
            try:
                storage.add_relationship(
                    child_division_id=child['division_id'],
                    parent_division_id=parent['division_id'],
                    relationship_type=relationship_type.strip(),
                    notes=notes.strip() if notes.strip() else None
                )
                st.success(f"✅ Added relationship: {child['name']} → {parent['name']} ({relationship_type})")
                st.rerun()
            except sqlite3.IntegrityError as e:
                error_msg = str(e)
                if 'UNIQUE constraint' in error_msg:
                    st.error(f"❌ This exact relationship already exists")
                elif 'CHECK constraint' in error_msg:
                    st.error(f"❌ Cannot create a relationship from a division to itself")
                else:
                    st.error(f"❌ Cannot add relationship: {error_msg}")


def render_relationships_table(storage: CRMMappingStorage, query_engine):
    """Render the table of current relationships."""
    st.subheader("📊 Current Relationships")

    relationships = storage.get_all_relationships()

    if not relationships:
        st.info("No relationships defined yet. Select divisions and add relationships above.")
        return

    st.write(f"**Total Relationships:** {len(relationships)}")

    # Fetch division names from Overture for display
    relationships_with_names = []
    for rel in relationships:
        # Get division metadata from Overture (cached)
        child_div = query_engine.get_division_by_id(rel['child_division_id'])
        parent_div = query_engine.get_division_by_id(rel['parent_division_id'])

        # Format names with fallback to ID if lookup fails
        child_name = f"{child_div['name']} ({child_div['subtype']})" if child_div else rel['child_division_id'][:12] + '...'
        parent_name = f"{parent_div['name']} ({parent_div['subtype']})" if parent_div else rel['parent_division_id'][:12] + '...'

        relationships_with_names.append({
            'Child Division': child_name,
            'Parent Division': parent_name,
            'Relationship Type': rel['relationship_type'],
            'Notes': rel.get('notes', '')[:50] if rel.get('notes') else '',
            '_id': rel['id']
        })

    # Create DataFrame for display
    df_display = pd.DataFrame(relationships_with_names)
    display_columns = ['Child Division', 'Parent Division', 'Relationship Type', 'Notes']

    st.dataframe(
        df_display[display_columns],
        hide_index=True,
        use_container_width=True
    )

    # Delete relationship
    st.write("---")
    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button("🗑️ Delete Relationship", use_container_width=True):
            st.session_state.show_delete_rel_dialog = True

    if st.session_state.get('show_delete_rel_dialog', False):
        rel_options = [
            f"{r['Child Division']} → {r['Parent Division']} ({r['Relationship Type']})"
            for r in relationships_with_names
        ]
        selected_to_delete = st.selectbox(
            "Select relationship to delete",
            options=rel_options,
            key="delete_rel_select"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Confirm Delete", type="primary", use_container_width=True):
                idx = rel_options.index(selected_to_delete)
                rel_id = relationships_with_names[idx]['_id']
                storage.delete_relationship(rel_id)
                st.session_state.show_delete_rel_dialog = False
                st.success("Relationship deleted")
                st.rerun()

        with col_b:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_delete_rel_dialog = False
                st.rerun()


def render_download_section(storage: CRMMappingStorage):
    """Render the download functionality."""
    st.write("---")
    st.subheader("💾 Download Relationships")

    relationships = storage.get_all_relationships()

    if not relationships:
        st.info("No relationships to download yet.")
        return

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.write(f"**Ready to download {len(relationships)} relationships**")

    with col2:
        # JSON download
        export_data = storage.export_relationships_to_json()
        json_str = json.dumps(export_data, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name="organizational_relationships.json",
            mime="application/json",
            use_container_width=True,
            help="Export all relationships as JSON"
        )

    with col3:
        # CSV download
        export_df = pd.DataFrame(export_data)
        csv_str = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_str,
            file_name="organizational_relationships.csv",
            mime="text/csv",
            use_container_width=True,
            help="Export relationships as CSV"
        )

    # Clear all button
    st.write("")
    if st.button("🗑️ Clear All Relationships", use_container_width=False):
        if storage.clear_all_relationships():
            st.success("All relationships cleared")
            st.rerun()


def main():
    """Main application entry point."""
    init_session_state()

    # Title
    st.title(page_emoji + " " + page_title)
    st.write(
        "Define organizational reporting relationships between Overture administrative divisions. "
        "This allows you to capture who-reports-to-whom hierarchies that may differ from "
        "spatial containment relationships."
    )

    # Initialize storage
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

        # Display relationship stats
        st.subheader("📊 Relationship Statistics")
        rel_count = mapping_storage.get_relationship_count()
        st.metric("Total Relationships", rel_count)

    # Initialize query engine
    if (st.session_state.query_engine is None or
        st.session_state.query_engine.parquet_path != st.session_state.parquet_path):
        try:
            st.session_state.query_engine = create_query_engine(st.session_state.parquet_path)
        except Exception as e:
            st.error(f"Error initializing query engine: {e}")
            st.stop()

    # Main layout with two selectors
    st.write("---")
    st.header("Select Divisions")

    col1, col2 = st.columns(2)

    with col1:
        render_division_selector(st.session_state.query_engine, "child", "Child Division (Subordinate)")

    with col2:
        render_division_selector(st.session_state.query_engine, "parent", "Parent Division (Supervisor)")

    st.write("---")

    # Relationship form
    render_relationship_form(mapping_storage, st.session_state.query_engine)

    st.write("---")

    # Relationships table
    render_relationships_table(mapping_storage, st.session_state.query_engine)

    # Download section
    render_download_section(mapping_storage)


if __name__ == "__main__":
    main()
