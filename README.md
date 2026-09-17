# Farecast — Real-Time Airfare Price Index for India (SIH26056)

## Member 1 Responsibility: Data Collection + Data Cleaning

This repository contains the complete, production-ready Data Collection and Data Cleaning subsystem for Problem Statement **SIH26056**: *"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)"*.

---

## 🌟 Key Architecture & Highlights

- **Standardized 32-Field Schema**: Built on Pydantic `FareObservation` schema covering identification, flight details, price breakdowns, availability, lead-time windows, raw audit trails, and data quality flags.
- **Source-Agnostic Adapter Pattern**: Unified `BaseFareSource` abstract interface supporting **11 target SIH sources**:
  1. **IndiGo** (`scrapers/indigo.py`)
  2. **EaseMyTrip** (`scrapers/easemytrip.py`)
  3. **Ixigo** (`scrapers/ixigo.py`)
  4. **Yatra** (`scrapers/yatra.py`)
  5. **Air India** (`scrapers/airindia.py`)
  6. **Air India Express** (`scrapers/airindiaexpress.py`)
  7. **Akasa Air** (`scrapers/akasa.py`)
  8. **SpiceJet** (`scrapers/spicejet.py`)
  9. **Cleartrip** (`scrapers/cleartrip.py`)
  10. **Goibibo** (`scrapers/goibibo.py`)
  11. **MakeMyTrip** (`scrapers/makemytrip.py`)
- **Compliant Access & Robust Block Handling**: Strictly uses permitted HTTP/REST request mechanisms without evasion or anti-bot bypass. Blocked requests (WAF/Cloudflare/Akamai HTTP 403/429/503) are gracefully trapped as `CollectionStatus.SOURCE_BLOCKED` with preserved raw payloads.
- **Data Cleaning & Normalization**:
  - `DataNormalizer`: Canonical airline names, 3-letter IATA uppercase airport codes, ISO 8601 dates (`YYYY-MM-DD`), 24-hour time format (`HH:MM`), and numeric currency values.
  - `DataCleaner`: Computes lead-time days and maps into standard advance purchase windows (`T+1`, `T+7`, `T+15`, `T+30`, `T+45`, `Other`).
  - `DataValidator`: Deterministic SHA-256 deduplication within sources and statistical Interquartile Range (IQR) price outlier flagging without dropping dynamic fares.
- **Storage & Export**: Preserves raw HTML/JSON responses in `data/raw/<source>/` with timestamps, and exports clean datasets to `data/processed/` in CSV and JSON formats.

---

## 📁 Repository Structure

```
farecast/
├── README.md                           # Root documentation & team integration guide
├── docs/                               # Source investigation & block logs for all 11 sources
│   ├── indigo-final-access-investigation.md
│   ├── easemytrip-final-access-investigation.md
│   ├── ixigo-final-access-investigation.md
│   ├── yatra-source-investigation.md
│   └── ...
└── data-collector/                     # Main python subsystem
    ├── config/
    │   └── routes.yaml                 # 6 top routes + 5 advance purchase windows + 11 source configs
    ├── models/
    │   └── fare.py                     # 32-field FareObservation Pydantic model
    ├── scrapers/
    │   ├── base.py                     # BaseFareSource & ScrapeResult models
    │   ├── yatra.py                    # Yatra source adapter
    │   ├── easemytrip.py               # EaseMyTrip source adapter
    │   └── ...                         # Adapters for all 11 sources
    ├── processors/
    │   ├── normalizer.py               # DataNormalizer (dates, times, airlines, fares, IATA)
    │   ├── cleaner.py                  # DataCleaner (advance purchase lead time & cleaning status)
    │   └── validator.py                # DataValidator (SHA-256 deduplication & IQR outlier flagging)
    ├── pipelines/
    │   └── collect.py                  # End-to-end collection, matrix runner, & manifest generator
    ├── data/
    │   ├── raw/                        # Timestamped raw scrape responses per source
    │   └── processed/                  # Standardized CSV, JSON, and collection manifests
    └── tests/                          # Complete unit & integration test suite (57 tests)
```

---

## 🚀 Quick Start for Teammates

### 1. Setup Virtual Environment & Install Dependencies

```bash
cd data-collector
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Test Suite

```bash
pytest tests/
```
*Expected result: 57/57 tests passing.*

### 3. Run Single Query Collection

```bash
python -m pipelines.collect --source yatra --origin DEL --destination BOM --travel-date 2026-10-17
```

### 4. Run Bulk Matrix Collection (All Configured Routes & Lead Times)

```bash
python -m pipelines.collect --run-matrix --source yatra
```
This runs collection across all 6 key routes (`DEL-BOM`, `DEL-BLR`, `BOM-BLR`, `DEL-CCU`, `BLR-HYD`, `MAA-DEL`) and 5 advance purchase dates (`T+1`, `T+7`, `T+15`, `T+30`, `T+45`), generating clean exports and a `manifest_<timestamp>.json` summary in `data/processed/`.

---

## 📊 Standardized 32-Field Schema Reference

| Field # | Field Name | Description | Example |
|---|---|---|---|
| 1-4 | `observation_id`, `source`, `source_url`, `collection_timestamp` | Audit metadata & unique ID | `yatra`, `2026-09-17T06:50:00Z` |
| 5-13 | `airline`, `flight_number`, `origin`, `destination`, `route`, `travel_date`, `departure_time`, `arrival_time`, `stops` | Flight & itinerary details | `IndiGo`, `6E 449`, `DEL`, `BOM`, `DEL-BOM`, `2026-10-17`, `06:00`, `08:15`, `0` |
| 14-23 | `cabin_class`, `fare_class`, `fare_type`, `base_fare`, `taxes`, `user_development_fee`, `convenience_fee`, `other_fees`, `total_fare`, `currency` | Fare breakdown & currency | `Economy`, `Saver`, `4299.0`, `INR` |
| 24-25 | `availability_status`, `seats_available` | Seat availability tracking | `available`, `7` |
| 26-27 | `advance_purchase_days`, `advance_purchase_window` | MoSPI lead-time windowing | `30`, `T+30` |
| 28 | `raw_fare_text` | Preserved unparsed HTML/text DOM snippet | `<div class="flightitem"...` |
| 29-32 | `cleaning_status`, `outlier_flag`, `duplicate_flag`, `missing_fields` | Data quality & validation flags | `CLEAN`, `False`, `False`, `["taxes"]` |
