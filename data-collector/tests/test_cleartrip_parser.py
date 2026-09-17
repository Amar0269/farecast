"""
Unit tests for Cleartrip source parser.
"""

import json
from scrapers.cleartrip import CleartripSource
from models.fare import CollectionStatus


def test_cleartrip_parse_next_data():
    payload = {
        "props": {
            "pageProps": {
                "initialState": {
                    "results": {
                        "data": {
                            "tuples": [
                                {
                                    "airlineName": "IndiGo",
                                    "flightNumber": "6E-5321",
                                    "depTime": "09:00",
                                    "arrTime": "11:15",
                                    "fare": 5200.0,
                                    "stops": 0
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    html_content = f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></html>'
    scraper = CleartripSource()
    observations = scraper.parse_html(html_content, "DEL", "BOM", "2026-10-17")

    assert len(observations) == 1
    obs = observations[0]
    assert obs.airline == "IndiGo"
    assert obs.flight_number == "6E 5321"
    assert obs.total_fare == 5200.0
    assert obs.departure_time == "09:00"
    assert obs.arrival_time == "11:15"


def test_cleartrip_search_blocked_response():
    scraper = CleartripSource()
    result = scraper.search("DEL", "BOM", "2026-10-17")
    assert result.status == CollectionStatus.SOURCE_BLOCKED
    assert "Akamai" in result.error_message or "hydration" in result.error_message or "blocked" in result.error_message.lower()
