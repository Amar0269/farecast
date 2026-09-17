"""
Unit tests for DataNormalizer.
"""

import pytest
from processors.normalizer import DataNormalizer


def test_currency_normalization():
    assert DataNormalizer.normalize_currency_amount("₹6,546") == 6546.0
    assert DataNormalizer.normalize_currency_amount("Rs 4,299") == 4299.0
    assert DataNormalizer.normalize_currency_amount("4,299 INR") == 4299.0
    assert DataNormalizer.normalize_currency_amount("7019") == 7019.0
    assert DataNormalizer.normalize_currency_amount(5080) == 5080.0
    assert DataNormalizer.normalize_currency_amount("N/A") is None
    assert DataNormalizer.normalize_currency_amount("-") is None
    assert DataNormalizer.normalize_currency_amount("Sold Out") is None


def test_airline_normalization():
    assert DataNormalizer.normalize_airline_name("INDIGO") == "IndiGo"
    assert DataNormalizer.normalize_airline_name("6E") == "IndiGo"
    assert DataNormalizer.normalize_airline_name("air india express") == "Air India Express"
    assert DataNormalizer.normalize_airline_name("spicejet") == "SpiceJet"


def test_iata_normalization():
    assert DataNormalizer.normalize_iata_code("del") == "DEL"
    assert DataNormalizer.normalize_iata_code(" BOM ") == "BOM"
    assert DataNormalizer.normalize_iata_code("DEL, Terminal 1") == "DEL"
    with pytest.raises(ValueError):
        DataNormalizer.normalize_iata_code("INVALID_CODE")


def test_date_normalization():
    assert DataNormalizer.normalize_date("2026-10-17") == "2026-10-17"
    assert DataNormalizer.normalize_date("17-10-2026") == "2026-10-17"
    assert DataNormalizer.normalize_date("17th Oct", target_year=2026) == "2026-10-17"


def test_time_normalization():
    assert DataNormalizer.normalize_time("05:00") == "05:00"
    assert DataNormalizer.normalize_time("05:00 DEL, T1") == "05:00"
    assert DataNormalizer.normalize_time("17:10 BOM, T1") == "17:10"
