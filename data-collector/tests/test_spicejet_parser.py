"""
Unit tests for SpiceJet source parser.
"""

from scrapers.spicejet import SpiceJetSource
from models.fare import CollectionStatus


def test_spicejet_parse_valid_html():
    html_content = """
    <table>
        <tr class="flight-row">
            <span class="fl-no">SG 8169</span>
            <span class="dep-time">06:00</span>
            <span class="arr-time">08:15</span>
            <span class="price">4,950</span>
            <span class="stop">Non-stop</span>
        </tr>
    </table>
    """
    scraper = SpiceJetSource()
    observations = scraper.parse_html(html_content, "DEL", "BOM", "2026-10-17")

    assert len(observations) == 1
    obs = observations[0]
    assert obs.airline == "SpiceJet"
    assert obs.flight_number == "SG 8169"
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.total_fare == 4950.0
    assert obs.departure_time == "06:00"
    assert obs.arrival_time == "08:15"
    assert obs.stops == 0


def test_spicejet_search_blocked_response():
    scraper = SpiceJetSource()
    result = scraper.search("DEL", "BOM", "2026-10-17")
    assert result.status == CollectionStatus.SOURCE_BLOCKED
    assert "Cloudflare" in result.error_message or "JS" in result.error_message or "blocked" in result.error_message.lower()
