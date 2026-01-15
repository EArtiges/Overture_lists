# Testing Guide

## Overview

This document outlines testing procedures for the Overture Admin Boundary List Builder POC.

## Test Data Generation

For local testing without access to actual Overture Maps data, you can generate sample test data:

```bash
# Install dependencies first
pip install -r requirements.txt

# Generate test Parquet file
python tests/generate_test_data.py
```

This creates `tests/test_boundaries.parquet` with sample boundaries for:
- **United States:** Country, States (CA, OR, WA), Counties (Los Angeles, San Francisco)
- **United Kingdom:** Country, Regions (England, Scotland)
- **Canada:** Country, Provinces (Ontario, British Columbia)

To use test data in the app:
1. Start the application
2. In the sidebar, change "Parquet Data Path" to: `./tests/test_boundaries.parquet`
3. Begin testing with the sample data

## Manual Test Cases

### Test Case 1: Basic Boundary Selection
**Objective:** Verify cascading dropdown filtering works correctly

**Steps:**
1. Select "US" from Country dropdown
2. Verify Admin Level dropdown populates (should show: 2, 4, 6)
3. Select "4" (State level)
4. Verify Boundary dropdown shows: California, Oregon, Washington
5. Select "California"
6. Verify map displays California geometry

**Expected Result:** Each dropdown filters correctly and map displays selected boundary

---

### Test Case 2: Add Boundaries to List
**Objective:** Verify adding boundaries to current list

**Steps:**
1. Select and view "California" (US, Level 4)
2. Click "Add to List"
3. Verify success message appears
4. Verify table shows California entry
5. Select and view "Oregon"
6. Click "Add to List"
7. Verify table now shows 2 entries

**Expected Result:** Boundaries are added to table without duplicates

---

### Test Case 3: Prevent Duplicate Additions
**Objective:** Verify duplicate boundary prevention

**Steps:**
1. Add "California" to list
2. Select "California" again
3. Click "Add to List" again
4. Verify warning message appears
5. Verify table still shows only 1 California entry

**Expected Result:** Duplicate warning shown, boundary not added twice

---

### Test Case 4: Remove Boundaries from List
**Objective:** Verify boundary removal functionality

**Steps:**
1. Add 3 boundaries to list (CA, OR, WA)
2. In the data editor table, delete Oregon row
3. Verify table updates to show only 2 boundaries

**Expected Result:** Boundary removed from list successfully

---

### Test Case 5: Save List - Happy Path
**Objective:** Verify successful list saving

**Steps:**
1. Add 2-3 boundaries to list
2. Enter List Name: "Test List"
3. Enter Description: "Testing save functionality"
4. Click "Save List"
5. Verify success message with list ID
6. Check `list_data/` directory for new JSON file

**Expected Result:**
- Success message displayed
- JSON file created with correct structure
- List appears in sidebar "Saved Lists"

---

### Test Case 6: Save Validation - Missing Name
**Objective:** Verify validation prevents saving without name

**Steps:**
1. Add 2 boundaries to list
2. Leave List Name blank
3. Click "Save List"
4. Verify error message appears

**Expected Result:** Error message: "Please enter a list name"

---

### Test Case 7: Save Validation - Empty List
**Objective:** Verify validation prevents saving empty list

**Steps:**
1. Ensure list is empty (no boundaries added)
2. Enter List Name: "Empty Test"
3. Click "Save List"
4. Verify error message appears

**Expected Result:** Error message: "Cannot save an empty list"

---

### Test Case 8: Load Saved List
**Objective:** Verify loading previously saved list

**Steps:**
1. Save a list with 3 boundaries
2. Click "Clear List" to reset
3. In sidebar, expand the saved list
4. Click "Load"
5. Verify success message
6. Verify table populates with 3 boundaries
7. Verify list name and description are restored

**Expected Result:** Saved list fully restored to working session

---

### Test Case 9: Delete Saved List
**Objective:** Verify list deletion

**Steps:**
1. Save a list
2. In sidebar, expand the saved list
3. Click "Delete"
4. Verify success message
5. Verify list disappears from sidebar
6. Check `list_data/` directory - file should be gone

**Expected Result:** List removed from storage and sidebar

---

### Test Case 10: Clear Current List
**Objective:** Verify clearing working list

**Steps:**
1. Add 3 boundaries to list
2. Enter name and description
3. Click "Clear List"
4. Verify success message
5. Verify table is empty
6. Verify name and description fields are cleared

**Expected Result:** All list data cleared, ready for new list

---

### Test Case 11: Cross-Country Selection
**Objective:** Verify switching between countries

**Steps:**
1. Select "US" and view California
2. Change country to "GB"
3. Verify Admin Level dropdown updates
4. Select "4" (Region level)
5. Verify Boundary dropdown shows UK regions
6. Select "Scotland"
7. Verify map updates to show Scotland

**Expected Result:** Dropdowns and map update correctly when country changes

---

### Test Case 12: Multiple Admin Levels
**Objective:** Verify working with different admin levels

**Steps:**
1. Add "California" (Level 4) to list
2. Add "Los Angeles County" (Level 6) to list
3. Add "United States" (Level 2) to list
4. Verify all 3 appear in table with correct admin_level values
5. Save the list
6. Load the list
7. Verify all levels preserved correctly

**Expected Result:** Mixed admin levels handled correctly

---

### Test Case 13: Map Visualization Only
**Objective:** Verify viewing boundaries without adding

**Steps:**
1. Select "California" and view on map
2. DO NOT click "Add to List"
3. Select "Oregon" and view on map
4. Verify map updates to show Oregon (not both)
5. Verify list table remains empty

**Expected Result:** Map shows current selection only; viewing doesn't add to list

---

### Test Case 14: Session Persistence
**Objective:** Verify session state maintains list during navigation

**Steps:**
1. Add 3 boundaries to list
2. Change Parquet path in sidebar (triggers some UI updates)
3. Select different filters
4. Verify list table still shows all 3 boundaries
5. Verify name/description preserved

**Expected Result:** Current list persists throughout session

---

### Test Case 15: List File Format Validation
**Objective:** Verify saved JSON format matches specification

**Steps:**
1. Create and save a list with 2 boundaries
2. Open the JSON file in `list_data/`
3. Verify structure:
   - `list_id`: MD5 hash string
   - `list_name`: matches entered name
   - `description`: matches entered description
   - `created_at`: ISO 8601 timestamp with Z
   - `boundaries`: array of objects with gers_id, name, admin_level, country

**Expected Result:** JSON structure exactly matches design specification

---

## Edge Cases

### Edge Case 1: Very Long List Names
- List name: 200 characters
- Should save and display correctly

### Edge Case 2: Special Characters
- List name: "Test List™️ <>&"
- Description with quotes, newlines
- Should handle and escape correctly

### Edge Case 3: Empty Description
- Save list with name but no description
- Should allow and save empty string

### Edge Case 4: Rapid Selections
- Quickly change dropdown selections
- Should not cause errors or race conditions

### Edge Case 5: Large Number of Boundaries
- Add 50+ boundaries to a list
- Should save and load without performance issues

## Automated Testing (Future)

For production, implement:

```python
# Unit tests for query_engine.py
def test_get_countries():
    engine = create_query_engine("test_data.parquet")
    countries = engine.get_countries()
    assert "US" in countries
    assert "GB" in countries

# Unit tests for list_storage.py
def test_save_and_load_list():
    storage = ListStorage("./test_data")
    list_id = storage.save_list(
        "Test", "Desc",
        [{"gers_id": "1", "name": "Test", "admin_level": 2, "country": "US"}]
    )
    loaded = storage.load_list(list_id)
    assert loaded['list_name'] == "Test"
```

## Integration Testing Checklist

- [ ] Test with actual Overture Maps S3 data
- [ ] Test with local Parquet files
- [ ] Test with HTTP-served Parquet files
- [ ] Verify Docker container starts and volume mounts work
- [ ] Test on Windows, Mac, Linux
- [ ] Verify memory usage stays reasonable with large datasets
- [ ] Test network failure handling (S3 timeouts)
- [ ] Verify cache invalidation works correctly

## Performance Benchmarks

Expected performance with test data:
- Country list query: < 100ms
- Admin level query: < 100ms
- Boundary list query: < 500ms
- Geometry query: < 1s
- Save list: < 100ms
- Load list: < 50ms

## Known Limitations

1. **DuckDB Spatial:** Requires geometry support - may need `duckdb_spatial` extension
2. **Large Geometries:** Very complex boundaries may render slowly in Folium
3. **S3 Access:** Requires network connectivity and appropriate permissions
4. **Cache:** Streamlit cache persists until server restart or cache clear

## Troubleshooting Tests

### "No countries found"
- Check Parquet path is correct
- Verify test data was generated
- Check DuckDB can read the file

### Map not rendering
- Check browser console for JS errors
- Verify geometry data format
- Ensure Folium version is compatible

### JSON file not created
- Check `list_data/` directory exists
- Verify write permissions
- Check disk space

## Test Data Cleanup

After testing:
```bash
# Remove test Parquet files
rm tests/test_boundaries.parquet

# Remove test list files
rm list_data/*.json
```

## Reporting Issues

When reporting bugs, include:
1. Steps to reproduce
2. Expected vs actual behavior
3. Browser and OS version
4. Console errors (if any)
5. Sample list JSON (if relevant)
