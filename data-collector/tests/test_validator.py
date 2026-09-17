"""
Unit tests for DataValidator (Deduplication and Outlier Flagging).
"""

from models.fare import FareObservation
from processors.validator import DataValidator


def test_deduplication_within_source():
    obs1 = FareObservation(
        source="indigo",
        airline="IndiGo",
        flight_number="6E 449",
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date="2026-10-17",
        departure_time="05:00",
        fare_class="Saver",
        total_fare=6546.0
    )
    # Duplicate from same source
    obs2 = FareObservation(
        source="indigo",
        airline="IndiGo",
        flight_number="6E 449",
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date="2026-10-17",
        departure_time="05:00",
        fare_class="Saver",
        total_fare=6546.0
    )
    # Different source (e.g. OTA) - should NOT be flagged as duplicate observation
    obs3 = FareObservation(
        source="makemytrip",
        airline="IndiGo",
        flight_number="6E 449",
        origin="DEL",
        destination="BOM",
        route="DEL-BOM",
        travel_date="2026-10-17",
        departure_time="05:00",
        fare_class="Saver",
        total_fare=6546.0
    )

    results = DataValidator.deduplicate([obs1, obs2, obs3])

    assert results[0].duplicate_flag is False
    assert results[1].duplicate_flag is True  # Duplicate from 'indigo'
    assert results[2].duplicate_flag is False # Different source 'makemytrip'


def test_outlier_flagging():
    # Group of normal fares around 5,000 to 7,000 INR
    fares = [5000.0, 5200.0, 5500.0, 5800.0, 6000.0, 6200.0, 6500.0, 25000.0]  # 25,000 is an outlier
    obs_list = [
        FareObservation(
            source="indigo",
            airline="IndiGo",
            flight_number=f"6E {100+i}",
            origin="DEL",
            destination="BOM",
            route="DEL-BOM",
            travel_date="2026-10-17",
            total_fare=f
        )
        for i, f in enumerate(fares)
    ]

    flagged = DataValidator.flag_outliers(obs_list)

    # Normal fares should not be outliers
    for obs in flagged[:-1]:
        assert obs.outlier_flag is False

    # Extreme fare of 25,000 should be flagged
    assert flagged[-1].outlier_flag is True
