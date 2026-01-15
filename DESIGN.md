# Overture Admin Boundary List Builder - Design Doc

## Problem Statement
Build a POC application that allows users to create and manage lists of administrative boundaries from Overture Maps Foundation data. The app enables users to search for boundaries through hierarchical filtering, visualize them on a map, and organize them into named, persistent lists.

## Use Case
Internal tool for a single user to demo to decision-makers. User needs to select admin boundaries (countries, states, counties, etc.) from Overture's dataset, organize them into lists with descriptions, and save these lists for future reference.

## Architecture Decisions

### Technology Stack
- **Language:** Python
- **Frontend:** Streamlit
- **Data Query:** DuckDB (querying Parquet files directly)
- **Data Source:** Overture Maps Foundation admin boundary dataset (Parquet format)
- **Storage:** JSON flat files
- **Deployment:** Docker container with volume mount for file persistence
- **Map Rendering:** Folium

### Storage Strategy
- **POC Phase:** Local filesystem with Docker volume mount (`-v ./list_data:/app/data`)
- **Future:** Azure Blob Storage or similar
- **Rationale:** Start simple with local files, migrate to cloud storage when multi-machine access is needed

## Data Models

### List File Structure (JSON)
```json
{
  "list_id": "md5_hash_of_initial_gers_ids_plus_timestamp",
  "list_name": "West Coast States",
  "description": "Sales territories for Q1 2026",
  "created_at": "2026-01-15T10:30:00Z",
  "boundaries": [
    {
      "gers_id": "overture_gers_id_1",
      "name": "California",
      "admin_level": 4,
      "country": "US"
    },
    {
      "gers_id": "overture_gers_id_2",
      "name": "Oregon",
      "admin_level": 4,
      "country": "US"
    }
  ]
}
```

**Notes:**
- `list_id` is generated as `md5(initial_gers_ids + timestamp)` to allow list renaming without breaking file references
- Boundaries array is denormalized (includes metadata, not just IDs) to avoid querying Parquet on every list load
- Filename: `{list_id}.json`

### Overture Data Schema (relevant fields)
- `id` (GERS ID): Unique identifier for each boundary
- `names.primary`: Display name
- `admin_level`: Hierarchical level (2=country, 4=state, 6=county, etc.)
- `country`: ISO country code
- Parent/child relationships exist in the dataset for hierarchy traversal
- `geometry`: Polygon/MultiPolygon geometries (fetched only when rendering)

## User Workflow

### Main Flow
1. **Filter boundaries using cascading dropdowns:**
   - Select country
   - Select admin level(s) progressively (e.g., state, then county)
   - Each selection narrows the search space for the next dropdown

2. **Select specific boundary:**
   - Final dropdown shows all boundaries matching the filter criteria
   - User selects one boundary from dropdown

3. **View on map:**
   - Selected boundary's geometry is fetched and displayed on map
   - Map shows only the currently-selected boundary (previous selections are cleared)
   - Map appears for the first time on first selection, updates on subsequent selections

4. **Add to list:**
   - User clicks "Add to list" button
   - Boundary metadata (GERS ID, name, admin_level, country) is added to session state

5. **Review list:**
   - Table at bottom of page shows all boundaries added so far
   - Columns: GERS ID, Name, Admin Level, Country
   - User can remove boundaries from the table

6. **Save list:**
   - User enters list name and description (editable throughout session)
   - User clicks "Save" button
   - JSON file is written to disk/storage

### Edit Capabilities
- User can rename list (but list_id remains the same)
- User can edit description at any time
- User can remove boundaries from the list before saving
- One list per session (save and start over for multiple lists)

## Implementation Notes

### Streamlit State Management
```python
# Cache expensive queries
@st.cache_data
def get_countries():
    # Query distinct countries from Parquet

@st.cache_data
def get_admin_levels(country):
    # Query distinct admin levels for given country

@st.cache_data
def get_boundaries(country, admin_level, parent_filters):
    # Query boundaries matching filters
    # Return: [{gers_id, name, admin_level, country}]

@st.cache_data
def get_geometry(gers_id):
    # Query geometry for specific boundary
    # Return: GeoJSON

# Session state structure
if 'current_list' not in st.session_state:
    st.session_state.current_list = {
        'list_name': '',
        'description': '',
        'boundaries': []  # [{gers_id, name, admin_level, country}]
    }
```

### Key Patterns
- **Caching:** All DuckDB queries must be cached with `@st.cache_data` to avoid re-querying Parquet on every Streamlit rerun
- **Lazy geometry loading:** Never load geometry into memory except when explicitly rendering a selected boundary
- **Explicit saves:** File writes happen only when user clicks "Save", not on every add operation
- **Map updates:** Map clears and shows only the latest selected boundary (no accumulation)

### Query Patterns
- Cascading dropdown queries only fetch the next level of hierarchy (e.g., given country, fetch admin levels within that country)
- Only one country is considered at a time (no cross-country queries)
- Final dropdown typically returns <100 results (small enough to display all without pagination)
- Geometry queries fetch only for the single boundary currently being viewed

### Edge Cases to Handle
- User selects boundary, views it, but doesn't add to list (that's fine, map just shows it)
- User adds same boundary multiple times (allow or prevent? TBD)
- User tries to save without entering list name (validation required)
- Empty list (allow saving? probably not)

## Future Migration Path
When moving from POC to production:
- Replace flat files with SQL database:
  - `lists` table: `(list_id, list_name, description, created_at, user_id)`
  - `list_boundaries` table: `(list_id, gers_id)` (join table)
  - Boundary metadata joined from Parquet/separate boundaries table
- Add multi-user support
- Add authentication
- Move to cloud-hosted deployment
- Migrate from volume mount to Blob Storage/cloud storage

## Out of Scope (for POC)
- Multi-user access
- List sharing between users
- Clicking on map to select boundaries (search/dropdown only)
- Visualizing entire list on map at once (only single boundary preview)
- Authentication
- List versioning or edit history
- Bulk import/export
- Advanced filtering beyond cascading hierarchy

## Implementation Status

### Completed
- ✅ Project structure and dependencies
- ✅ DuckDB query engine with caching
- ✅ Streamlit UI with cascading filters
- ✅ Map visualization (Folium)
- ✅ Session state management
- ✅ List management (add, remove, review)
- ✅ JSON storage backend
- ✅ Docker configuration
- ✅ Comprehensive documentation

### Testing Required
- Data access to actual Overture Maps Parquet files
- End-to-end workflow validation
- Edge case handling
- Performance with large datasets
