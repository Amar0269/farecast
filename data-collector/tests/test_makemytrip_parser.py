"""
Unit tests for MakeMyTrip source parser.
"""

from scrapers.makemytrip import MakeMyTripSource
from models.fare import CollectionStatus


def test_makemytrip_parse_valid_html():
    html_content = """
    <div class="listingcard">
        <span class="fl-no">AI 805</span>
        <span class="dep-time">17:00</span>
        <span class="arr-time">19:15</span>
        <span class="fare">₹ 5,890</span>
        <span class="stop">Non-stop</span>
    </div>
    """
    scraper = MakeMyTripSource()
    observations = scraper.parse_html(html_content, "DEL", "BOM", "2026-10-17")

    assert len(observations) == 1
    obs = observations[0]
    assert obs.airline == "Air India"
    assert obs.flight_number == "AI 805"
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.total_fare == 5890.0
    assert obs.departure_time == "17:00"
    assert obs.arrival_time == "19:15"
    assert obs.stops == 0


def test_makemytrip_search_blocked_response():
    scraper = MakeMyTripSource()
    result = scraper.search("DEL", "BOM", "2026-10-17")
    assert result.status == CollectionStatus.SOURCE_BLOCKED
    assert "Akamai" in result.error_message or "blocked" in result.error_message.lower() or "timeout" in result.error_message.lower()
