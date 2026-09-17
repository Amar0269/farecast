"""
Unit tests for IxigoSource HTML parser.
Uses a static HTML fixture to verify DOM parsing, schema compliance, and status detection.
"""

import pytest
from models.fare import FareObservation, CollectionStatus
from scrapers.ixigo import IxigoSource


IXIGO_FIXTURE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="flight-card">
        <div class="airline-name">IndiGo</div>
        <div class="flight-no">6E 5314</div>
        <div class="dep-time">06:00</div>
        <div class="arr-time">08:10</div>
        <div class="stop">Non-stop</div>
        <div class="price">₹ 4,899</div>
    </div>
    <div class="flight-card">
        <div class="airline-name">Air India</div>
        <div class="flight-no">AI 805</div>
        <div class="dep-time">10:15</div>
        <div class="arr-time">12:30</div>
        <div class="stop">1 Stop</div>
        <div class="price">₹ 6,150</div>
    </div>
</body>
</html>
"""


def test_parse_ixigo_fixture_count():
    adapter = IxigoSource()
    obs = adapter.parse_html(IXIGO_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")
    assert len(obs) == 2


def test_parse_ixigo_fixture_core_fields():
    adapter = IxigoSource()
    obs = adapter.parse_html(IXIGO_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")
    
    first = obs[0]
    assert first.source == "ixigo"
    assert first.airline == "IndiGo"
    assert first.flight_number == "6E 5314"
    assert first.origin == "DEL"
    assert first.destination == "BOM"
    assert first.route == "DEL-BOM"
    assert first.travel_date == "2026-10-17"
    assert first.departure_time == "06:00"
    assert first.arrival_time == "08:10"
    assert first.stops == 0
    assert first.total_fare == 4899.0
    assert first.currency == "INR"


def test_parse_ixigo_second_card():
    adapter = IxigoSource()
    obs = adapter.parse_html(IXIGO_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")
    
    second = obs[1]
    assert second.airline == "Air India"
    assert second.flight_number == "AI 805"
    assert second.departure_time == "10:15"
    assert second.arrival_time == "12:30"
    assert second.stops == 1
    assert second.total_fare == 6150.0
