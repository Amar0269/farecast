"""
Tests for Bulk Collector, Advance Purchase Matrix, Checkpoint/Resume, and Data Deduplication (Member 1 - SIH26056).
"""

import os
import json
import tempfile
from datetime import datetime, timezone
from pipelines.collect import calculate_travel_dates
from pipelines.bulk_collector import CheckpointManager
from models.fare import FareObservation, CollectionStatus
from scrapers.yatra import YatraSource


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

            CheckpointManager.save_checkpoint("yatra|DEL|BOM|2026-10-17")
            state_updated = CheckpointManager.load_checkpoint()
            assert "yatra|DEL|BOM|2026-10-17" in state_updated["completed_searches"]
        finally:
            pipelines.bulk_collector.CHECKPOINT_FILE = old_file


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
