"""
Tests for Route Discovery and Catalog Generation (Member 1 - SIH26056).
"""

import os
import tempfile
from scrapers.route_discovery import RouteDiscovery, INDIAN_DOMESTIC_AIRPORTS, SIH_REFERENCE_ROUTES


def test_is_valid_domestic_code():
    rd = RouteDiscovery(source_name="yatra")
    assert rd.is_valid_domestic_code("DEL") is True
    assert rd.is_valid_domestic_code("bom ") is True
    assert rd.is_valid_domestic_code("JFK") is False
    assert rd.is_valid_domestic_code("LHR") is False


def test_discover_routes_from_payload():
    rd = RouteDiscovery(source_name="yatra")
    mock_payload = '''
    var mainData = {
        "resultData": [
            {
                "fltSchedule": {
                    "DELBOM20261017": {},
                    "BLRHYD20261017": {},
                    "JFKDEL20261017": {},
                    "DELDEL20261017": {}
                }
            }
        ]
    };
    '''
    routes = rd.discover_routes_from_payload(mock_payload)
    assert ("DEL", "BOM") in routes
    assert ("BLR", "HYD") in routes
    # International and self-loops must be excluded
    assert ("JFK", "DEL") not in routes
    assert ("DEL", "DEL") not in routes


def test_generate_full_domestic_catalog():
    rd = RouteDiscovery(source_name="yatra")
    extracted = {("DEL", "BOM"), ("COK", "MAA")}
    catalog = rd.generate_full_domestic_catalog(extracted_routes=extracted)

    assert len(catalog) > 0
    route_ids = [c["route_id"] for c in catalog]
    assert len(route_ids) == len(set(route_ids))  # unique IDs

    routes = [c["route"] for c in catalog]
    assert "DEL-BOM" in routes
    assert "BOM-DEL" in routes  # directionality preserved
    assert "COK-MAA" in routes

    # Check SIH reference status
    del_bom_item = next(c for c in catalog if c["route"] == "DEL-BOM")
    assert del_bom_item["discoverability_status"] in ["REF_SIH", "VERIFIED_LIVE"]
    assert del_bom_item["domestic"] is True


def test_duplicate_and_self_loop_exclusion():
    rd = RouteDiscovery(source_name="yatra")
    catalog = rd.generate_full_domestic_catalog()
    for item in catalog:
        assert item["origin_code"] != item["destination_code"]
        assert item["origin_code"] in INDIAN_DOMESTIC_AIRPORTS
        assert item["destination_code"] in INDIAN_DOMESTIC_AIRPORTS


def test_export_catalog():
    rd = RouteDiscovery(source_name="yatra")
    catalog = rd.generate_full_domestic_catalog()[:5]

    with tempfile.TemporaryDirectory() as tmpdir:
        paths = rd.export_catalog(catalog, processed_dir=tmpdir)
        assert os.path.exists(paths["csv"])
        assert os.path.exists(paths["json"])
