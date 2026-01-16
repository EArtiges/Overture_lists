# Overture Admin Boundary Tools

A multi-page Streamlit application for working with administrative boundaries from [Overture Maps Foundation](https://overturemaps.org/) data. Create boundary lists and map divisions to CRM accounts with custom metadata.

## Overview

This application provides two main tools:

### 📋 List Builder
Create and manage collections of administrative boundaries:
- Browse hierarchical divisions via cascading dropdowns
- Visualize boundaries on interactive maps
- Build named lists with descriptions
- Save, load, and download boundary lists
- Persistent JSON storage

### 🏢 CRM Mapping
Map Overture divisions to your CRM accounts:
- Select divisions using hierarchical navigation
- Assign custom fields: System ID, Account Name, Admin Level
- Build multiple mappings in one session
- Export mappings as JSON or CSV
- Link geographic territories to business data

## Architecture

- **Frontend:** Streamlit multi-page application
- **Data Query:** DuckDB (queries Parquet files directly from S3)
- **Data Source:** Overture Maps Foundation divisions dataset
- **Storage:** JSON flat files with Docker volume persistence
- **Map Rendering:** Folium with geometry simplification for performance
- **Code Structure:** Shared components for DRY architecture

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and run with docker-compose
docker-compose up -d

# Access the app at http://localhost:8501
```

The application will mount `./list_data` and `./pages` as volumes for persistent storage.

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

**Via UI (List Builder only):**
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

3. **Build Mappings:** Create multiple mappings in one session
   - View all mappings in data table
   - Remove individual mappings or clear all

4. **Export:** Download your mappings
   - **JSON format:** Structured data for APIs
   - **CSV format:** Spreadsheet-compatible
   - Includes 4 columns: division_id, system_id, account_name, custom_admin_level

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
Lists are saved as JSON in `./list_data/`:

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
Exports include only essential columns:

```json
[
  {
    "division_id": "08f7...",
    "system_id": "ACC-12345",
    "account_name": "Acme Corp - West",
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
│   └── CRM_Mapping.py          # CRM Mapping page
├── src/
│   ├── query_engine.py         # DuckDB query functions (cached)
│   ├── list_storage.py         # JSON storage management
│   └── shared_components.py    # Shared UI components (DRY)
├── list_data/                   # Persistent storage directory
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
- Common state managed via `init_common_session_state()`
- Proper cleanup on country/selection changes

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
- No bulk import/export beyond JSON/CSV
- Map shows only one boundary at a time
- No map-based selection (dropdown-only navigation)
- Session-based storage (no database)

## Future Enhancements

When migrating from POC to production:
- Replace flat files with SQL database
- Add multi-user support and authentication
- Implement list sharing and permissions
- Add bulk operations and advanced filtering
- Migrate to cloud storage (Azure Blob, S3)
- Enable full list visualization on map
- Add spatial queries (boundaries within radius, overlaps, etc.)
- Support batch CRM mapping uploads

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
# Ensure list_data directory has correct permissions
chmod 777 list_data
```

## License

This project is provided as-is for demonstration purposes.

## Credits

- **Data:** [Overture Maps Foundation](https://overturemaps.org/)
- **Built with:** Streamlit, DuckDB, Folium, Pandas, Python
