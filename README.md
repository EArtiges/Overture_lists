# Overture Admin Boundary Tools

A multi-page Streamlit application for working with administrative boundaries from [Overture Maps Foundation](https://overturemaps.org/) data. Create boundary lists, map divisions to CRM accounts, and build targeted client lists from mapped territories.

## Overview

This application provides three integrated tools:

### 📋 List Builder
Create and manage collections of administrative boundaries:
- Browse hierarchical divisions via cascading dropdowns
- Visualize boundaries on interactive maps
- Build named lists with descriptions
- Save, load, and download boundary lists
- Persistent JSON storage

### 🏢 CRM Mapping
Map Overture divisions to your CRM accounts with persistent storage:
- Select divisions using hierarchical navigation
- Assign custom fields: System ID, Account Name, Admin Level
- Build multiple mappings with 1:1 constraint enforcement
- SQLite persistence across sessions
- Export mappings as JSON (with geometry) or CSV
- Link geographic territories to business data

### 👥 CRM Client List Builder
Build targeted client lists from pre-mapped territories:
- Filter clients by country and mapped territories
- Visualize client territories on interactive maps
- Create and manage client lists
- Save, load, and download client lists
- Leverage existing CRM mappings for targeted marketing

## Architecture

- **Frontend:** Streamlit multi-page application (3 pages)
- **Data Query:** DuckDB (queries Parquet files directly from S3)
- **Data Source:** Overture Maps Foundation divisions dataset
- **Storage:**
  - SQLite for CRM mappings (persistent, 1:1 constraint enforcement)
  - JSON flat files for boundary lists and client lists
  - Docker volume persistence for all data
- **Map Rendering:** Folium with geometry simplification for performance
- **Code Structure:** Shared components and utilities for DRY architecture

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and run with docker-compose
docker-compose up -d

# Access the app at http://localhost:8501
```

The application will mount multiple volumes for persistent storage:
- `./list_data` - Boundary lists (JSON)
- `./crm_client_lists` - Client lists (JSON)
- `./crm_data` - CRM client data (clients.json)
- `./data` - SQLite database for CRM mappings
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

4. **Save & Download:** Persist your work
   - Save lists to JSON storage
   - Download saved lists as JSON files
   - Load previously saved lists from sidebar

### CRM Mapping Workflow

1. **Select Division:** Navigate through administrative hierarchy
   - Same cascading dropdown interface as List Builder
   - Visualize selected division on map

2. **Add Custom Fields:** Map division to your CRM account
   - **System ID:** Your internal CRM identifier
   - **Account Name:** Account name from your system
   - **Custom Admin Level:** Your own administrative nomenclature

3. **Build Mappings:** Create multiple mappings with constraint enforcement
   - View all mappings in data table
   - 1:1 constraint: each CRM ID maps to one division, each division to one CRM ID
   - Clear error messages on constraint violations
   - Remove individual mappings or clear all
   - SQLite persistence across sessions

4. **Export:** Download your mappings
   - **JSON format:** Structured data with full geometry for APIs
   - **CSV format:** Spreadsheet-compatible (no geometry)
   - Includes: division_id, system_id, account_name, custom_admin_level, geometry (JSON only)

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

4. **Save & Export:** Persist your client lists
   - Save lists to `crm_client_lists/` directory
   - Load previously saved lists from sidebar
   - Delete saved lists
   - Download as JSON for CRM integration
   - Includes: list metadata, client details, division IDs

## Features

### Hierarchical Division Selection
- **Parent-child navigation:** Cascading dropdowns based on `parent_division_id` relationships
- **Country-based filtering:** Always starts with country selection
- **Dynamic levels:** Adapts to available subdivision levels per country
- **Session persistence:** Maintains selections across page interactions

### Map Visualization
- **Geometry simplification:** ST_Simplify reduces polygon complexity for faster rendering
- **Dual dataset queries:**
  - Division metadata from `type=division`
  - Geometries from `type=division_area`
- **Interactive controls:** Zoom, pan, and tooltips via Folium

### Data Management

#### List Builder
Boundary lists are saved as JSON in `./list_data/`:

```json
{
  "list_id": "abc123...",
  "list_name": "West Coast States",
  "description": "Sales territories for Q1 2026",
  "created_at": "2026-01-15T10:30:00Z",
  "boundaries": [
    {
      "division_id": "08f7...",
      "name": "California",
      "subtype": "region",
      "country": "US"
    }
  ]
}
```

#### CRM Mapping
Mappings are stored in SQLite database at `./data/crm_mappings.db`:

**Schema:**
- Table: `crm_mappings`
- Columns: `id`, `division_id` (UNIQUE), `system_id` (UNIQUE), `account_name`, `custom_admin_level`, `created_at`
- Constraints: UNIQUE on both `division_id` and `system_id` for bidirectional 1:1 enforcement

**JSON Export (with geometry):**
```json
[
  {
    "division_id": "08f7...",
    "system_id": "ACC-12345",
    "account_name": "Acme Corp - West",
    "custom_admin_level": "Sales Territory",
    "geometry": {...}
  }
]
```

**CSV Export (no geometry):**
```csv
division_id,system_id,account_name,custom_admin_level
08f7...,ACC-12345,Acme Corp - West,Sales Territory
```

#### CRM Client List Builder
Client lists are saved as JSON in `./crm_client_lists/`:

```json
{
  "list_id": "xyz789...",
  "list_name": "Q1 2026 Campaign Targets",
  "description": "High-value clients in expansion territories",
  "created_at": "2026-01-15T14:30:00Z",
  "clients": [
    {
      "system_id": "ACC-12345",
      "account_name": "Acme Corp - West",
      "country": "US",
      "custom_admin_level": "Sales Territory",
      "division_id": "08f7..."
    }
  ]
}
```

**Client Data Format (`crm_data/clients.json`):**
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
│   ├── List_Builder.py         # List Builder page
│   ├── CRM_Mapping.py          # CRM Mapping page
│   └── CRM_Client_List.py      # CRM Client List Builder page
├── src/
│   ├── query_engine.py         # DuckDB query functions (cached)
│   ├── list_storage.py         # JSON storage for boundary lists
│   ├── crm_mapping_storage.py  # SQLite storage for CRM mappings
│   ├── crm_client_storage.py   # Client data loader with caching
│   └── components.py           # Shared UI components (DRY)
├── list_data/                   # Boundary lists (JSON)
├── crm_client_lists/            # Client lists (JSON)
├── crm_data/
│   └── clients.json            # CRM client data
├── data/
│   └── crm_mappings.db         # SQLite database for mappings
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
- SQLite for CRM mappings with UNIQUE constraints for 1:1 relationships
- JSON files for boundary lists and client lists
- Separate storage classes: `ListStorage`, `CRMMappingStorage`, `CRMClientStorage`
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
- Map shows only one boundary at a time
- No map-based selection (dropdown-only navigation)
- Client data must be manually placed in `crm_data/clients.json`
- No live CRM integration (import/export via JSON/CSV only)

## Recent Enhancements (Implemented)

✅ **SQLite Persistence for CRM Mappings** - Replaced session-based storage with SQLite database, including 1:1 constraint enforcement

✅ **CRM Client List Builder** - New page for building targeted client lists from mapped territories

✅ **Save/Load Functionality** - Full save/load workflow for both boundary lists and client lists

✅ **Enhanced Exports** - JSON exports now include full geometry data for GIS integration

✅ **Data Persistence** - Docker volumes for all data directories (list_data, crm_data, crm_client_lists, data)

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
chmod 777 list_data crm_client_lists crm_data data
```

### CRM Mapping constraint violations

**Symptom:** Error message when adding mapping: "Division already mapped to a different CRM account" or "CRM ID already mapped to a different division"

**Cause:** The 1:1 constraint enforcement prevents duplicate mappings.

**Solution:**
1. Check existing mappings in the data table
2. Delete the conflicting mapping if you want to remap
3. Use a different System ID or select a different division
4. The constraint ensures data integrity - each CRM account maps to exactly one territory

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
