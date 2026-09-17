"""
Unit tests for Air India Express source parser.
"""

from scrapers.airindiaexpress import AirIndiaExpressSource
from models.fare import CollectionStatus


def test_airindiaexpress_parse_valid_html():
    html_content = """
    <div class="flight-card">
        <span class="fl-no">IX 123</span>
        <span class="dep-time">08:30</span>
        <span class="arr-time">10:45</span>
        <span class="price">₹ 4,800</span>
        <span class="stop">Non stop</span>
    </div>
    """
    scraper = AirIndiaExpressSource()
    observations = scraper.parse_html(html_content, "DEL", "BOM", "2026-10-17")

    assert len(observations) == 1
    obs = observations[0]
    assert obs.airline == "Air India Express"
    assert obs.flight_number == "IX 123"
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.total_fare == 4800.0
    assert obs.departure_time == "08:30"
    assert obs.arrival_time == "10:45"
    assert obs.stops == 0


def test_airindiaexpress_search_blocked_response():
    scraper = AirIndiaExpressSource()
    result = scraper.search("DEL", "BOM", "2026-10-17")
    assert result.status == CollectionStatus.SOURCE_BLOCKED
    assert "Akamai" in result.error_message or "blocked" in result.error_message.lower()
