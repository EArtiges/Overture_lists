"""
Tests for Overture release discovery.

Network calls are mocked; no internet access required.
"""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import overture_release
from overture_release import (
    get_latest_release,
    get_default_parquet_path,
    STAC_CATALOG_URL,
    S3_LISTING_URL,
)

STAC_RESPONSE = json.dumps({
    "type": "Catalog",
    "latest": "2026-09-23.1",
    "links": [],
}).encode()

S3_RESPONSE = b"""<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Prefix>release/</Prefix>
<CommonPrefixes><Prefix>release/2026-08-19.0/</Prefix></CommonPrefixes>
<CommonPrefixes><Prefix>release/2026-09-23.1/</Prefix></CommonPrefixes>
<CommonPrefixes><Prefix>release/2026-09-23.0/</Prefix></CommonPrefixes>
</ListBucketResult>"""


def fake_fetch(responses):
    """Build a _fetch replacement returning bytes or raising per URL."""
    def _fetch(url):
        result = responses[url]
        if isinstance(result, Exception):
            raise result
        return result
    return _fetch


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch):
    """Reset the Streamlit cache and env override between tests."""
    get_latest_release.clear()
    monkeypatch.delenv('OVERTURE_PARQUET_PATH', raising=False)
    yield
    get_latest_release.clear()


class TestGetLatestRelease:
    """Test latest release lookup."""

    def test_uses_stac_catalog(self):
        with patch.object(overture_release, '_fetch', fake_fetch({STAC_CATALOG_URL: STAC_RESPONSE})):
            assert get_latest_release() == "2026-09-23.1"

    def test_falls_back_to_s3_listing(self):
        responses = {STAC_CATALOG_URL: OSError("down"), S3_LISTING_URL: S3_RESPONSE}
        with patch.object(overture_release, '_fetch', fake_fetch(responses)):
            assert get_latest_release() == "2026-09-23.1"

    def test_falls_back_when_stac_latest_invalid(self):
        responses = {
            STAC_CATALOG_URL: json.dumps({"latest": "garbage"}).encode(),
            S3_LISTING_URL: S3_RESPONSE,
        }
        with patch.object(overture_release, '_fetch', fake_fetch(responses)):
            assert get_latest_release() == "2026-09-23.1"

    def test_revision_sorted_numerically(self):
        listing = S3_RESPONSE.replace(b"2026-09-23.0", b"2026-09-23.10")
        responses = {STAC_CATALOG_URL: OSError("down"), S3_LISTING_URL: listing}
        with patch.object(overture_release, '_fetch', fake_fetch(responses)):
            assert get_latest_release() == "2026-09-23.10"

    def test_raises_when_all_sources_fail(self):
        responses = {STAC_CATALOG_URL: OSError("down"), S3_LISTING_URL: OSError("down")}
        with patch.object(overture_release, '_fetch', fake_fetch(responses)):
            with pytest.raises(RuntimeError, match="Could not determine latest Overture release"):
                get_latest_release()


class TestGetDefaultParquetPath:
    """Test default path resolution."""

    def test_builds_latest_release_path(self):
        with patch.object(overture_release, '_fetch', fake_fetch({STAC_CATALOG_URL: STAC_RESPONSE})):
            assert get_default_parquet_path() == (
                "s3://overturemaps-us-west-2/release/2026-09-23.1/theme=divisions/type=division/*.parquet"
            )

    def test_env_override_skips_lookup(self, monkeypatch):
        monkeypatch.setenv('OVERTURE_PARQUET_PATH', '/local/data.parquet')
        with patch.object(overture_release, '_fetch', side_effect=AssertionError("should not fetch")):
            assert get_default_parquet_path() == '/local/data.parquet'
