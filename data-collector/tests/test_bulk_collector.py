"""
Tests for Bulk Collector, Advance Purchase Matrix, Checkpoint/Resume, and Data Deduplication (Member 1 - SIH26056).
"""

import os
import json
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from pipelines.collect import calculate_travel_dates
from pipelines.bulk_collector import CheckpointManager, run_bulk_collection, validate_dataset_integrity
from models.fare import FareObservation, CollectionStatus
from scrapers.yatra import YatraSource
from scrapers.base import ScrapeResult


def test_calculate_travel_dates():
    base = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    windows = calculate_travel_dates(base, [1, 7, 15, 30, 45])

    assert len(windows) == 5
    assert windows[0]["window"] == "T+1"
    assert windows[0]["travel_date"] == "2026-09-02"
    assert windows[1]["window"] == "T+7"
    assert windows[1]["travel_date"] == "2026-09-08"
    assert windows[2]["window"] == "T+15"
    assert windows[2]["travel_date"] == "2026-09-16"
    assert windows[3]["window"] == "T+30"
    assert windows[3]["travel_date"] == "2026-10-01"
    assert windows[4]["window"] == "T+45"
    assert windows[4]["travel_date"] == "2026-10-16"


def test_checkpoint_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        checkpoint_file = os.path.join(tmpdir, "checkpoint.json")

        import pipelines.bulk_collector
        old_file = pipelines.bulk_collector.CHECKPOINT_FILE
        pipelines.bulk_collector.CHECKPOINT_FILE = checkpoint_file

        try:
            state = CheckpointManager.load_checkpoint()
            assert state["completed_searches"] == []

            CheckpointManager.save_checkpoint("yatra|DEL|BOM|2026-10-17|T+30")
            state_updated = CheckpointManager.load_checkpoint()
            assert "yatra|DEL|BOM|2026-10-17|T+30" in state_updated["completed_searches"]
        finally:
            pipelines.bulk_collector.CHECKPOINT_FILE = old_file


def test_bulk_collector_matrix_uniqueness():
    """
    Tests Requirement 13: Proves that bulk collector does NOT repeat DEL-BOM/T+30 with hardcoded values.
    Asserts that 3 routes x 5 windows generates 15 unique route/window search calls.
    """
    mock_catalog = [
        {"route_id": "R0001", "route": "DEL-BOM", "origin_code": "DEL", "destination_code": "BOM", "origin": "Delhi", "destination": "Mumbai"},
        {"route_id": "R0002", "route": "DEL-BLR", "origin_code": "DEL", "destination_code": "BLR", "origin": "Delhi", "destination": "Bengaluru"},
        {"route_id": "R0003", "route": "BOM-BLR", "origin_code": "BOM", "destination_code": "BLR", "origin": "Mumbai", "destination": "Bengaluru"},
    ]

    searched_keys = []

    def mock_search(origin, destination, travel_date):
        searched_keys.append(f"{origin}-{destination}|{travel_date}")
        return ScrapeResult(
            source="yatra",
            origin=origin,
            destination=destination,
            travel_date=travel_date,
            status=CollectionStatus.SUCCESS,
            observations=[
                FareObservation(
                    source="yatra",
                    airline="IndiGo",
                    flight_number="6E 101",
                    origin=origin,
                    destination=destination,
                    route=f"{origin}-{destination}",
                    travel_date=travel_date,
                    departure_time="08:00",
                    arrival_time="10:00",
                    total_fare=5000.0,
                    base_fare=4000.0,
                    taxes=1000.0,
                )
            ]
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = os.path.join(tmpdir, "route_catalog.json")
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(mock_catalog, f)

        with patch("scrapers.yatra.YatraSource.search", side_effect=mock_search), \
             patch("pipelines.bulk_collector.PRIMARY_JSON", os.path.join(tmpdir, "primary.json")), \
             patch("pipelines.bulk_collector.PRIMARY_CSV", os.path.join(tmpdir, "primary.csv")), \
             patch("pipelines.bulk_collector.CHECKPOINT_FILE", os.path.join(tmpdir, "checkpoint.json")), \
             patch("pipelines.bulk_collector.export_processed_data", return_value={"csv": "", "json": ""}):

            manifest = run_bulk_collection(
                limit_routes=3,
                limit_windows=5,
                resume=False,
                delay_seconds=0.0
            )

            assert manifest["searches_attempted"] == 15
            assert manifest["successful_searches"] == 15
            assert len(searched_keys) == 15
            # Ensure all 15 searches were unique combinations
            assert len(set(searched_keys)) == 15


def test_dataset_integrity_check():
    catalog = [{"route": "DEL-BOM"}]
    obs_valid = [
        FareObservation(
            source="yatra",
            airline="IndiGo",
            flight_number="6E 204",
            origin="DEL",
            destination="BOM",
            route="DEL-BOM",
            travel_date="2026-10-17",
            total_fare=5000.0
        )
    ]
    assert validate_dataset_integrity(obs_valid, catalog) is True

    # Invalid route not in catalog test
    obs_invalid = [
        FareObservation(
            source="yatra",
            airline="IndiGo",
            flight_number="6E 204",
            origin="DEL",
            destination="IXC",
            route="DEL-IXC",
            travel_date="2026-10-17",
            total_fare=5000.0
        )
    ]
    try:
        validate_dataset_integrity(obs_invalid, catalog)
        assert False, "Should have failed integrity check for uncataloged route"
    except ValueError:
        pass


def test_yatra_all_flight_fixture_extraction():
    adapter = YatraSource()
    mock_payload = '''
    var mainData = {
        "resultData": [
            {
                "fltSchedule": {
                    "DELBOM20261017": [
                        {
                            "ID": "F001",
                            "OD": [
                                {
                                    "ts": "0",
                                    "classtype": "Economy",
                                    "fareId": "SAVER",
                                    "FS": [
                                        {"acn": "IndiGo", "ac": "6E", "fl": "204", "dd": "06:00", "ad": "08:15"}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "fareDetails": {
                    "RK": {
                        "F001": {
                            "O": {
                                "ADT": {
                                    "bf": 4500,
                                    "tf": 5600,
                                    "UDF": 300
                                }
                            }
                        }
                    }
                }
            }
        ]
    };
    '''
    observations = adapter.parse_html(mock_payload, origin="DEL", destination="BOM", travel_date="2026-10-17")
    assert len(observations) == 1
    obs = observations[0]
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.airline == "IndiGo"
    assert obs.flight_number == "6E 204"
    assert obs.base_fare == 4500.0
    assert obs.taxes == 1100.0
    assert obs.total_fare == 5600.0


def test_blocked_source_handling():
    adapter = YatraSource()
    blocked_html = "<html><head><title>Access Denied</title></head><body>Cloudflare / Access Denied block</body></html>"
    observations = adapter.parse_html(blocked_html, origin="DEL", destination="BOM", travel_date="2026-10-17")
    assert len(observations) == 0


def test_no_results_handling():
    adapter = YatraSource()
    empty_html = "<html><body><h1>Search Results</h1><p>No flights found for selected route</p></body></html>"
    observations = adapter.parse_html(empty_html, origin="DEL", destination="BOM", travel_date="2026-10-17")
    assert len(observations) == 0
