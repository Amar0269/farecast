"""
Data Normalizer Module.
Standardizes currency values, dates, times, airline names, and IATA airport codes.
"""

import re
from datetime import datetime
from typing import Optional, Any


class DataNormalizer:
    @staticmethod
    def normalize_currency_amount(val: Any) -> Optional[float]:
        """
        Normalizes fare strings like '₹6,546', 'Rs 4,299', '4,299 INR' into numeric floats.
        Returns None if value is missing or invalid.
        """
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val) if val >= 0 else None

        val_str = str(val).strip()
        if not val_str or val_str.lower() in ("n/a", "na", "-", "—", "null", "blank", "not available", "sold out", "unavailable"):
            return None

        # Remove currency symbols, letters, commas, whitespace
        cleaned = re.sub(r"[^\d.]", "", val_str)
        if not cleaned:
            return None

        try:
            amount = float(cleaned)
            return amount if amount >= 0 else None
        except ValueError:
            return None

    @staticmethod
    def normalize_airline_name(raw_name: str) -> str:
        """Standardizes airline names to official canonical representations."""
        if not raw_name:
            return "Unknown Airline"

        cleaned = str(raw_name).strip()
        lower_name = cleaned.lower()

        if "indigo" in lower_name or "6e" in lower_name:
            return "IndiGo"
        elif "air india express" in lower_name or "ix" in lower_name:
            return "Air India Express"
        elif "air india" in lower_name or lower_name == "ai":
            return "Air India"
        elif "akasa" in lower_name or "akasaair" in lower_name or lower_name == "qp":
            return "Akasa Air"
        elif "spicejet" in lower_name or lower_name == "sg":
            return "SpiceJet"
        elif "vistara" in lower_name or lower_name == "uk":
            return "Vistara"
        elif "star air" in lower_name or lower_name == "s5":
            return "Star Air"
        elif "alliance air" in lower_name or lower_name == "9i":
            return "Alliance Air"

        return cleaned.title()

    @staticmethod
    def normalize_iata_code(code: str) -> str:
        """Standardizes airport codes to 3-letter uppercase IATA format."""
        if not code:
            raise ValueError("IATA airport code cannot be empty")
        cleaned = str(code).strip().upper()
        # Extract 3 letter code if surrounded by brackets or details like 'DEL, T1'
        match = re.search(r"\b([A-Z]{3})\b", cleaned)
        if match:
            return match.group(1)
        if len(cleaned) == 3 and cleaned.isalpha():
            return cleaned
        raise ValueError(f"Invalid IATA airport code format: '{code}'")

    @staticmethod
    def normalize_date(raw_date: str, target_year: Optional[int] = None) -> str:
        """
        Normalizes various date formats ('17th Oct', '2026-10-17', '17-10-2026') into 'YYYY-MM-DD'.
        """
        """
        Normalize dates such as:
        '17th Oct'      -> 'YYYY-10-17'
        '17 Oct 2026'  -> '2026-10-17'
        '17-10-2026'   -> '2026-10-17'
        '2026-10-17'   -> '2026-10-17'
        """

        if not raw_date:
            raise ValueError("Date cannot be empty")

        if target_year is None:
            target_year = datetime.now().year
        cleaned = str(raw_date).strip()
        
        # Already YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
            return cleaned

        # DD-MM-YYYY or DD/MM/YYYY
        match_dmy = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", cleaned)
        if match_dmy:
            d, m, y = match_dmy.groups()
            return f"{y}-{int(m):02d}-{int(d):02d}"

        # Try parsing '17th Oct', '17 Oct 2026', '17-Oct-2026'
        cleaned_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", cleaned, flags=re.IGNORECASE)
        for fmt in ("%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d %b", "%d-%b"):
            try:
                for fmt in ("%d %b", "%d-%b"):
                    try:
                        dt = datetime.strptime(
                            f"{cleaned_str} {target_year}",
                            f"{fmt} %Y"
                        )
                        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
                    except ValueError:
                        continue
                year = dt.year if "%Y" in fmt else target_year
                return f"{year:04d}-{dt.month:02d}-{dt.day:02d}"
            except ValueError:
                continue

        raise ValueError(f"Could not parse date format: '{raw_date}'")

    @staticmethod
    def normalize_currency(val: Any) -> Optional[float]:
        """Alias for normalize_currency_amount."""
        return DataNormalizer.normalize_currency_amount(val)

    @staticmethod
    def normalize_time(raw_time: str) -> str:
        """
        Normalizes departure/arrival time strings into 'HH:MM' 24-hour format.
        """
        cleaned = str(raw_time).strip()
        match_time = re.search(r"(\d{1,2}):(\d{2})", cleaned)
        if match_time:
            h, m = match_time.groups()
            return f"{int(h):02d}:{m}"
        raise ValueError(f"Could not parse time: '{raw_time}'")

    @staticmethod
    def normalize_time_format(raw_time: str) -> Optional[str]:
        """Alias for normalize_time with graceful None handling."""
        if not raw_time:
            return None
        try:
            return DataNormalizer.normalize_time(raw_time)
        except ValueError:
            return None

    @staticmethod
    def normalize_date_format(raw_date: str, target_year: Optional[int] = None) -> Optional[str]:
        """Alias for normalize_date with graceful None handling."""
        if not raw_date:
            return None
        try:
            return DataNormalizer.normalize_date(raw_date, target_year=target_year)
        except ValueError:
            return None

    @staticmethod
    def normalize_flight_number(raw_fl: str, airline: str = "") -> str:
        """Standardizes flight numbers like 'SG-8723' -> 'SG 8723', '6E-5314' -> '6E 5314'."""
        if not raw_fl:
            return None
        cleaned = str(raw_fl).strip().upper().replace("-", " ")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

