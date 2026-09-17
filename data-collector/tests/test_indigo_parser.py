"""
Unit tests for IndigoSource HTML parser using static HTML DOM fixtures.
Ensures zero live website dependency during unit testing.
"""

from scrapers.indigo import IndigoSource


SAMPLE_INDIGO_DOM = """
<div class="flight-list-container">
    <div class="flight-card">
        <div class="flight-info">
            <span class="flight-number">6E 449</span>
            <span class="departure">05:00 DEL, T1</span>
            <span class="duration">02h 15m Non-stop</span>
            <span class="arrival">07:15 BOM, T2</span>
        </div>
        <div class="fare-options">
            <div class="fare-tile">
                <span class="fare-type">Saver fare</span>
                <span class="price">₹6,546</span>
            </div>
            <div class="fare-tile">
                <span class="fare-type">Flexi Plus</span>
                <span class="price">₹7,019</span>
            </div>
            <div class="fare-tile">
                <span class="fare-type">Stretch | Business</span>
                <span class="price">₹21,900</span>
            </div>
        </div>
    </div>
    <div class="flight-card">
        <div class="flight-info">
            <span class="flight-number">6E 5198</span>
            <span class="departure">15:00 DXN</span>
            <span class="duration">02h 10m Non-stop</span>
            <span class="arrival">17:10 BOM, T1</span>
        </div>
        <div class="fare-options">
            <div class="fare-tile">
                <span class="fare-type">Saver fare</span>
                <span class="price">₹6,447</span>
            </div>
        </div>
    </div>
    <div class="flight-card">
        <div class="flight-info">
            <span class="flight-number">6E 999</span>
            <span class="departure">23:00 DEL</span>
            <span class="duration">Non-stop</span>
            <span class="arrival">01:15 BOM</span>
        </div>
        <div class="fare-options">
            <span class="status">Sold Out</span>
        </div>
    </div>
</div>
"""


def test_parse_indigo_dom_fixture():
    observations = IndigoSource.parse_html_payload(
        html_content=SAMPLE_INDIGO_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )

    assert len(observations) > 0

    # Verify first flight (6E 449)
    flight_449_obs = [o for o in observations if o.flight_number == "6E 449"]
    assert len(flight_449_obs) == 3
    assert flight_449_obs[0].departure_time == "05:00"
    assert flight_449_obs[0].arrival_time == "07:15"
    assert flight_449_obs[0].stops == 0
    assert flight_449_obs[0].total_fare == 6546.0
    assert flight_449_obs[0].fare_class == "Saver"

    # Verify business cabin flight tier
    biz_obs = [o for o in flight_449_obs if o.cabin_class == "Stretch | Business"][0]
    assert biz_obs.total_fare == 21900.0

    # Verify sold out flight (6E 999)
    sold_out_obs = [o for o in observations if o.flight_number == "6E 999"][0]
    assert sold_out_obs.total_fare is None
    assert sold_out_obs.availability_status == "sold_out"
