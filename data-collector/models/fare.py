"""
Pydantic model representing a standardized 32-field Airfare Price Observation.
Adheres strictly to the SIH26056 schema requirements for MoSPI Airfare Price Index calculation.
"""

from enum import Enum
from typing import List, Optional, Any
import uuid
import re
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator


def _clean_monetary_val(val: Any) -> Optional[float]:
    """Helper to parse raw currency strings like '₹6,546', 'Rs 4,299' into float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val >= 0 else None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("n/a", "na", "-", "—", "null", "blank", "not available", "sold out", "unavailable"):
        return None
    cleaned = re.sub(r"[^\d.]", "", val_str)
    if not cleaned:
        return None
    try:
        amt = float(cleaned)
        return amt if amt >= 0 else None
    except ValueError:
        return None


class CollectionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    SOLD_OUT = "SOLD_OUT"
    SOURCE_BLOCKED = "SOURCE_BLOCKED"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    API_REQUIRED = "API_REQUIRED"
    PARSER_WORKING_BUT_LIVE_BLOCKED = "PARSER_WORKING_BUT_LIVE_BLOCKED"
    TIMEOUT = "TIMEOUT"
    PARSER_ERROR = "PARSER_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class FareObservation(BaseModel):
    # 1-4 IDENTIFICATION
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = Field(description="Source name, e.g., 'indigo'")
    source_url: Optional[str] = Field(default=None, description="URL where fare was extracted")
    collection_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of collection"
    )

    # 5-13 FLIGHT
    airline: str = Field(description="Standardized airline name, e.g., 'IndiGo'")
    flight_number: str = Field(description="Flight designation, e.g., '6E 449'")
    origin: str = Field(description="IATA 3-letter origin airport code, e.g., 'DEL'")
    destination: str = Field(description="IATA 3-letter destination airport code, e.g., 'BOM'")
    route: str = Field(description="Route format 'ORIGIN-DEST', e.g., 'DEL-BOM'")
    travel_date: str = Field(description="Date of flight in 'YYYY-MM-DD' format")
    departure_time: Optional[str] = Field(default=None, description="Departure time 'HH:MM'")
    arrival_time: Optional[str] = Field(default=None, description="Arrival time 'HH:MM'")
    stops: int = Field(default=0, description="Number of stops (0 for non-stop)")

    # 14-23 FARE DETAILS
    cabin_class: Optional[str] = Field(default=None, description="e.g., 'Economy', 'Business'")
    fare_class: Optional[str] = Field(default=None, description="e.g., 'Saver', 'Flexi Plus', 'Lite'")
    fare_type: Optional[str] = Field(default=None, description="e.g., 'Standard', 'Student'")
    base_fare: Optional[float] = Field(default=None, description="Base fare in INR")
    taxes: Optional[float] = Field(default=None, description="Taxes and airport charges")
    user_development_fee: Optional[float] = Field(default=None, description="UDF component if exposed")
    convenience_fee: Optional[float] = Field(default=None, description="Convenience fee if exposed")
    other_fees: Optional[float] = Field(default=None, description="Other ancillary fees if exposed")
    total_fare: Optional[float] = Field(default=None, description="Total fare in currency units")
    currency: str = Field(default="INR", description="Currency ISO code")

    # 24-25 AVAILABILITY
    availability_status: str = Field(default="available", description="available, sold_out, unavailable, etc.")
    seats_available: Optional[int] = Field(default=None, description="Seats remaining if specified")

    # 26-27 LEAD TIME
    advance_purchase_days: Optional[int] = Field(default=None, description="Days between collection & flight")
    advance_purchase_window: Optional[str] = Field(default=None, description="T+1, T+7, T+15, T+30, T+45, Other")

    # 28 RAW/AUDIT
    raw_fare_text: Optional[str] = Field(default=None, description="Preserved unparsed raw fare card HTML/text")

    # 29-32 DATA QUALITY
    cleaning_status: str = Field(default="RAW", description="RAW, CLEAN, WARNING, INVALID")
    outlier_flag: bool = Field(default=False, description="Flagged by outlier detection")
    duplicate_flag: bool = Field(default=False, description="Flagged as duplicate observation")
    missing_fields: List[str] = Field(default_factory=list, description="List of unavailable schema fields")

    @field_validator(
        "base_fare", "taxes", "user_development_fee",
        "convenience_fee", "other_fees", "total_fare",
        mode="before"
    )
    def normalize_monetary_input(cls, v: Any) -> Optional[float]:
        return _clean_monetary_val(v)

    @field_validator("origin", "destination")
    def validate_iata(cls, v: str) -> str:
        v_str = str(v).strip().upper()
        if len(v_str) != 3 or not v_str.isalpha():
            raise ValueError(f"Invalid IATA airport code: {v}")
        return v_str

    def update_missing_fields(self) -> List[str]:
        """Recomputes list of missing/null fields dynamically."""
        field_checks = [
            ("departure_time", self.departure_time),
            ("arrival_time", self.arrival_time),
            ("cabin_class", self.cabin_class),
            ("fare_class", self.fare_class),
            ("fare_type", self.fare_type),
            ("base_fare", self.base_fare),
            ("taxes", self.taxes),
            ("user_development_fee", self.user_development_fee),
            ("convenience_fee", self.convenience_fee),
            ("other_fees", self.other_fees),
            ("total_fare", self.total_fare),
            ("seats_available", self.seats_available),
            ("advance_purchase_days", self.advance_purchase_days),
        ]
        missing = [fname for fname, fval in field_checks if fval is None]
        self.missing_fields = sorted(list(set(missing)))
        return self.missing_fields

    @model_validator(mode="after")
    def populate_computed_fields(self) -> "FareObservation":
        # Ensure route matches origin-destination
        expected_route = f"{self.origin}-{self.destination}"
        if self.route != expected_route:
            self.route = expected_route

        self.update_missing_fields()
        return self

    def to_csv_dict(self) -> dict:
        """Flattens model into strict 32-field dictionary suitable for CSV export."""
        d = self.model_dump()
        d["missing_fields"] = ";".join(self.missing_fields)
        return d
