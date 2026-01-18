# Overture Admin Boundary Tools

A multi-page Streamlit application for working with administrative boundaries from [Overture Maps Foundation](https://overturemaps.org/) data. Create boundary lists, map divisions to CRM accounts, build targeted client lists, define organizational hierarchies, auto-generate lists, and visualize saved data on interactive maps.

## Overview

This application provides six integrated tools:

### 📋 List Builder
Create and manage collections of administrative boundaries:
- Browse hierarchical divisions via cascading dropdowns (countries as Level 1)
- Visualize boundaries on interactive maps
- Build named lists with descriptions
- Save lists to SQLite database
- Duplicate detection via MD5 hash (name + type)
- Persistent storage across sessions

### 🏢 CRM Mapping
Map Overture divisions to your CRM accounts with persistent storage:
- Select divisions using hierarchical navigation
- Assign custom fields: System ID, Account Name, Admin Level
- SQLite persistence with cached division geometry
- View, delete, and manage mappings
- Link geographic territories to business data

### 👥 CRM Client List Builder
Build targeted client lists from pre-mapped territories:
- Filter clients by country and mapped territories
- Visualize client territories on interactive maps
- Create and manage client lists
- Save lists to SQLite database
- Load mock client data from clients.json
- Leverage existing CRM mappings for targeted marketing

### 🔗 Organizational Hierarchy
Define reporting relationships between divisions:
- Select parent and child divisions
- Build "reports_to" and "collaborates_with" relationships
- SQLite persistence for organizational structures
- View and manage all relationships
- Foundation for admin hierarchy auto-list generation

### 🤖 Auto List Builder
Automatically generate lists from hierarchical relationships:
- Generate from spatial hierarchies (child divisions via Overture data)
- Generate from admin hierarchies (organizational relationships)
- Select parent division as starting point
- Automatic collection of all children
- Save generated lists to database

### 🗺️ List Visualizer
Visualize saved lists on interactive maps:
- View all list items simultaneously
- Color-coded multi-layer maps
- Toggle individual item visibility
- Supports both boundary and CRM client lists
- Load any saved list for visual exploration

## Architecture

- **Frontend:** Streamlit multi-page application (6 pages)
- **Data Query:** DuckDB (queries Parquet files directly from S3)
- **Data Source:** Overture Maps Foundation divisions dataset
- **Storage:**
  - **Unified SQLite database** (app_data.db) for all persistence
  - Single DatabaseStorage class handles all data operations
  - Tables: divisions (cache), lists, list_divisions, list_clients, crm_mappings, relationships
  - Foreign key constraints and CASCADE deletes
  - PRAGMA foreign_keys = ON for constraint enforcement
  - Mock client data loaded from clients.json
- **Map Rendering:** Folium with geometry simplification for performance
- **Code Structure:** Shared components and utilities for DRY architecture

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and run with docker-compose
docker-compose up -d

# Access the app at http://localhost:8501
```

The application will mount volumes for persistent storage:
- `./data` - SQLite database (app_data.db) - **ALL persistent data**
- `./crm_data` - Mock CRM client data (clients.json)
- `./pages` - Application pages

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Configuration

### Parquet Data Path

By default, the app connects to Overture Maps S3 data using the **divisions** theme:
```
s3://overturemaps-us-west-2/release/2025-12-17.0/theme=divisions/type=division/*.parquet
```

**Important:** The `admins` theme was deprecated in mid-2024 and replaced with `divisions`. Use the divisions theme for current releases.

#### Path Structure
- **Division records:** `theme=divisions/type=division`
- **Area geometries:** `theme=divisions/type=division_area` (used for map rendering)
- **Legacy releases (pre-July 2024):** `theme=admins/type=*/`

#### Release Versions
Overture releases data monthly. Check [available releases](https://docs.overturemaps.org/release/) and update the date accordingly (format: `YYYY-MM-DD.0`).

You can configure a different path:

**Via Environment Variable:**
```bash
export OVERTURE_PARQUET_PATH="path/to/your/data.parquet"
```

**Via Docker Compose:**
Edit `docker-compose.yml`:
```yaml
environment:
  - OVERTURE_PARQUET_PATH=your/custom/path
```

**Via UI:**
Use the "Parquet Data Path" input in the sidebar (changes persist during session only)

## User Workflows

### List Builder Workflow

1. **Navigate:** Use cascading dropdowns to drill down through the administrative hierarchy
   - Start with country selection
   - Navigate through regions, provinces, districts, etc.
   - Each level shows divisions based on parent-child relationships

2. **Visualize:** Click "Show on Map" to display the selected boundary
   - Optimized rendering with geometry simplification
   - Interactive Folium map with zoom and pan

3. **Build List:** Add boundaries to your working list
   - Enter list name and description
   - Add multiple boundaries from different hierarchies
   - Review in editable data table

4. **Save:** Persist your work
   - Save lists to SQLite database
   - Duplicate detection via MD5 hash (name + type)
   - Lists persist across sessions
   - View saved lists in sidebar

### CRM Mapping Workflow

1. **Select Division:** Navigate through administrative hierarchy
   - Same cascading dropdown interface as List Builder
   - Visualize selected division on map

2. **Add Custom Fields:** Map division to your CRM account
   - **System ID:** Your internal CRM identifier
   - **Account Name:** Account name from your system
   - **Custom Admin Level:** Your own administrative nomenclature

3. **Build Mappings:** Create multiple mappings
   - View all mappings in data table
   - SQLite persistence with cached geometry
   - Remove individual mappings as needed
   - All data persists across sessions

### CRM Client List Builder Workflow

1. **Load Client Data:** Place your CRM client data in `crm_data/clients.json`
   - Required fields: system_id, account_name, country, custom_admin_level
   - Automatically loaded on page load

2. **Select Territory:** Filter clients by country and mapped division
   - Country dropdown shows available client countries
   - Client dropdown filters by selected country
   - Only shows clients with CRM mappings
   - Visualize selected client territory on map

3. **Build Client List:** Create targeted marketing lists
   - Add clients to your working list
   - Enter list name and description
   - View all clients in data table
   - Remove individual clients or clear all

4. **Save:** Persist your client lists
   - Save lists to SQLite database (type='client')
   - Lists persist across sessions
   - View saved lists in sidebar
   - Delete saved lists as needed

## Features

### Hierarchical Division Selection
- **Countries as Level 1 divisions:** Countries are now proper divisions with division_ids
- **Parent-child navigation:** Cascading dropdowns based on `parent_division_id` relationships
- **Dynamic levels:** Adapts to available subdivision levels per country
- **Session persistence:** Maintains selections across page interactions
- **Simplified queries:** `SELECT DISTINCT ... WHERE subtype='country'` for country list

### Map Visualization
- **Geometry simplification:** ST_Simplify reduces polygon complexity for faster rendering
- **Dual dataset queries:**
  - Division metadata from `type=division`
  - Geometries from `type=division_area`
- **Interactive controls:** Zoom, pan, and tooltips via Folium

### Data Management

All application data is stored in a single SQLite database at `./data/app_data.db`.

**Database Schema:**

**divisions table** (division metadata cache):
- `id` - Auto-increment primary key
- `system_id` - Overture division ID (UNIQUE)
- `name` - Division name
- `subtype` - Division type (country, region, etc.)
- `country` - Country code
- `geometry_json` - Cached GeoJSON geometry
- `cached_at` - Timestamp

**lists table** (boundary and client lists):
- `id` - Auto-increment primary key
- `name` - List name
- `type` - 'division' or 'client'
- `notes` - Optional description
- `hash` - MD5 hash of name+type for duplicate detection (UNIQUE)
- `created_at`, `updated_at` - Timestamps

**list_divisions table** (junction table for division lists):
- `list_id` - Foreign key to lists (CASCADE delete)
- `division_id` - Foreign key to divisions (CASCADE delete)

**list_clients table** (junction table for client lists):
- `list_id` - Foreign key to lists (CASCADE delete)
- `system_id` - CRM client system ID

**crm_mappings table** (division to CRM account mappings):
- `id` - Auto-increment primary key
- `system_id` - CRM system ID (UNIQUE)
- `division_id` - Internal division ID (UNIQUE, FK to divisions)
- `account_name` - CRM account name
- `custom_admin_level` - User-defined admin level
- `division_name`, `overture_subtype`, `country` - Division metadata
- `geometry_json` - Cached geometry
- `created_at`, `updated_at` - Timestamps

**relationships table** (organizational hierarchy):
- `id` - Auto-increment primary key
- `parent_division_id` - FK to divisions (CASCADE delete)
- `child_division_id` - FK to divisions (CASCADE delete)
- `relationship_type` - 'reports_to' or 'collaborates_with'
- `created_at` - Timestamp
- UNIQUE constraint on (parent_division_id, child_division_id, relationship_type)

**Mock Client Data Format (`crm_data/clients.json`):**
```json
[
  {
    "system_id": "ACC-12345",
    "account_name": "Acme Corp - West",
    "country": "US",
    "custom_admin_level": "Sales Territory"
  }
]
```

## Project Structure

```
.
├── app.py                       # Home page / landing page
├── pages/
│   ├── List_Builder.py         # Manual list builder
│   ├── CRM_Mapping.py          # Division to CRM mapping
│   ├── CRM_Client_List.py      # Client list builder
│   ├── Organizational_Hierarchy.py  # Define reporting relationships
│   ├── Auto_List_Builder.py    # Auto-generate lists from hierarchies
│   └── List_Visualizer.py      # Visualize saved lists on maps
├── src/
│   ├── query_engine.py         # DuckDB query functions (cached)
│   ├── database_storage.py     # Unified SQLite storage class
│   ├── crm_client_storage.py   # Client data loader with caching
│   ├── components.py           # Shared UI components (DRY)
│   └── sql/
│       └── schema.sql          # Database schema definition
├── crm_data/
│   └── clients.json            # Mock CRM client data
├── data/
│   └── app_data.db             # SQLite database (all persistent data)
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container configuration
├── docker-compose.yml           # Docker orchestration
└── README.md                    # This file
```

## Development

### Key Design Patterns

**Multi-page Architecture:** Streamlit automatically detects pages in the `pages/` directory and creates sidebar navigation.

**Shared Components:** Common UI elements (map rendering, boundary selector, session state) extracted to `src/shared_components.py` to eliminate duplication and ensure consistency.

**Caching:** All DuckDB queries use `@st.cache_data` to avoid re-querying Parquet files on every Streamlit rerun.

**Lazy Loading:** Geometries are only loaded when viewing on the map, never bulk-loaded into memory.

**Session State Management:**
- Each page maintains its own state keys (e.g., `crm_selected_boundary` vs `selected_boundary`)
- Common state managed via shared initialization functions
- Proper cleanup on country/selection changes

**Data Persistence:**
- Unified SQLite database for all application data (app_data.db)
- Single DatabaseStorage class with context manager pattern
- Foreign key constraints and CASCADE deletes
- Hash-based duplicate detection for lists (MD5 of name + type)
- Transaction management via context manager (__enter__/__exit__)
- Cached division geometry to avoid re-querying Overture
- Easy migration path to PostgreSQL or cloud databases

**Performance Optimization:**
- Geometry simplification: `ST_Simplify(geometry, 0.001)` reduces polygon complexity by ~100 meters tolerance
- Separate queries for metadata vs geometries
- Cached query results

### Data Schema

The app uses Overture Maps divisions dataset with schema:

**Division records (`type=division`):**
- `id`: Division ID (unique identifier)
- `names.primary`: Display name
- `subtype`: Division type (country, region, province, etc.)
- `country`: ISO country code
- `parent_division_id`: Parent division for hierarchy

**Division areas (`type=division_area`):**
- `division_id`: References division record
- `geometry`: Polygon/MultiPolygon geometries

### Adding Custom Fields

The page configuration pattern uses variables for titles and emojis:

```python
page_title = "Your Page Title"
page_emoji = "🎯"
st.set_page_config(
    page_title=page_title,
    page_icon=page_emoji,
    layout="wide"
)
```

## Limitations

This is a proof-of-concept with intentional scope limitations:
- Single-user tool (no authentication)
- No multi-user access or list sharing
- List Visualizer can show multiple items, but List Builder shows one at a time
- No map-based selection (dropdown-only navigation)
- Client data must be manually placed in `crm_data/clients.json` (mock data)
- No live CRM integration
- No export functionality yet (all data in SQLite)

## Recent Enhancements (Implemented)

✅ **Unified SQLite Database** - Migrated all persistence to single SQLite database with unified DatabaseStorage class

✅ **Six Tools** - Added Organizational Hierarchy, Auto List Builder, and List Visualizer pages

✅ **Countries as Divisions** - Improved cascading dropdown to treat countries as Level 1 divisions with proper division_ids

✅ **Hash-based Duplicate Detection** - Lists use MD5 hash of name+type to prevent duplicates

✅ **Relationship Management** - Define organizational hierarchies with reports_to and collaborates_with relationships

✅ **Auto-List Generation** - Generate lists from spatial hierarchies (Overture parent-child) or admin hierarchies (user-defined relationships)

✅ **Multi-Item Visualization** - List Visualizer shows all items on map with color-coding and toggle visibility

✅ **Context Manager Pattern** - Proper transaction management with commit/rollback and st.rerun() safety

## Future Enhancements

When migrating from POC to production:
- Add multi-user support and authentication
- Implement list sharing and permissions
- Add bulk operations and advanced filtering
- Migrate to cloud storage (Azure Blob, S3) or managed database (PostgreSQL, Azure SQL)
- Enable full list visualization on map (multiple boundaries at once)
- Add spatial queries (boundaries within radius, overlaps, etc.)
- Support live CRM integration via API
- Add batch import from CSV for client data and mappings

## Troubleshooting

### "No files found that match the pattern" or "No countries found" error

**Common cause:** Using the deprecated `admins` theme or incorrect path pattern.

**Solution:**
1. Update your path to use the `divisions` theme:
   ```
   s3://overturemaps-us-west-2/release/2025-12-17.0/theme=divisions/type=division/*.parquet
   ```

2. Verify the release date exists on [Overture releases page](https://docs.overturemaps.org/release/)

3. Check network access to S3 if using remote data

### Map rendering is slow

**Solution:** The app already uses geometry simplification. If still slow:
- Adjust simplification tolerance in `src/shared_components.py` (increase from 0.001)
- Check network bandwidth for S3 downloads
- Consider caching geometries locally

### Sidebar navigation not appearing

**Common cause:** Docker volume not mounted for `pages/` directory

**Solution:**
1. Verify `docker-compose.yml` includes:
   ```yaml
   volumes:
     - ./pages:/app/pages
   ```

2. Restart containers: `docker-compose down && docker-compose up -d`

### Pages show `st.set_page_config` error

**Cause:** Only the main `app.py` should call `st.set_page_config()` in the root level. Pages can call it but must do so before any other Streamlit commands.

**Solution:** Ensure page files have `st.set_page_config()` as the first Streamlit call, right after imports.

### Docker volume permissions
```bash
# Ensure data directories have correct permissions
chmod 777 crm_data data
```

### Database file permissions

**Symptom:** "Unable to open database file" or permission errors

**Solution:**
```bash
chmod 666 data/app_data.db
```

### Transaction rollback issues

**Symptom:** Data not persisting even though no error shown

**Cause:** st.rerun() called inside DatabaseStorage context manager causes exception, triggering rollback

**Solution:** Ensure st.rerun() is called AFTER the context manager exits
```python
# CORRECT:
with DatabaseStorage() as db:
    db.save_mapping(...)
# Context exits here, commit happens
st.rerun()  # Safe

# WRONG:
with DatabaseStorage() as db:
    db.save_mapping(...)
    st.rerun()  # Causes rollback!
```

### Client List Builder shows no clients

**Symptom:** "No clients found" or empty dropdown in Client List Builder

**Cause:** Either no client data in `crm_data/clients.json` or no CRM mappings exist for those clients.

**Solution:**
1. Verify `crm_data/clients.json` exists and contains valid client data
2. Check that clients have the required fields: system_id, account_name, country, custom_admin_level
3. Ensure you've created CRM mappings in the CRM Mapping page
4. Client List Builder only shows clients that have been mapped to divisions

## License

This project is provided as-is for demonstration purposes.

## Credits

- **Data:** [Overture Maps Foundation](https://overturemaps.org/)
- **Built with:** Streamlit, DuckDB, Folium, Pandas, Python
