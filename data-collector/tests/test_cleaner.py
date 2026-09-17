"""
Unit tests for DataCleaner.
"""

from models.fare import FareObservation
from processors.cleaner import DataCleaner


def test_missing_value_detection():
    assert DataCleaner.is_missing_value("N/A") is True
    assert DataCleaner.is_missing_value("Sold Out") is True
    assert DataCleaner.is_missing_value("null") is True
    assert DataCleaner.is_missing_value("-") is True
    assert DataCleaner.is_missing_value(None) is True
    assert DataCleaner.is_missing_value("6546") is False


def test_advance_purchase_windows():
    col_date = "2026-09-17"

    d1, w1 = DataCleaner.calculate_advance_purchase(col_date, "2026-09-18")
    assert d1 == 1
    assert w1 == "T+1"

    d7, w7 = DataCleaner.calculate_advance_purchase(col_date, "2026-09-24")
    assert d7 == 7
    assert w7 == "T+7"

    d15, w15 = DataCleaner.calculate_advance_purchase(col_date, "2026-10-02")
    assert d15 == 15
    assert w15 == "T+15"

    d30, w30 = DataCleaner.calculate_advance_purchase(col_date, "2026-10-17")
    assert d30 == 30
    assert w30 == "T+30"

    d45, w45 = DataCleaner.calculate_advance_purchase(col_date, "2026-11-01")
    assert d45 == 45
    assert w45 == "T+45"


def test_clean_observation_preserves_null_fares():
    obs = FareObservation(
        source="indigo",
        airline="indigo",
        flight_number="6E 449",
        origin="del",
        destination="bom",
        route="DEL-BOM",
        travel_date="17th Oct",
        base_fare=None,
        taxes="N/A",
        total_fare="₹6,546"
    )

    cleaned = DataCleaner.clean_observation(obs, collection_date_override="2026-09-17")

    assert cleaned.origin == "DEL"
    assert cleaned.destination == "BOM"
    assert cleaned.airline == "IndiGo"
    assert cleaned.travel_date == "2026-10-17"
    assert cleaned.total_fare == 6546.0
    assert cleaned.base_fare is None  # CRITICAL: Must not be converted to 0
    assert cleaned.taxes is None      # CRITICAL: Must not be converted to 0
    assert cleaned.advance_purchase_days == 30
    assert cleaned.advance_purchase_window == "T+30"
