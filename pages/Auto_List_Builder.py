"""
Auto List Builder

Automatically create boundary lists from hierarchical relationships.
"""

import streamlit as st
import pandas as pd
import json
import os

from src.query_engine import create_query_engine
from src.database_storage import DatabaseStorage

page_title = "Auto List Builder"
page_emoji = "🤖"

st.set_page_config(
    page_title=page_title,
    page_icon=page_emoji,
    layout="wide"
)


def init_session_state():
    """Initialize session state variables."""
    if 'selected_parent' not in st.session_state:
        st.session_state.selected_parent = None

    if 'parquet_path' not in st.session_state:
        st.session_state.parquet_path = os.getenv(
            'OVERTURE_PARQUET_PATH',
            's3://overturemaps-us-west-2/release/2025-12-17.0/theme=divisions/type=division/*.parquet'
        )

    if 'query_engine' not in st.session_state:
        st.session_state.query_engine = None

    if 'division_selections' not in st.session_state:
        st.session_state.division_selections = []

    if 'generated_list' not in st.session_state:
        st.session_state.generated_list = []

    if 'list_metadata' not in st.session_state:
        st.session_state.list_metadata = {
            'list_name': '',
            'description': ''
        }


def render_division_selector(query_engine):
    """Render hierarchical division selector for parent selection."""
    st.subheader("🔍 Select Parent Division")

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
        st.session_state.selected_parent = None

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

        # Select button for currently selected division
        st.write("---")
        last_selected = st.session_state.division_selections[-1]
        if st.button(f"✓ Select {last_selected['name']} as Parent", use_container_width=True, type="primary"):
            st.session_state.selected_parent = last_selected
            st.success(f"Selected parent: {last_selected['name']}")
            st.rerun()

    return None


def render_list_generation_section(query_engine, ):
    """Render the list generation controls."""
    st.subheader("🤖 Auto-Generate List")

    if st.session_state.selected_parent is None:
        st.info("Select a parent division above to generate a list of its children")
        return

    parent = st.session_state.selected_parent

    st.write(f"**Parent Division:** {parent['name']} ({parent['subtype']})")
    st.write(f"**Division ID:** `{parent['division_id']}`")

    st.write("---")

    # Hierarchy type selection
    hierarchy_type = st.radio(
        "Create list according to:",
        options=["Spatial Hierarchy", "Admin Hierarchy"],
        help="Spatial: uses Overture's parent_division_id field. Admin: uses your custom organizational relationships (reports_to only)."
    )

    st.write("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Generate List", type="primary", use_container_width=True):
            with st.spinner("Generating list..."):
                if hierarchy_type == "Spatial Hierarchy":
                    # Query Overture for spatial children
                    children_df = query_engine.get_child_divisions(parent['division_id'])

                    if children_df.empty:
                        st.warning(f"No spatial children found for {parent['name']}")
                        return

                    # Convert to list of boundaries
                    boundaries = []
                    for _, row in children_df.iterrows():
                        boundaries.append({
                            'division_id': row['division_id'],
                            'name': row['name'],
                            'subtype': row['subtype'],
                            'country': row['country']
                        })

                    st.session_state.generated_list = boundaries
                    st.success(f"✅ Generated list with {len(boundaries)} divisions from spatial hierarchy")
                    st.rerun()

                else:  # Admin Hierarchy
                    # Query SQLite for admin relationships (reports_to only)
                    with DatabaseStorage() as db:
                        # Get parent's internal DB ID
                        parent_div = db.get_division_by_system_id(parent['division_id'])
                        if not parent_div:
                            st.warning(f"Parent division not found in cache: {parent['name']}")
                            st.info("Add relationships for this division in Organizational Hierarchy first")
                            return

                        # Get all relationships for this division
                        all_relationships = db.get_relationships(division_id=parent_div['id'])

                        # Filter for reports_to relationships where this is the parent
                        reports_to_rels = [
                            r for r in all_relationships
                            if r['relationship_type'] == 'reports_to'
                            and r['parent_division_id'] == parent_div['id']
                        ]

                        if not reports_to_rels:
                            st.warning(f"No admin hierarchy relationships (reports_to) found for {parent['name']}")
                            st.info("Define relationships in the Organizational Hierarchy page first")
                            return

                        # Fetch division details from Overture for each child
                        boundaries = []
                        for rel in reports_to_rels:
                            # Get child division from cache to get its system_id
                            child_cached = db.get_division(rel['child_division_id'])
                            if child_cached:
                                # Query Overture for full details
                                child_div = query_engine.get_division_by_id(child_cached['system_id'])
                                if child_div:
                                    boundaries.append({
                                        'division_id': child_div['division_id'],
                                        'name': child_div['name'],
                                        'subtype': child_div['subtype'],
                                        'country': child_div['country']
                                    })

                        st.session_state.generated_list = boundaries
                    st.success(f"✅ Generated list with {len(boundaries)} divisions from admin hierarchy")
                    st.rerun()

    with col2:
        if st.button("🗑️ Clear Generated List", use_container_width=True):
            st.session_state.generated_list = []
            st.session_state.list_metadata = {'list_name': '', 'description': ''}
            st.success("List cleared")
            st.rerun()


def render_generated_list_section():
    """Display the generated list."""
    st.subheader("📋 Generated List")

    if not st.session_state.generated_list:
        st.info("No list generated yet. Select a parent division and generate a list above.")
        return

    st.write(f"**Total Divisions:** {len(st.session_state.generated_list)}")

    # Create DataFrame for display
    df = pd.DataFrame(st.session_state.generated_list)
    display_columns = ['name', 'subtype', 'country', 'division_id']

    st.dataframe(
        df[display_columns],
        hide_index=True,
        use_container_width=True
    )


def render_save_section():
    """Render save functionality for generated lists."""
    st.write("---")
    st.subheader("💾 Save Generated List")

    if not st.session_state.generated_list:
        st.info("Generate a list first to save it")
        return

    col1, col2 = st.columns([2, 3])

    with col1:
        list_name = st.text_input(
            "List Name",
            value=st.session_state.list_metadata['list_name'],
            placeholder="e.g., California Counties",
            key="save_list_name"
        )
        st.session_state.list_metadata['list_name'] = list_name

    with col2:
        description = st.text_area(
            "Description",
            value=st.session_state.list_metadata['description'],
            placeholder="Brief description of this list",
            height=100,
            key="save_list_description"
        )
        st.session_state.list_metadata['description'] = description

    st.write("---")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("💾 Save List", type="primary", use_container_width=True):
            if not list_name.strip():
                st.error("Please enter a list name")
            else:
                try:
                    with DatabaseStorage() as db:
                        # Cache divisions and collect their IDs
                        division_ids = []
                        for boundary in st.session_state.generated_list:
                            division_id = db.save_division(
                                system_id=boundary['division_id'],
                                name=boundary['name'],
                                subtype=boundary.get('subtype', ''),
                                country=boundary.get('country', ''),
                                geometry=boundary.get('geometry', {})
                            )
                            division_ids.append(division_id)

                        # Create the list
                        list_id = db.create_list(
                            name=list_name,
                            list_type='division',
                            item_ids=division_ids,
                            notes=description
                        )
                        st.success(f"List saved successfully! ID: {list_id}")
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Error saving list: {e}")
                else:
                    st.rerun()

    with col_b:
        # Download button
        export_data = {
            'list_name': list_name if list_name else 'Unnamed List',
            'description': description,
            'boundary_count': len(st.session_state.generated_list),
            'boundaries': st.session_state.generated_list
        }
        json_str = json.dumps(export_data, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"{list_name.replace(' ', '_') if list_name else 'list'}.json",
            mime="application/json",
            use_container_width=True
        )


def render_saved_lists_sidebar():
    """Render saved lists in sidebar."""
    st.sidebar.header("📚 Saved Lists")

    with DatabaseStorage() as db:
        saved_lists = db.get_all_lists(list_type='division')

    if not saved_lists:
        st.sidebar.info("No saved lists yet")
        return

    for list_info in saved_lists:
        # Get boundary count
        with DatabaseStorage() as db:
            boundaries = db.get_list_items(list_info['id'])
        boundary_count = len(boundaries)

        with st.sidebar.expander(f"📄 {list_info['name']}"):
            st.write(f"**Boundaries:** {boundary_count}")
            st.write(f"**Created:** {list_info['created_at'][:10]}")
            if list_info.get('notes'):
                st.write(f"**Description:** {list_info['notes']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load", key=f"load_{list_info['id']}", use_container_width=True):
                    with DatabaseStorage() as db:
                        boundaries = db.get_list_items(list_info['id'])
                        # Convert division objects to boundary format
                        boundary_list = []
                        for div in boundaries:
                            boundary_list.append({
                                'division_id': div['system_id'],
                                'name': div['name'],
                                'subtype': div.get('subtype', ''),
                                'country': div.get('country', ''),
                                'geometry': div.get('geometry', {})
                            })

                        st.session_state.generated_list = boundary_list
                        st.session_state.list_metadata = {
                            'list_name': list_info['name'],
                            'description': list_info.get('notes', '')
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
                boundaries = db.get_list_items(list_info['id'])
                boundary_list = []
                for div in boundaries:
                    boundary_list.append({
                        'division_id': div['system_id'],
                        'name': div['name'],
                        'subtype': div.get('subtype', ''),
                        'country': div.get('country', ''),
                        'geometry': div.get('geometry', {})
                    })

                export_data = {
                    'list_name': list_info['name'],
                    'description': list_info.get('notes', ''),
                    'boundary_count': len(boundary_list),
                    'boundaries': boundary_list
                }
                json_str = json.dumps(export_data, indent=2)
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
        "Automatically generate boundary lists from hierarchical relationships. "
        "Select a parent division and choose whether to use spatial hierarchy (Overture's structure) "
        "or admin hierarchy (your custom organizational relationships)."
    )

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

        # Show saved lists
        render_saved_lists_sidebar()

    # Initialize query engine
    if (st.session_state.query_engine is None or
        st.session_state.query_engine.parquet_path != st.session_state.parquet_path):
        try:
            st.session_state.query_engine = create_query_engine(st.session_state.parquet_path)
        except Exception as e:
            st.error(f"Error initializing query engine: {e}")
            st.stop()

    # Main layout
    st.write("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        render_division_selector(st.session_state.query_engine)

    with col2:
        render_list_generation_section(st.session_state.query_engine)

    st.write("---")

    # Display generated list
    render_generated_list_section()

    # Save section
    render_save_section()


if __name__ == "__main__":
    main()
