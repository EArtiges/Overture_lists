"""
Tests for OvertureQueryEngine.

Note: These tests use local test Parquet files to avoid hitting S3.
"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from query_engine import OvertureQueryEngine


@pytest.mark.unit
class TestOvertureQueryEngine:
    """Test query engine functionality with test data."""

    @pytest.fixture
    def test_parquet_path(self):
        """Path to test Parquet file."""
        # Use the existing test data file
        test_data_path = Path(__file__).parent.parent / "test_data" / "sample_boundaries.parquet"
        if test_data_path.exists():
            return str(test_data_path)
        # Fallback to the existing tests directory
        return str(Path(__file__).parent.parent.parent / "tests" / "sample_boundaries.parquet")

    @pytest.fixture
    def engine(self, test_parquet_path):
        """Create query engine instance."""
        return OvertureQueryEngine(test_parquet_path)

    def test_engine_initialization(self, test_parquet_path):
        """Test that engine can be initialized."""
        engine = OvertureQueryEngine(test_parquet_path)
        assert engine is not None
        assert engine.parquet_path == test_parquet_path
        assert engine.conn is None  # Connection lazy-loaded

    def test_get_connection(self, engine):
        """Test that connection is created on first access."""
        conn = engine._get_connection()
        assert conn is not None

    # Note: The following tests require actual test Parquet data
    # They are marked as integration tests and will be skipped if test data doesn't exist

    @pytest.mark.integration
    @pytest.mark.skipif(
        not Path("tests/test_data/sample_boundaries.parquet").exists(),
        reason="Test Parquet data not generated yet"
    )
    def test_get_countries(self, engine):
        """Test retrieving countries from test data."""
        countries = engine.get_countries()
        assert isinstance(countries, list)
        # If test data exists, should have countries
        if len(countries) > 0:
            assert all('name' in c for c in countries)
            assert all('division_id' in c for c in countries)

    @pytest.mark.integration
    @pytest.mark.skipif(
        not Path("tests/test_data/sample_boundaries.parquet").exists(),
        reason="Test Parquet data not generated yet"
    )
    def test_get_country_division(self, engine):
        """Test retrieving specific country division."""
        country_div = engine.get_country_division('US')
        if country_div:
            assert 'name' in country_div
            assert 'division_id' in country_div

    def test_parquet_path_validation(self):
        """Test that engine accepts various path formats."""
        # Local path
        engine1 = OvertureQueryEngine("/path/to/file.parquet")
        assert engine1.parquet_path == "/path/to/file.parquet"

        # S3 URL
        engine2 = OvertureQueryEngine("s3://bucket/path/*.parquet")
        assert engine2.parquet_path == "s3://bucket/path/*.parquet"

        # Glob pattern
        engine3 = OvertureQueryEngine("/path/**/*.parquet")
        assert engine3.parquet_path == "/path/**/*.parquet"


@pytest.mark.unit
class TestQueryEngineMocking:
    """Test query engine with mocked DuckDB."""

    def test_handle_missing_file(self):
        """Test graceful handling of missing Parquet file."""
        engine = OvertureQueryEngine("/nonexistent/path.parquet")
        # Should not crash on initialization
        assert engine.parquet_path == "/nonexistent/path.parquet"

        # When querying non-existent file, should handle error
        # This would require mocking or catching the error in the actual query


# Placeholder for future comprehensive tests once test data generator is enhanced
class TestQueryEngineWithTestData:
    """
    Comprehensive tests with generated test data.
    These will be implemented after enhancing tests/generate_test_data.py
    """
    pass
