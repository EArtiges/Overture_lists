# Overture Admin Boundary List Builder

A Streamlit-based POC application for creating and managing lists of administrative boundaries from [Overture Maps Foundation](https://overturemaps.org/) data.

## Overview

This tool allows users to:
- Search and filter administrative boundaries (countries, states, counties, etc.) from Overture Maps
- Visualize boundaries on an interactive map
- Create named lists of boundaries with descriptions
- Save and manage multiple boundary lists
- Export lists as JSON for future use

## Architecture

- **Frontend:** Streamlit
- **Data Query:** DuckDB (queries Parquet files directly)
- **Data Source:** Overture Maps Foundation admin boundary dataset
- **Storage:** JSON flat files with Docker volume persistence
- **Map Rendering:** Folium

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and run with docker-compose
docker-compose up -d

# Access the app at http://localhost:8501
```

The application will mount `./list_data` as a volume for persistent storage of your lists.

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

By default, the app connects to Overture Maps S3 data:
```
s3://overturemaps-us-west-2/release/2024-11-13.0/theme=admins/type=*/*.parquet
```

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

## User Workflow

### 1. Filter and Select Boundaries

Use the cascading dropdowns to filter boundaries:
1. **Country:** Select a country code (e.g., US, GB, CA)
2. **Admin Level:** Select administrative level (2=country, 4=state, 6=county, etc.)
3. **Boundary:** Select the specific boundary from filtered results

### 2. View on Map

Once you select a boundary, it will be displayed on the interactive map below the filters.

### 3. Add to List

Click the "Add to List" button to add the selected boundary to your current working list.

### 4. Manage Your List

- **List Name:** Give your list a descriptive name
- **Description:** Add details about the purpose of this list
- **Review Table:** View all boundaries in your current list
- **Remove Items:** Delete rows from the table to remove boundaries

### 5. Save Your List

Click "Save List" to persist your list as a JSON file. The list will appear in the sidebar for future access.

## Features

### Saved Lists Management (Sidebar)

- **View:** All saved lists appear in the sidebar with metadata
- **Load:** Click "Load" to restore a saved list into your working session
- **Delete:** Remove saved lists you no longer need

### List File Format

Lists are saved as JSON in `./list_data/`:

```json
{
  "list_id": "abc123...",
  "list_name": "West Coast States",
  "description": "Sales territories for Q1 2026",
  "created_at": "2026-01-15T10:30:00Z",
  "boundaries": [
    {
      "gers_id": "overture_gers_id_1",
      "name": "California",
      "admin_level": 4,
      "country": "US"
    }
  ]
}
```

## Project Structure

```
.
├── app.py                 # Main Streamlit application
├── src/
│   ├── query_engine.py    # DuckDB query functions (cached)
│   └── list_storage.py    # JSON storage management
├── list_data/             # Persistent storage directory
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Docker orchestration
└── README.md             # This file
```

## Development

### Key Design Patterns

**Caching:** All DuckDB queries use `@st.cache_data` to avoid re-querying Parquet files on every Streamlit rerun.

**Lazy Loading:** Boundary geometries are only loaded when viewing on the map, never bulk-loaded into memory.

**Session State:** The current working list is stored in Streamlit session state and only persisted when explicitly saved.

### Data Schema

The app expects Overture Maps admin boundary Parquet files with schema:
- `id`: GERS ID (unique identifier)
- `names.primary`: Display name
- `admin_level`: Hierarchical level (2, 4, 6, etc.)
- `country`: ISO country code
- `geometry`: Polygon/MultiPolygon geometries

## Limitations (POC)

This is a proof-of-concept with intentional scope limitations:
- Single-user tool (no authentication)
- No multi-user access or list sharing
- No bulk import/export beyond JSON
- Map shows only one boundary at a time (no full list visualization)
- Boundary selection via dropdowns only (no map-based selection)

## Future Enhancements

When migrating from POC to production:
- Replace flat files with SQL database
- Add multi-user support and authentication
- Implement list sharing and permissions
- Add bulk operations and advanced filtering
- Migrate to cloud storage (Azure Blob, S3)
- Enable full list visualization on map

## Troubleshooting

### "No countries found" error
- Check that your Parquet path is correct
- Verify network access to S3 if using remote data
- Ensure DuckDB httpfs extension is installed (automatic for S3)

### Map not displaying
- Check browser console for JavaScript errors
- Verify geometry data exists for the selected boundary

### Docker volume permissions
```bash
# Ensure list_data directory has correct permissions
chmod 777 list_data
```

## License

This project is provided as-is for demonstration purposes.

## Credits

- **Data:** [Overture Maps Foundation](https://overturemaps.org/)
- **Built with:** Streamlit, DuckDB, Folium, Python