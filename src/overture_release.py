"""
Overture Maps release discovery

Resolves the latest Overture Maps release so the app always queries current
data without hardcoding a release date. Overture only keeps the most recent
few releases on S3, so pinned release paths stop working after a few months.
"""

import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

import streamlit as st

STAC_CATALOG_URL = "https://stac.overturemaps.org/catalog.json"
S3_LISTING_URL = (
    "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/"
    "?list-type=2&prefix=release/&delimiter=/"
)
DIVISIONS_PATH_TEMPLATE = (
    "s3://overturemaps-us-west-2/release/{release}/theme=divisions/type=division/*.parquet"
)
RELEASE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.\d+$")
REQUEST_TIMEOUT = 10


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def _release_sort_key(release: str):
    date, _, revision = release.partition('.')
    return date, int(revision)


def _latest_from_stac() -> str:
    """Read the 'latest' release from Overture's STAC catalog."""
    catalog = json.loads(_fetch(STAC_CATALOG_URL))
    release = catalog.get('latest')
    if not release or not RELEASE_PATTERN.match(release):
        raise ValueError(f"Unexpected 'latest' value in STAC catalog: {release!r}")
    return release


def _latest_from_s3_listing() -> str:
    """Find the most recent release prefix by listing the public S3 bucket."""
    root = ET.fromstring(_fetch(S3_LISTING_URL))
    releases = [
        el.text.strip('/').split('/')[-1]
        for el in root.iter()
        if el.tag.endswith('Prefix') and el.text and el.text != 'release/'
    ]
    releases = [r for r in releases if RELEASE_PATTERN.match(r)]
    if not releases:
        raise ValueError("No releases found in S3 bucket listing")
    return max(releases, key=_release_sort_key)


@st.cache_data(ttl=6 * 3600, show_spinner="Looking up latest Overture release...")
def get_latest_release() -> str:
    """
    Get the latest Overture Maps release identifier (e.g. '2026-09-23.1').

    Tries the STAC catalog first, then falls back to listing the S3 bucket.
    Cached for 6 hours so long-running servers pick up new releases.

    Raises:
        RuntimeError: If the release cannot be determined from any source.
    """
    errors = []
    for source in (_latest_from_stac, _latest_from_s3_listing):
        try:
            return source()
        except Exception as e:
            errors.append(f"{source.__name__}: {e}")
    raise RuntimeError("Could not determine latest Overture release (" + "; ".join(errors) + ")")


def get_default_parquet_path() -> str:
    """
    Get the divisions Parquet path to use by default.

    Uses OVERTURE_PARQUET_PATH if set (local file or pinned release),
    otherwise points at the latest Overture release on S3.
    """
    override = os.getenv('OVERTURE_PARQUET_PATH')
    if override:
        return override
    return DIVISIONS_PATH_TEMPLATE.format(release=get_latest_release())
