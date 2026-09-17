"""
Data Cleaner Module.
Handles missing values, availability statuses, advance purchase calculations, and initial schema cleanup.
"""

from datetime import datetime, date
from typing import Optional, Tuple, Any

from models.fare import FareObservation
from processors.normalizer import DataNormalizer


MISSING_TEXT_VALUES = {
    "n/a", "na", "-", "—", "null", "blank", "not available",
    "sold out", "unavailable", "none", "", "undefined"
}


class DataCleaner:
    @staticmethod
    def is_missing_value(val: Any) -> bool:
        """Determines if a given value represents missing/unavailable data."""
        if val is None:
            return True
        if isinstance(val, str) and val.strip().lower() in MISSING_TEXT_VALUES:
            return True
        return False

    @staticmethod
    def calculate_advance_purchase(
        collection_date_str: str,
        travel_date_str: str
    ) -> Tuple[int, str]:
        """
        Calculates advance purchase lead time in days and categorizes into standard window.
        - T+1
        - T+7
        - T+15
        - T+30
        - T+45
        - Other
        """
        # Parse collection date (extract date portion if ISO string)
        col_date_part = collection_date_str.split("T")[0]
        c_dt = datetime.strptime(col_date_part, "%Y-%m-%d").date()
        t_dt = datetime.strptime(travel_date_str, "%Y-%m-%d").date()

        days = (t_dt - c_dt).days

        # Classify advance purchase window
        if days <= 1:
            window = "T+1"
        elif days <= 7:
            window = "T+7"
        elif days <= 15:
            window = "T+15"
        elif days <= 30:
            window = "T+30"
        elif days <= 45:
            window = "T+45"
        else:
            window = f"T+{days}"

        return days, window

    @classmethod
    def clean_observation(
        cls,
        obs: FareObservation,
        collection_date_override: Optional[str] = None
    ) -> FareObservation:
        """
        Cleans an observation in-place:
        1. Normalizes fields using DataNormalizer
        2. Calculates advance_purchase_days & advance_purchase_window
        3. Updates cleaning_status
        """
        # 1. Normalize Origin / Destination / Route
        try:
            obs.origin = DataNormalizer.normalize_iata_code(obs.origin)
            obs.destination = DataNormalizer.normalize_iata_code(obs.destination)
            obs.route = f"{obs.origin}-{obs.destination}"
        except Exception:
            obs.cleaning_status = "INVALID"

        # 2. Normalize Airline Name
        obs.airline = DataNormalizer.normalize_airline_name(obs.airline)

        # 3. Normalize Date & Times
        try:
            obs.travel_date = DataNormalizer.normalize_date(obs.travel_date)
        except Exception:
            obs.cleaning_status = "INVALID"

        if obs.departure_time and not cls.is_missing_value(obs.departure_time):
            try:
                obs.departure_time = DataNormalizer.normalize_time(obs.departure_time)
            except Exception:
                obs.departure_time = None

        if obs.arrival_time and not cls.is_missing_value(obs.arrival_time):
            try:
                obs.arrival_time = DataNormalizer.normalize_time(obs.arrival_time)
            except Exception:
                obs.arrival_time = None

        # 4. Normalize Fares (Do NOT replace missing values with zero!)
        obs.base_fare = DataNormalizer.normalize_currency_amount(obs.base_fare)
        obs.taxes = DataNormalizer.normalize_currency_amount(obs.taxes)
        obs.user_development_fee = DataNormalizer.normalize_currency_amount(obs.user_development_fee)
        obs.convenience_fee = DataNormalizer.normalize_currency_amount(obs.convenience_fee)
        obs.other_fees = DataNormalizer.normalize_currency_amount(obs.other_fees)
        obs.total_fare = DataNormalizer.normalize_currency_amount(obs.total_fare)

        # 5. Handle Advance Purchase
        col_timestamp = collection_date_override or obs.collection_timestamp
        try:
            days, window = cls.calculate_advance_purchase(col_timestamp, obs.travel_date)
            obs.advance_purchase_days = days
            obs.advance_purchase_window = window
        except Exception:
            pass

        # 6. Update Status
        if obs.cleaning_status != "INVALID":
            obs.cleaning_status = "CLEAN" if obs.total_fare is not None else "WARNING"

        return obs
