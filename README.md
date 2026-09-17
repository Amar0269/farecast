# Farecast — Real-Time Airfare Price Index for India (SIH26056)

## Member 1 Responsibility: Data Collection + Data Cleaning

This repository contains the complete, production-ready Data Collection and Data Cleaning subsystem for Problem Statement **SIH26056**: *"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)"*.

---

## 🌟 Key Architecture & Highlights

- **Yatra Route Discovery Engine**: Dynamically discovers and builds the complete **Indian Domestic Route Catalog** (630 directional routes across 43 airports) rather than limiting collection to hardcoded routes.
- **Resumable Bulk Collection Engine**: Paced, rate-limited batch collection pipeline with state checkpointing (`pipelines/bulk_collector.py`).
- **All-Flight Extraction Policy**: Collects **ALL** returned flight/fare observations per search (base fare, taxes, fees, total fare).
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
- **Compliant Access & Block Trapping**: Traps WAF/Cloudflare/Akamai blocks gracefully as `CollectionStatus.SOURCE_BLOCKED`.
- **Data Cleaning & Quality**: Normalization, lead-time window mapping (`T+1`, `T+7`, `T+15`, `T+30`, `T+45`), SHA-256 deduplication, and IQR outlier flagging.

---

## 📁 Repository Structure

```
farecast/
├── README.md                           # Root documentation & team integration guide
├── docs/                               # Documentation & source access reports
│   ├── DATA_COLLECTION.md              # Pipeline, Route Discovery & Bulk Collector Guide
│   ├── TEAMMATE_HANDOFF.md             # Member 2 PostgreSQL DDL & CSV import guide
│   └── ...                             # Access reports for all 11 sources
└── data-collector/                     # Main python subsystem
    ├── models/
    │   └── fare.py                     # 32-field FareObservation Pydantic model
    ├── scrapers/
    │   ├── route_discovery.py          # Yatra Indian domestic route discovery engine
    │   ├── yatra.py                    # Yatra source adapter with all-flight parser
    │   └── ...                         # Adapters for all 11 sources
    ├── processors/
    │   ├── normalizer.py               # DataNormalizer (dates, times, airlines, fares, IATA)
    │   ├── cleaner.py                  # DataCleaner (advance purchase lead time & status)
    │   └── validator.py                # DataValidator (SHA-256 deduplication & IQR flagging)
    ├── pipelines/
    │   ├── bulk_collector.py           # Resumable bulk batch collector & CLI
    │   └── collect.py                  # Single query & matrix collection runner
    ├── data/
    │   ├── raw/                        # Timestamped raw scrape responses
    │   └── processed/                  # Route catalog, airfare observations, checkpoints, manifests
    └── tests/                          # Complete unit & integration test suite (67 tests)
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
*Expected result: 67/67 tests passing.*

### 3. Route Discovery & Catalog Generation

```bash
python pipelines/bulk_collector.py --discover-routes
```
Generates `data/processed/route_catalog.csv` (630 directional domestic routes).

### 4. Resumable Bulk Collection Engine

```bash
python pipelines/bulk_collector.py --run-bulk --limit-routes 10 --limit-windows 5 --delay 0.3 --source yatra --resume
```

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
