"""
Unit tests for Goibibo source parser.
"""

from scrapers.goibibo import GoibiboSource
from models.fare import CollectionStatus


def test_goibibo_parse_valid_html():
    html_content = """
    <div class="srp-card">
        <span class="fl-no">6E 5321</span>
        <span class="dep-time">09:15</span>
        <span class="arr-time">11:30</span>
        <span class="price">₹ 5,350</span>
        <span class="stop">Non stop</span>
    </div>
    """
    scraper = GoibiboSource()
    observations = scraper.parse_html(html_content, "DEL", "BOM", "2026-10-17")

    assert len(observations) == 1
    obs = observations[0]
    assert obs.airline == "IndiGo"
    assert obs.flight_number == "6E 5321"
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.total_fare == 5350.0
    assert obs.departure_time == "09:15"
    assert obs.arrival_time == "11:30"
    assert obs.stops == 0


def test_goibibo_search_blocked_response():
    scraper = GoibiboSource()
    result = scraper.search("DEL", "BOM", "2026-10-17")
    assert result.status == CollectionStatus.SOURCE_BLOCKED
    assert "Akamai" in result.error_message or "blocked" in result.error_message.lower()
