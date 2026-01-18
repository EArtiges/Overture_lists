# Unit Testing Plan - Domain-Driven Design Approach

## Executive Summary

This plan outlines a comprehensive unit testing strategy for the Overture Admin Boundary Tools PoC, following Domain-Driven Design (DDD) principles. We'll test the application in layers: Domain, Application, and Infrastructure.

---

## Testing Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                    │
│              (Streamlit Pages - Manual Testing)         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│              APPLICATION LAYER TESTS                    │
│  - Use case orchestration                               │
│  - Service layer coordination                           │
│  - Business workflows                                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                DOMAIN LAYER TESTS                       │
│  - Business logic & rules                               │
│  - Entity behavior                                      │
│  - Domain invariants                                    │
│  - Value objects                                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│            INFRASTRUCTURE LAYER TESTS                   │
│  - Database operations (DatabaseStorage)                │
│  - Query engine (OvertureQueryEngine)                   │
│  - External data access                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 1. DOMAIN LAYER TESTING

### 1.1 Core Domain Entities

#### **Division Entity**
**Domain Concepts:**
- Geographic administrative boundary
- Has identity (system_id from Overture)
- Has hierarchical relationships (parent-child)
- Can be associated with CRM mappings

**Test Cases:**
```python
# tests/domain/test_division.py

class TestDivision:
    - test_create_division_with_valid_data()
    - test_division_identity_equality()  # Same system_id = same division
    - test_division_requires_system_id()
    - test_division_name_validation()
    - test_division_country_code_format()
    - test_division_geometry_optional()
    - test_division_geometry_json_serialization()
```

**Business Rules to Test:**
- ✓ Division must have unique system_id
- ✓ Division must have non-empty name
- ✓ Geometry can be null or valid GeoJSON
- ✓ Division properties (system_id, name, subtype, country) are immutable once created

---

#### **List Entity (Aggregate Root)**
**Domain Concepts:**
- Collection of divisions OR CRM clients (not mixed)
- Has name and type ('division' or 'client')
- Must have at least one item
- Name uniqueness enforced by hash (name + type)
- Audit trail (created_at, updated_at)

**Test Cases:**
```python
# tests/domain/test_list.py

class TestList:
    - test_create_division_list()
    - test_create_client_list()
    - test_list_requires_name()
    - test_list_requires_type()
    - test_list_type_must_be_valid()  # 'division' or 'client'
    - test_list_cannot_be_empty()  # Must have ≥1 item
    - test_list_hash_generation()
    - test_list_duplicate_hash_detection()
    - test_add_division_to_list()
    - test_remove_division_from_list()
    - test_cannot_add_duplicate_division()
    - test_cannot_mix_divisions_and_clients()
    - test_list_update_timestamp()
```

**Business Rules to Test:**
- ✓ List must have unique name within its type
- ✓ List cannot be empty (≥1 item required)
- ✓ List items must be homogeneous (all divisions OR all clients)
- ✓ Cannot add same division twice to same list
- ✓ Hash = MD5(name + type)
- ✓ Updated_at changes on modification

---

#### **CRM Mapping Entity**
**Domain Concepts:**
- 1:1 mapping between Division and CRM Account
- Has custom metadata (account_name, custom_admin_level as text label)
- Caches geometry for performance

**Test Cases:**
```python
# tests/domain/test_crm_mapping.py

class TestCRMMapping:
    - test_create_crm_mapping()
    - test_one_division_one_mapping()  # 1:1 constraint
    - test_mapping_requires_system_id()
    - test_mapping_requires_division_id()
    - test_mapping_with_custom_admin_level_text()  # Text like "Regional Office"
    - test_mapping_geometry_caching()
    - test_update_mapping_metadata()
    - test_delete_mapping_cascade()  # If division deleted
```

**Business Rules to Test:**
- ✓ Each division can have max 1 CRM mapping
- ✓ System_id must be unique (CRM account ID)
- ✓ Custom admin level is free-text label (e.g., "Regional Office", "Sales Territory")
- ✓ Geometry cached from division
- ✓ Deleting division deletes mapping

---

#### **Relationship Entity**
**Domain Concepts:**
- Organizational hierarchy between divisions (many-to-many)
- Types: 'reports_to', 'collaborates_with'
- Directional (parent → child)
- Independent of Overture's parent_division_id (our own business rules)

**Test Cases:**
```python
# tests/domain/test_relationship.py

class TestRelationship:
    - test_create_reports_to_relationship()
    - test_create_collaborates_with_relationship()
    - test_relationship_requires_parent_and_child()
    - test_relationship_requires_valid_type()
    - test_cannot_create_self_relationship()  # DB CHECK constraint enforces this
    - test_unique_relationship_constraint()  # Same parent+child+type
    - test_can_have_multiple_relationship_types()  # Same pair, different types
    - test_delete_division_cascades_relationships()
    - test_many_to_many_relationships_allowed()
```

**Business Rules to Test:**
- ✓ Self-relationships prevented (CHECK: parent_division_id != child_division_id)
- ✓ Relationship type must be valid enum ('reports_to' or 'collaborates_with')
- ✓ (parent, child, type) tuple must be unique
- ✓ Same pair can have multiple relationship types
- ✓ Deleting division deletes all its relationships (CASCADE)
- ✓ Many-to-many relationships are allowed (division can have multiple parents/children)

---

### 1.2 Value Objects

#### **ListHash Value Object**
```python
# tests/domain/test_value_objects.py

class TestListHash:
    - test_hash_generation_from_name_and_type()
    - test_hash_equality()
    - test_hash_immutability()
    - test_same_name_different_type_different_hash()
```

#### **GeometryJSON Value Object**
```python
class TestGeometryJSON:
    - test_parse_valid_geojson()
    - test_reject_invalid_geojson()
    - test_geometry_simplification()
    - test_geometry_serialization()
```

---

### 1.3 Domain Services

#### **Hierarchy Service**
**Domain Concepts:**
- Navigate admin hierarchies (user-defined relationships)
- Collect immediate children only (one level below root)
- Support filtering by relationship type

**Test Cases:**
```python
# tests/domain/test_hierarchy_service.py

class TestHierarchyService:
    - test_get_admin_children_via_relationships()
    - test_get_children_by_relationship_type()  # Filter by 'reports_to' or 'collaborates_with'
    - test_empty_hierarchy()  # Division with no children
    - test_mixed_relationship_types()
    - test_multiple_parents()  # Child can have many parents
```

**Business Rules to Test:**
- ✓ Admin hierarchy follows relationships table
- ✓ Only collect immediate children (one level below root)
- ✓ Can filter by relationship type
- ✓ Division can have multiple parents (many-to-many)

---

#### **Duplicate Detection Service**
```python
# tests/domain/test_duplicate_detection_service.py

class TestDuplicateDetectionService:
    - test_detect_duplicate_list_name()
    - test_detect_duplicate_division_in_list()
    - test_allow_same_name_different_type()
    - test_case_sensitive_comparison()
```

---

## 2. APPLICATION LAYER TESTING

### 2.1 Use Cases / Application Services

#### **CreateListUseCase**
```python
# tests/application/test_create_list_use_case.py

class TestCreateListUseCase:
    - test_create_division_list_success()
    - test_create_client_list_success()
    - test_create_list_with_duplicate_name_fails()
    - test_create_empty_list_fails()
    - test_create_list_invalid_type_fails()
    - test_create_list_persists_to_database()
    - test_create_list_returns_list_id()
```

#### **AddDivisionToListUseCase**
```python
class TestAddDivisionToListUseCase:
    - test_add_division_to_existing_list()
    - test_add_duplicate_division_fails()
    - test_add_to_nonexistent_list_fails()
    - test_add_updates_timestamp()
```

#### **GenerateListFromHierarchyUseCase**
```python
class TestGenerateListFromHierarchyUseCase:
    - test_generate_from_admin_hierarchy()
    - test_generate_empty_hierarchy()  # Root with no children
    - test_generate_includes_root_division()
    - test_generate_one_level_below_root()  # Only immediate children
    - test_generate_with_relationship_type_filter()
```

#### **CreateCRMMappingUseCase**
```python
class TestCreateCRMMappingUseCase:
    - test_create_mapping_success()
    - test_create_duplicate_mapping_fails()
    - test_create_mapping_caches_geometry()
    - test_create_mapping_invalid_division_fails()
```

#### **CreateRelationshipUseCase**
```python
class TestCreateRelationshipUseCase:
    - test_create_reports_to_relationship()
    - test_create_collaborates_with_relationship()
    - test_create_self_relationship_fails()  # DB CHECK constraint
    - test_create_duplicate_relationship_fails()
    - test_create_multiple_relationship_types_for_same_pair()
```

---

## 3. INFRASTRUCTURE LAYER TESTING

### 3.1 Database Storage (SQLite)

#### **DatabaseStorage - Lists Operations**
```python
# tests/infrastructure/test_database_storage_lists.py

class TestDatabaseStorageLists:
    - test_save_division_list()
    - test_save_client_list()
    - test_get_list_by_id()
    - test_get_all_lists()
    - test_get_lists_by_type()
    - test_delete_list_cascades_items()
    - test_hash_uniqueness_constraint()  # Hash from name+type, immutable
    - test_transaction_rollback_on_error()
    - test_concurrent_list_creation()  # Race conditions
```

#### **DatabaseStorage - Divisions Cache**
```python
# tests/infrastructure/test_database_storage_divisions.py

class TestDatabaseStorageDivisions:
    - test_cache_division()
    - test_get_cached_division()
    - test_cache_division_with_geometry()
    - test_update_cached_geometry()
    - test_system_id_uniqueness()
```

#### **DatabaseStorage - CRM Mappings**
```python
# tests/infrastructure/test_database_storage_crm.py

class TestDatabaseStorageCRMMappings:
    - test_save_crm_mapping()
    - test_get_mapping_by_system_id()
    - test_get_mapping_by_division_id()
    - test_one_to_one_constraint()
    - test_delete_mapping()
    - test_update_mapping_metadata()
```

#### **DatabaseStorage - Relationships**
```python
# tests/infrastructure/test_database_storage_relationships.py

class TestDatabaseStorageRelationships:
    - test_create_relationship()
    - test_get_children_for_parent()
    - test_get_parents_for_child()
    - test_delete_relationship()
    - test_unique_constraint()
    - test_cascade_delete_when_division_deleted()
```

---

### 3.2 Query Engine (DuckDB)

#### **OvertureQueryEngine**
```python
# tests/infrastructure/test_query_engine.py

class TestOvertureQueryEngine:
    - test_get_countries()
    - test_get_child_divisions()
    - test_get_division_by_id()
    - test_search_boundaries()
    - test_get_geometry()
    - test_geometry_simplification()
    - test_cache_behavior()  # Verify caching works
    - test_handle_missing_file()
    - test_handle_s3_connection_error()
    - test_filter_by_admin_level()
    - test_filter_by_country()
```

**Mock Strategy:**
- Use local test Parquet files (extend `tests/generate_test_data.py`)
- Mock DuckDB connection for error scenarios
- Verify SQL query structure without hitting S3

---

**Note:** CRM Client Storage tests are omitted as the JSON file is temporary and will be replaced with real CRM API integration.

---

## 4. INTEGRATION TESTING

### 4.1 End-to-End Workflows

```python
# tests/integration/test_list_creation_workflow.py

class TestListCreationWorkflow:
    - test_create_and_save_division_list_workflow()
    - test_create_and_visualize_list_workflow()
    - test_duplicate_prevention_workflow()

# tests/integration/test_hierarchy_workflow.py

class TestHierarchyWorkflow:
    - test_define_relationship_and_generate_list()
    - test_spatial_hierarchy_auto_generation()

# tests/integration/test_crm_workflow.py

class TestCRMWorkflow:
    - test_map_division_to_crm_and_create_client_list()
```

---

## 5. MOCK DATA STRATEGY

### 5.1 Test Data Fixtures

#### **Division Test Data**
```python
# tests/fixtures/divisions.py

@pytest.fixture
def sample_country():
    return Division(
        system_id="0858d7df-4c21-6d95-ffff-aadc92e00b0a",
        name="United States",
        subtype="country",
        country="US",
        # admin_level not stored in divisions table
        # admin_level=1,
        # parent_division_id not stored in divisions table
        # parent_division_id=None,
        geometry_json=None
    )

@pytest.fixture
def sample_state():
    return Division(
        system_id="0858d7e2-aa18-ae63-ffff-e4dc0fb91919",
        name="California",
        subtype="region",
        country="US",
        # admin_level not stored in divisions table
        # admin_level=2,
        # parent_division_id not stored in divisions table
        # parent_division_id="0858d7df-4c21-6d95-ffff-aadc92e00b0a",
        geometry_json=None
    )

@pytest.fixture
def sample_county():
    return Division(
        system_id="0858d7e4-1234-5678-ffff-abcd12345678",
        name="Los Angeles County",
        subtype="county",
        country="US",
        # admin_level not stored in divisions table
        # admin_level=3,
        # parent_division_id not stored in divisions table
        # parent_division_id="0858d7e2-aa18-ae63-ffff-e4dc0fb91919",
        geometry_json=load_test_geometry("la_county.geojson")
    )

@pytest.fixture
def sample_division_hierarchy():
    """Returns US → California → LA County hierarchy"""
    return [sample_country(), sample_state(), sample_county()]
```

#### **List Test Data**
```python
# tests/fixtures/lists.py

@pytest.fixture
def sample_division_list(sample_state, sample_county):
    return List(
        name="West Coast Territories",
        type="division",
        notes="Primary sales territories",
        divisions=[sample_state, sample_county]
    )

@pytest.fixture
def sample_client_list():
    return List(
        name="Enterprise Clients Q1",
        type="client",
        notes="Target list for Q1 campaign",
        client_ids=["CRM-001", "CRM-002", "CRM-003"]
    )
```

#### **CRM Mapping Test Data**
```python
# tests/fixtures/crm_mappings.py

@pytest.fixture
def sample_crm_mapping(sample_state):
    return CRMMapping(
        system_id="CRM-WEST-001",
        division_id=sample_state.system_id,
        account_name="California Sales Territory",
        custom_admin_level="Regional Office",
        geometry_json=sample_state.geometry_json
    )
```

#### **Relationship Test Data**
```python
# tests/fixtures/relationships.py

@pytest.fixture
def sample_reports_to_relationship(sample_county, sample_state):
    return Relationship(
        # parent_division_id not stored in divisions table
        # parent_division_id=sample_state.system_id,
        child_division_id=sample_county.system_id,
        relationship_type="reports_to"
    )
```

---

### 5.2 Parquet Test Data

**Extend `tests/generate_test_data.py`:**
```python
# tests/test_data_generator.py

def generate_comprehensive_test_data():
    """
    Generate realistic test dataset:
    - 5 countries (US, UK, CA, FR, DE)
    - 20 states/provinces (4 per country)
    - 100 counties/districts (5 per state)
    - 50 cities (selected counties only)

    Total: 175 boundaries across 4 admin levels
    """

def generate_hierarchical_test_data():
    """
    Generate complete US hierarchy:
    US → California → [LA County, SF County, SD County]
       → Texas → [Harris County, Dallas County]

    For testing recursive hierarchy traversal
    """

def generate_edge_case_data():
    """
    Generate edge cases:
    - Divisions with very long names (>100 chars)
    - Divisions with special characters
    - Orphaned divisions (parent doesn't exist)
    - Circular parent references
    - Missing geometry
    """
```

---

### 5.3 SQLite Test Database

```python
# tests/fixtures/database.py

@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    db_path = ":memory:"
    storage = DatabaseStorage(db_path)
    storage.initialize_schema()
    yield storage
    storage.close()

@pytest.fixture
def populated_test_db(test_db, sample_division_hierarchy):
    """Test database pre-populated with sample data"""
    for division in sample_division_hierarchy:
        test_db.cache_division(division)
    return test_db
```

---

### 5.4 Mock CRM Client Data

```python
# tests/fixtures/crm_clients.json

{
  "clients": [
    {
      "system_id": "CRM-001",
      "name": "Acme Corporation",
      "country": "US",
      "territory": "West"
    },
    {
      "system_id": "CRM-002",
      "name": "TechStart Inc",
      "country": "US",
      "territory": "East"
    },
    {
      "system_id": "CRM-003",
      "name": "Global Solutions Ltd",
      "country": "UK",
      "territory": "London"
    }
  ]
}
```

---

## 6. TESTING INFRASTRUCTURE

### 6.1 Directory Structure

```
tests/
├── __init__.py
├── conftest.py                      # Shared pytest configuration
│
├── domain/                          # Domain layer tests
│   ├── __init__.py
│   ├── test_division.py
│   ├── test_list.py
│   ├── test_crm_mapping.py
│   ├── test_relationship.py
│   ├── test_value_objects.py
│   ├── test_hierarchy_service.py
│   └── test_duplicate_detection_service.py
│
├── application/                     # Application layer tests
│   ├── __init__.py
│   ├── test_create_list_use_case.py
│   ├── test_add_division_to_list_use_case.py
│   ├── test_generate_list_from_hierarchy_use_case.py
│   ├── test_create_crm_mapping_use_case.py
│   └── test_create_relationship_use_case.py
│
├── infrastructure/                  # Infrastructure layer tests
│   ├── __init__.py
│   ├── test_database_storage_lists.py
│   ├── test_database_storage_divisions.py
│   ├── test_database_storage_crm.py
│   ├── test_database_storage_relationships.py
│   ├── test_query_engine.py
│   └── test_crm_client_storage.py
│
├── integration/                     # Integration tests
│   ├── __init__.py
│   ├── test_list_creation_workflow.py
│   ├── test_hierarchy_workflow.py
│   └── test_crm_workflow.py
│
├── fixtures/                        # Test data fixtures
│   ├── __init__.py
│   ├── divisions.py
│   ├── lists.py
│   ├── crm_mappings.py
│   ├── relationships.py
│   ├── database.py
│   └── crm_clients.json
│
├── test_data/                       # Static test data
│   ├── sample_boundaries.parquet
│   ├── hierarchical_data.parquet
│   ├── edge_case_data.parquet
│   └── geometries/
│       ├── us.geojson
│       ├── california.geojson
│       └── la_county.geojson
│
└── generate_test_data.py            # Enhanced test data generator
```

---

### 6.2 Dependencies

```python
# requirements-test.txt

pytest==8.3.4
pytest-cov==6.0.0              # Coverage reporting
pytest-mock==3.14.0            # Mocking utilities
pytest-asyncio==0.24.0         # Async test support
freezegun==1.5.1               # Time mocking for timestamps
faker==30.8.2                  # Generate realistic fake data
hypothesis==6.122.3            # Property-based testing
```

---

### 6.3 Pytest Configuration

```python
# tests/conftest.py

import pytest
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture(autouse=True)
def reset_streamlit_cache():
    """Clear Streamlit cache between tests"""
    # Prevents cache pollution between tests
    pass

@pytest.fixture
def mock_parquet_path(tmp_path):
    """Provide path to test Parquet file"""
    return str(tmp_path / "test_boundaries.parquet")
```

```ini
# pytest.ini

[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
    database: Tests requiring database
```

---

## 7. TEST EXECUTION PLAN

### Phase 1: Foundation (Week 1)
1. Set up test infrastructure (conftest.py, pytest.ini)
2. Create domain entity models (if not already extracted)
3. Generate comprehensive test data (Parquet + fixtures)
4. Write domain layer tests (Division, List, CRMMapping, Relationship)

### Phase 2: Core Logic (Week 2)
5. Write domain service tests (Hierarchy, DuplicateDetection)
6. Write application use case tests
7. Achieve 80%+ coverage on domain + application layers

### Phase 3: Infrastructure (Week 3)
8. Write DatabaseStorage tests (all operations)
9. Write QueryEngine tests (with mocked data)
10. Write CRMClientStorage tests

### Phase 4: Integration (Week 4)
11. Write end-to-end workflow tests
12. Performance testing (large datasets)
13. Edge case and error handling tests
14. CI/CD integration (GitHub Actions)

---

## 8. SUCCESS CRITERIA

| Metric | Target |
|--------|--------|
| **Code Coverage** | ≥80% for src/ directory |
| **Domain Layer Coverage** | ≥95% |
| **Application Layer Coverage** | ≥90% |
| **Infrastructure Layer Coverage** | ≥75% |
| **Test Execution Time** | <5 minutes for full suite |
| **Test Reliability** | 0 flaky tests |
| **Documentation** | Every test has clear docstring |

---

## 9. NEXT STEPS

### Immediate Actions:
1. **Review this plan** - Discuss and refine with team
2. **Extract domain models** - Refactor src/ to separate domain entities from infrastructure
3. **Create fixtures** - Build comprehensive mock data library
4. **Start with domain tests** - Highest value, lowest dependencies

### Long-term:
- Integrate with CI/CD (run tests on every PR)
- Add mutation testing (PIT, mutmut) to verify test quality
- Property-based testing with Hypothesis for edge cases
- Performance regression tests

---

## 10. TESTING PRINCIPLES

✅ **DO:**
- Test behavior, not implementation
- Use descriptive test names: `test_cannot_add_duplicate_division_to_list()`
- Follow AAA pattern: Arrange, Act, Assert
- Keep tests isolated and independent
- Use fixtures for common setup
- Mock external dependencies (S3, file I/O)
- Test edge cases and error conditions

❌ **DON'T:**
- Test framework code (DuckDB, SQLite internals)
- Test Streamlit UI directly (use manual testing)
- Couple tests to implementation details
- Share state between tests
- Skip assertions
- Write tests that depend on test execution order

---

**This plan provides a roadmap for creating a robust, maintainable test suite that validates the business logic and ensures the PoC works correctly as it evolves toward production.**
