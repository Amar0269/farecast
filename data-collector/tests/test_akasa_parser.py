"""
Unit tests for Akasa Air source parser.
"""

from scrapers.akasa import AkasaSource
from models.fare import CollectionStatus


def test_akasa_parse_valid_html():
    html_content = """
    <div class="flight-card">
        <span class="fl-no">QP 1102</span>
        <span class="dep-time">14:15</span>
        <span class="arr-time">16:30</span>
        <span class="fare">5,120</span>
        <span class="stop">Non-stop</span>
    </div>
    """
    scraper = AkasaSource()
    observations = scraper.parse_html(html_content, "DEL", "BOM", "2026-10-17")

    assert len(observations) == 1
    obs = observations[0]
    assert obs.airline == "Akasa Air"
    assert obs.flight_number == "QP 1102"
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.total_fare == 5120.0
    assert obs.departure_time == "14:15"
    assert obs.arrival_time == "16:30"
    assert obs.stops == 0


def test_akasa_search_blocked_response():
    scraper = AkasaSource()
    result = scraper.search("DEL", "BOM", "2026-10-17")
    assert result.status == CollectionStatus.SOURCE_BLOCKED
    assert result.error_message is not None
