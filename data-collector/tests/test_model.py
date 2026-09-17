"""
Unit tests for FareObservation Pydantic model.
"""

import pytest
from pydantic import ValidationError
from models.fare import FareObservation


def test_valid_fare_observation():
    obs = FareObservation(
        source="indigo",
        airline="IndiGo",
        flight_number="6E 449",
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date="2026-10-17",
        departure_time="05:00",
        arrival_time="07:15",
        cabin_class="Economy",
        fare_class="Saver",
        total_fare=6546.0,
        currency="INR"
    )
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.route == "DEL-BOM"
    assert obs.total_fare == 6546.0
    assert "base_fare" in obs.missing_fields
    assert "user_development_fee" in obs.missing_fields


def test_invalid_iata_rejection():
    with pytest.raises(ValidationError):
        FareObservation(
            source="indigo",
            airline="IndiGo",
            flight_number="6E 449",
            origin="DELHI",  # Invalid IATA (must be 3 chars)
            destination="BOM",
            route="DELHI-BOM",
            travel_date="2026-10-17"
        )


def test_route_auto_generation():
    obs = FareObservation(
        source="indigo",
        airline="IndiGo",
        flight_number="6E 449",
        origin="del",
        destination="bom",
        route="INVALID-ROUTE",
        travel_date="2026-10-17"
    )
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.route == "DEL-BOM"


def test_csv_32_field_dict_export():
    obs = FareObservation(
        source="indigo",
        airline="IndiGo",
        flight_number="6E 449",
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date="2026-10-17",
        total_fare=6546.0
    )
    d = obs.to_csv_dict()
    assert len(d.keys()) == 32
    assert d["source"] == "indigo"
    assert d["airline"] == "IndiGo"
    assert d["route"] == "DEL-BOM"
    assert isinstance(d["missing_fields"], str)
