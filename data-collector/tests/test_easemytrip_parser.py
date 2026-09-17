"""
Unit tests for EaseMyTripSource HTML parser.
Uses a static HTML fixture that mirrors the real EaseMyTrip DOM structure
(confirmed from live DOM analysis on 2026-09-17, DEL->BOM route).

Zero live website dependency — all tests run offline.
"""

import pytest
from models.fare import FareObservation
from processors.cleaner import DataCleaner
from processors.validator import DataValidator
from scrapers.easemytrip import (
    EaseMyTripSource,
    _normalize_flight_number,
    _parse_time,
    _parse_stops,
    _parse_seats,
)


# ---------------------------------------------------------------------------
# Static HTML fixture mirroring confirmed EaseMyTrip DOM structure
# ---------------------------------------------------------------------------
SAMPLE_EASEMYTRIP_DOM = """
<div id="divResultSet">

  <!-- Card 1: IndiGo nonstop, 6 seats left -->
  <div class="top-bottom-single-row">
    <div class="airlines-logo">
      <img src="indigo.png" />
      <span class="txt-r-l">IndiGo</span>
      <span class="txt-r-2">6E- 324</span>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">13:00</div>
      <div class="txt-r-4">New Delhi(DEL)</div>
    </div>
    <div class="stop-info">
      <div class="stop-t-n">02h 10m</div>
      <div class="stop-t-n2">Nonstop</div>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">15:10</div>
      <div class="txt-r-4">Mumbai(BOM)</div>
    </div>
    <div class="fare-sec">
      <div class="txt-r-3">Rs.6,198</div>
    </div>
    <div class="st-av">6 Seats Left</div>
  </div>

  <!-- Card 2: IndiGo nonstop, no seat count -->
  <div class="top-bottom-single-row">
    <div class="airlines-logo">
      <img src="indigo.png" />
      <span class="txt-r-l">IndiGo</span>
      <span class="txt-r-2">6E-6318</span>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">14:45</div>
      <div class="txt-r-4">New Delhi(DEL)</div>
    </div>
    <div class="stop-info">
      <div class="stop-t-n">02h 15m</div>
      <div class="stop-t-n2">Nonstop</div>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">17:00</div>
      <div class="txt-r-4">Mumbai(BOM)</div>
    </div>
    <div class="fare-sec">
      <div class="txt-r-3">Rs.6,198</div>
    </div>
  </div>

  <!-- Card 3: Air India nonstop -->
  <div class="top-bottom-single-row">
    <div class="airlines-logo">
      <img src="airindia.png" />
      <span class="txt-r-l">Air India</span>
      <span class="txt-r-2">AI-101</span>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">06:00</div>
      <div class="txt-r-4">New Delhi(DEL)</div>
    </div>
    <div class="stop-info">
      <div class="stop-t-n">02h 05m</div>
      <div class="stop-t-n2">Nonstop</div>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">08:05</div>
      <div class="txt-r-4">Mumbai(BOM)</div>
    </div>
    <div class="fare-sec">
      <div class="txt-r-3">Rs.7,450</div>
    </div>
    <div class="st-av">3 Seats Left</div>
  </div>

  <!-- Card 4: Akasa Air nonstop -->
  <div class="top-bottom-single-row">
    <div class="airlines-logo">
      <img src="akasa.png" />
      <span class="txt-r-l">AkasaAir</span>
      <span class="txt-r-2">QP-1368</span>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">08:30</div>
      <div class="txt-r-4">New Delhi(DEL)</div>
    </div>
    <div class="stop-info">
      <div class="stop-t-n">02h 20m</div>
      <div class="stop-t-n2">Nonstop</div>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">10:50</div>
      <div class="txt-r-4">Mumbai(BOM)</div>
    </div>
    <div class="fare-sec">
      <div class="txt-r-3">Rs.5,899</div>
    </div>
  </div>

  <!-- Card 5: SpiceJet 1-stop -->
  <div class="top-bottom-single-row">
    <div class="airlines-logo">
      <img src="spicejet.png" />
      <span class="txt-r-l">SpiceJet</span>
      <span class="txt-r-2">SG-8169</span>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">07:15</div>
      <div class="txt-r-4">New Delhi(DEL)</div>
    </div>
    <div class="stop-info">
      <div class="stop-t-n">04h 10m</div>
      <div class="stop-t-n2">1 Stop</div>
    </div>
    <div class="flight-time-sec">
      <div class="txt-r-3">11:25</div>
      <div class="txt-r-4">Mumbai(BOM)</div>
    </div>
    <div class="fare-sec">
      <div class="txt-r-3">Rs.4,299</div>
    </div>
  </div>

</div>
"""


# ---------------------------------------------------------------------------
# Fixture-level tests
# ---------------------------------------------------------------------------

def test_parse_easemytrip_fixture_count():
    """Should parse all 5 flight cards from the fixture."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    assert len(obs) == 5, f"Expected 5 observations, got {len(obs)}"


def test_parse_easemytrip_fixture_core_fields():
    """Core identity fields must be populated for all cards."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    for o in obs:
        assert o.source == "easemytrip"
        assert o.origin == "DEL"
        assert o.destination == "BOM"
        assert o.route == "DEL-BOM"
        assert o.travel_date == "2026-10-17"
        assert o.currency == "INR"


# ---------------------------------------------------------------------------
# Airline extraction tests
# ---------------------------------------------------------------------------

def test_indigo_airline_extraction():
    """IndiGo cards must have airline='IndiGo' and correct 6E prefix."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    indigo_obs = [o for o in obs if o.airline == "IndiGo"]
    assert len(indigo_obs) == 2
    flight_numbers = {o.flight_number for o in indigo_obs}
    assert "6E 324" in flight_numbers
    assert "6E 6318" in flight_numbers


def test_air_india_airline_extraction():
    """Air India card must normalize airline to 'Air India'."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    ai_obs = [o for o in obs if o.airline == "Air India"]
    assert len(ai_obs) == 1
    assert ai_obs[0].flight_number == "AI 101"


def test_akasa_airline_extraction():
    """AkasaAir card must normalize airline to 'Akasa Air'."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    akasa_obs = [o for o in obs if o.airline == "Akasa Air"]
    assert len(akasa_obs) == 1
    assert akasa_obs[0].flight_number == "QP 1368"


# ---------------------------------------------------------------------------
# Stops parsing tests
# ---------------------------------------------------------------------------

def test_nonstop_stops_parsing():
    """'Nonstop' label must yield stops=0."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    indigo_obs = [o for o in obs if o.airline == "IndiGo"]
    for o in indigo_obs:
        assert o.stops == 0, f"Expected 0 stops for IndiGo, got {o.stops}"


def test_one_stop_parsing():
    """'1 Stop' label must yield stops=1."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    spicejet_obs = [o for o in obs if o.airline == "SpiceJet"]
    assert len(spicejet_obs) == 1
    assert spicejet_obs[0].stops == 1


# ---------------------------------------------------------------------------
# Fare parsing tests
# ---------------------------------------------------------------------------

def test_fare_parsing_inr():
    """Rs.6,198 must parse to float 6198.0, currency must be INR."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    indigo_6e324 = next((o for o in obs if o.flight_number == "6E 324"), None)
    assert indigo_6e324 is not None
    assert indigo_6e324.total_fare == 6198.0
    assert indigo_6e324.currency == "INR"


def test_fare_parsing_all_cards():
    """Every card with a Rs. fare must parse to a positive float."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    expected_fares = {
        "6E 324": 6198.0,
        "6E 6318": 6198.0,
        "AI 101": 7450.0,
        "QP 1368": 5899.0,
        "SG 8169": 4299.0,
    }
    for o in obs:
        if o.flight_number in expected_fares:
            assert o.total_fare == expected_fares[o.flight_number], (
                f"Fare mismatch for {o.flight_number}: "
                f"expected {expected_fares[o.flight_number]}, got {o.total_fare}"
            )


# ---------------------------------------------------------------------------
# Departure / arrival time tests
# ---------------------------------------------------------------------------

def test_departure_arrival_times():
    """Departure and arrival times must parse correctly for 6E 324."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    card = next((o for o in obs if o.flight_number == "6E 324"), None)
    assert card is not None
    assert card.departure_time == "13:00"
    assert card.arrival_time == "15:10"


# ---------------------------------------------------------------------------
# Seats available test
# ---------------------------------------------------------------------------

def test_seats_available_extraction():
    """'6 Seats Left' must yield seats_available=6; missing must yield None."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    six_seat_card = next((o for o in obs if o.flight_number == "6E 324"), None)
    assert six_seat_card is not None
    assert six_seat_card.seats_available == 6

    three_seat_card = next((o for o in obs if o.flight_number == "AI 101"), None)
    assert three_seat_card is not None
    assert three_seat_card.seats_available == 3

    no_seat_card = next((o for o in obs if o.flight_number == "6E 6318"), None)
    assert no_seat_card is not None
    assert no_seat_card.seats_available is None


# ---------------------------------------------------------------------------
# Missing fields tracking (schema integrity)
# ---------------------------------------------------------------------------

def test_missing_fields_tracking():
    """
    Fields unavailable on EaseMyTrip listing page must appear in missing_fields.
    CRITICAL: Must NOT be 0.0 — must remain None (null).
    """
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    for o in obs:
        assert o.base_fare is None,            "base_fare must be None (not 0)"
        assert o.taxes is None,                "taxes must be None (not 0)"
        assert o.user_development_fee is None, "UDF must be None (not 0)"
        assert o.convenience_fee is None,      "convenience_fee must be None (not 0)"
        assert o.other_fees is None,           "other_fees must be None (not 0)"
        assert o.fare_class is None,           "fare_class not exposed on listing"
        assert o.fare_type is None,            "fare_type not exposed on listing"

        # Confirm these appear in missing_fields list
        assert "base_fare" in o.missing_fields
        assert "taxes" in o.missing_fields
        assert "user_development_fee" in o.missing_fields


# ---------------------------------------------------------------------------
# Cabin class test
# ---------------------------------------------------------------------------

def test_cabin_class_economy_default():
    """Default cabin (class code 0) must yield 'Economy'."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17",
        cabin_class_code=0
    )
    for o in obs:
        assert o.cabin_class == "Economy"


def test_cabin_class_business():
    """Cabin code 2 must yield 'Business'."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17",
        cabin_class_code=2
    )
    for o in obs:
        assert o.cabin_class == "Business"


# ---------------------------------------------------------------------------
# Advance purchase calculation test
# ---------------------------------------------------------------------------

def test_advance_purchase_calculation():
    """
    Advance purchase days and window must be computed correctly by DataCleaner.
    Collection on 2026-09-17, travel on 2026-10-17 = 30 days → T+30.
    """
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    assert len(obs) > 0
    cleaned = DataCleaner.clean_observation(obs[0], collection_date_override="2026-09-17")
    assert cleaned.advance_purchase_days == 30
    assert cleaned.advance_purchase_window == "T+30"


# ---------------------------------------------------------------------------
# Deduplication test
# ---------------------------------------------------------------------------

def test_duplicate_detection_easemytrip():
    """
    Identical flight+fare from same source must be flagged as duplicate.
    Same flight from a different source must NOT be flagged.
    """
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    assert len(obs) > 0

    # Duplicate from same source
    dup = FareObservation(
        source="easemytrip",
        airline=obs[0].airline,
        flight_number=obs[0].flight_number,
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date="2026-10-17",
        departure_time=obs[0].departure_time,
        fare_class=None,
        total_fare=obs[0].total_fare
    )

    # Different source — same flight
    other_source = FareObservation(
        source="makemytrip",
        airline=obs[0].airline,
        flight_number=obs[0].flight_number,
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date="2026-10-17",
        departure_time=obs[0].departure_time,
        fare_class=None,
        total_fare=obs[0].total_fare
    )

    combined = obs + [dup, other_source]
    result = DataValidator.deduplicate(combined)

    # Original observations must not be duplicates
    for o in result[:len(obs)]:
        assert o.duplicate_flag is False

    # The explicit duplicate must be flagged
    assert result[len(obs)].duplicate_flag is True

    # Different source must not be flagged
    assert result[len(obs) + 1].duplicate_flag is False


# ---------------------------------------------------------------------------
# Schema validation — 32-field CSV export
# ---------------------------------------------------------------------------

def test_schema_validation_32_fields():
    """to_csv_dict() must return exactly 32 fields for every EaseMyTrip observation."""
    obs = EaseMyTripSource.parse_html_payload(
        html_content=SAMPLE_EASEMYTRIP_DOM,
        origin="DEL",
        destination="BOM",
        travel_date="2026-10-17"
    )
    assert len(obs) > 0
    for o in obs:
        d = o.to_csv_dict()
        assert len(d) == 32, f"Expected 32 fields, got {len(d)} for {o.flight_number}"


# ---------------------------------------------------------------------------
# Unit tests for private helper functions
# ---------------------------------------------------------------------------

def test_normalize_flight_number_formats():
    """Flight number normalizer handles all EaseMyTrip formats."""
    assert _normalize_flight_number("6E- 324") == "6E 324"
    assert _normalize_flight_number("6E-324") == "6E 324"
    assert _normalize_flight_number("6E-6318") == "6E 6318"
    assert _normalize_flight_number("AI-101") == "AI 101"
    assert _normalize_flight_number("QP-1368") == "QP 1368"
    assert _normalize_flight_number("SG-8169") == "SG 8169"
    assert _normalize_flight_number("AI 101") == "AI 101"   # already correct


def test_parse_time_formats():
    """Time parser handles HH:MM and inline city text."""
    assert _parse_time("13:00") == "13:00"
    assert _parse_time("06:05") == "06:05"
    assert _parse_time("13:00 New Delhi(DEL)") == "13:00"
    assert _parse_time("") is None
    assert _parse_time(None) is None


def test_parse_stops_labels():
    """Stops parser converts all label variants correctly."""
    assert _parse_stops("nonstop") == 0
    assert _parse_stops("Nonstop") == 0
    assert _parse_stops("non-stop") == 0
    assert _parse_stops("1 Stop") == 1
    assert _parse_stops("1stop") == 1
    assert _parse_stops("2 Stops") == 2
    assert _parse_stops("") == 0


def test_parse_seats_labels():
    """Seats parser extracts integer or returns None."""
    assert _parse_seats("6 Seats Left") == 6
    assert _parse_seats("3 seats left") == 3
    assert _parse_seats("1 Seat Left") == 1
    assert _parse_seats("") is None
    assert _parse_seats(None) is None
