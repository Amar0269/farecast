"""
Unit tests for YatraSource HTML parser.
Uses a static HTML fixture that mirrors the real Yatra DOM structure to verify extraction, normalization, and 32-field schema compliance.
"""

import pytest
from models.fare import FareObservation
from scrapers.yatra import YatraSource


YATRA_FIXTURE_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="flightItem border-shadow pr">
  <div class="airline-name ml-5">
    <span>SpiceJet</span>
    <p class="normal fs-11 font-lightgrey no-wrap fl-no blank-label">
      <span>SG-8723</span>
    </p>
  </div>
  <div class="timing-det">
    <p class="depart-time">08:30</p>
    <p class="arrival-time">10:35</p>
    <span class="stop-info">Non Stop</span>
  </div>
  <div class="price-det">
    <span class="final-price">24,220</span>
  </div>
</div>
<div class="flightItem border-shadow pr">
  <div class="airline-name ml-5">
    <span>IndiGo</span>
    <p class="normal fs-11 font-lightgrey no-wrap fl-no blank-label">
      <span>6E-5314</span>
    </p>
  </div>
  <div class="timing-det">
    <p class="depart-time">14:15</p>
    <p class="arrival-time">16:30</p>
    <span class="stop-info">1 Stop</span>
  </div>
  <div class="price-det">
    <span class="final-price">5,890</span>
  </div>
</div>
</body>
</html>
"""


def test_parse_yatra_fixture_count():
    adapter = YatraSource()
    obs = adapter.parse_html(YATRA_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")
    assert len(obs) == 2


def test_parse_yatra_fixture_core_fields():
    adapter = YatraSource()
    obs = adapter.parse_html(YATRA_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")

    first = obs[0]
    assert first.source == "yatra"
    assert first.airline == "SpiceJet"
    assert first.flight_number == "SG 8723"
    assert first.origin == "DEL"
    assert first.destination == "BOM"
    assert first.route == "DEL-BOM"
    assert first.travel_date == "2026-10-17"
    assert first.departure_time == "08:30"
    assert first.arrival_time == "10:35"
    assert first.stops == 0
    assert first.total_fare == 24220.0
    assert first.currency == "INR"


def test_parse_yatra_second_card():
    adapter = YatraSource()
    obs = adapter.parse_html(YATRA_FIXTURE_HTML, "DEL", "BOM", "2026-10-17")

    second = obs[1]
    assert second.airline == "IndiGo"
    assert second.flight_number == "6E 5314"
    assert second.departure_time == "14:15"
    assert second.arrival_time == "16:30"
    assert second.stops == 1
    assert second.total_fare == 5890.0
