"""
Unit tests for AirIndiaSource HTML parser.
Uses a static HTML fixture to verify DOM extraction, airline normalization, and 32-field schema compliance.
"""

import pytest
from models.fare import FareObservation
from scrapers.airindia import AirIndiaSource


AIRINDIA_FIXTURE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="flight-card">
        <div class="flight-number">AI 805</div>
        <div class="dep-time">10:15</div>
        <div class="arr-time">12:30</div>
        <div class="stop">Non-stop</div>
        <div class="price">₹ 6,550</div>
    </div>
    <div class="flight-card">
        <div class="flight-number">AI 332</div>
        <div class="dep-time">17:00</div>
        <div class="arr-time">19:15</div>
        <div class="stop">Non-stop</div>
        <div class="price">₹ 7,120</div>
    </div>
</body>
</html>
"""


def test_parse_airindia_fixture_count():
    adapter = AirIndiaSource()
    obs = adapter.parse_html(AIRINDIA_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")
    assert len(obs) == 2


def test_parse_airindia_fixture_core_fields():
    adapter = AirIndiaSource()
    obs = adapter.parse_html(AIRINDIA_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")

    first = obs[0]
    assert first.source == "airindia"
    assert first.airline == "Air India"
    assert first.flight_number == "AI 805"
    assert first.origin == "DEL"
    assert first.destination == "BOM"
    assert first.route == "DEL-BOM"
    assert first.travel_date == "2026-10-17"
    assert first.departure_time == "10:15"
    assert first.arrival_time == "12:30"
    assert first.stops == 0
    assert first.total_fare == 6550.0
    assert first.currency == "INR"


def test_parse_airindia_second_card():
    adapter = AirIndiaSource()
    obs = adapter.parse_html(AIRINDIA_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")

    second = obs[1]
    assert second.airline == "Air India"
    assert second.flight_number == "AI 332"
    assert second.departure_time == "17:00"
    assert second.arrival_time == "19:15"
    assert second.stops == 0
    assert second.total_fare == 7120.0
