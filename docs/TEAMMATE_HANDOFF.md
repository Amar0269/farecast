# Member 1 Data Collector & Data Cleaning Handoff (SIH26056)

**Problem Statement**: SIH26056 — Real-time Airfare Price Index for India (MoSPI / DIID)  
**Author**: Lead Engineer (Member 1 - Data Collection + Cleaning)  
**Target Audience**: Member 2 (Database / Backend / Analytics Integration)

---

## 📌 Dataset Quick Reference

| Dataset File | File Location | Record Count | Description |
|---|---|---|---|
| **Production CSV** | [`data-collector/data/processed/airfare_observations.csv`](file:///Users/amar/farecast/data-collector/data/processed/airfare_observations.csv) | **604** | Primary 32-field dataset formatted for PostgreSQL COPY / pandas import |
| **Production JSON** | [`data-collector/data/processed/airfare_observations.json`](file:///Users/amar/farecast/data-collector/data/processed/airfare_observations.json) | **604** | Primary 32-field JSON array for API / backend consumption |
| **Run Manifest** | [`data-collector/data/processed/collection_runs/manifest_20260917_073450.json`](file:///Users/amar/farecast/data-collector/data/processed/collection_runs/) | **1** | Full matrix collection summary audit trail |

---

## 📊 Dataset Breakdown

- **Total Real Observations**: **604**
- **Unique Observations**: **604**
- **Duplicate Count**: **0**
- **Outlier Count**: **8** (IQR flagged)
- **Collection Timestamp**: `2026-09-17T06:06:35Z`
- **Source Availability**:
  - `Yatra`: **SUCCESS** (604 observations)
  - `IndiGo`, `EaseMyTrip`, `Ixigo`, `Air India`, `Air India Express`, `Akasa Air`, `SpiceJet`, `Cleartrip`, `Goibibo`, `MakeMyTrip`: **`SOURCE_BLOCKED`** (HTTP 403 / Cloudflare / Akamai WAF access control)

### Observations Per Airline
- **Air India**: 284
- **IndiGo**: 236
- **Air India Express**: 54
- **Akasa Air**: 24
- **SpiceJet**: 6

### Observations Per Route
- **DEL-BOM**: 604

### Observations Per Advance Purchase Window
- **T+30**: 604

---

## 📐 32-Field Schema Specification

| Field # | Column Name | Data Type | Nullable | Description & Constraints | Example |
|---|---|---|---|---|---|
| 1 | `observation_id` | UUID string | No | Unique observation identifier | `012fa35a-d119-4cfe-a1d5-2e6da9b0085d` |
| 2 | `source` | VARCHAR(32) | No | Target source adapter | `yatra` |
| 3 | `source_url` | TEXT | Yes | Exact query URL where fare was extracted | `https://flight.yatra.com/...` |
| 4 | `collection_timestamp` | TIMESTAMP (UTC) | No | ISO 8601 collection timestamp | `2026-09-17T06:06:35.431622Z` |
| 5 | `airline` | VARCHAR(64) | No | Standardized canonical airline name | `IndiGo`, `Air India`, `Akasa Air` |
| 6 | `flight_number` | VARCHAR(32) | No | Standardized flight number (`<CODE> <NUM>`) | `6E 353`, `AI 2678`, `QP 1833` |
| 7 | `origin` | CHAR(3) | No | 3-letter IATA origin airport code | `DEL` |
| 8 | `destination` | CHAR(3) | No | 3-letter IATA destination airport code | `BOM` |
| 9 | `route` | VARCHAR(10) | No | Route formatted as `ORIGIN-DEST` | `DEL-BOM` |
| 10 | `travel_date` | DATE | No | Flight date `YYYY-MM-DD` | `2026-10-17` |
| 11 | `departure_time` | VARCHAR(5) | Yes | Departure 24h time `HH:MM` | `06:50` |
| 12 | `arrival_time` | VARCHAR(5) | Yes | Arrival 24h time `HH:MM` | `09:10` |
| 13 | `stops` | INT | No | Number of stops (0 for non-stop) | `0` |
| 14 | `cabin_class` | VARCHAR(32) | Yes | Seating cabin (`Economy`, `Business`) | `Economy` |
| 15 | `fare_class` | VARCHAR(32) | Yes | Fare family tier (`Saver Fare`, `Flexi Fare`) | `Saver Fare` |
| 16 | `fare_type` | VARCHAR(32) | Yes | Ticket fare condition | `NULL` |
| 17 | `base_fare` | NUMERIC(10,2) | Yes | Pure base fare in INR | `5715.00` |
| 18 | `taxes` | NUMERIC(10,2) | Yes | Taxes & surcharge breakdown | `894.00` |
| 19 | `user_development_fee` | NUMERIC(10,2) | Yes | Airport UDF component | `0.00` |
| 20 | `convenience_fee` | NUMERIC(10,2) | Yes | Payment convenience fee | `NULL` |
| 21 | `other_fees` | NUMERIC(10,2) | Yes | Ancillary fees | `NULL` |
| 22 | `total_fare` | NUMERIC(10,2) | Yes | Total ticket fare in INR | `6609.00` |
| 23 | `currency` | CHAR(3) | No | Currency ISO code | `INR` |
| 24 | `availability_status` | VARCHAR(20) | No | `available`, `sold_out`, `unavailable` | `available` |
| 25 | `seats_available` | INT | Yes | Remaining seats | `NULL` |
| 26 | `advance_purchase_days` | INT | Yes | Days between collection & flight date | `30` |
| 27 | `advance_purchase_window` | VARCHAR(10) | Yes | `T+1`, `T+7`, `T+15`, `T+30`, `T+45`, `Other` | `T+30` |
| 28 | `raw_fare_text` | TEXT | Yes | Preserved DOM/JSON snippet | `{"ID": "DELBOMQP1833..."}` |
| 29 | `cleaning_status` | VARCHAR(15) | No | `RAW`, `CLEAN`, `WARNING`, `INVALID` | `CLEAN` |
| 30 | `outlier_flag` | BOOLEAN | No | Interquartile Range (IQR) price outlier flag | `false` |
| 31 | `duplicate_flag` | BOOLEAN | No | Deterministic SHA-256 duplicate flag | `false` |
| 32 | `missing_fields` | TEXT | Yes | Semicolon-delimited null schema fields | `convenience_fee;fare_type;...` |

---

## 🗄️ PostgreSQL Database Import Guide (Member 2)

Member 2 can immediately load `airfare_observations.csv` into PostgreSQL using the following DDL & COPY script:

```sql
-- 1. Create Tablespace & Enum Types
CREATE TYPE collection_status_enum AS ENUM (
    'RAW', 'CLEAN', 'WARNING', 'INVALID'
);

-- 2. Create Airfare Observations Table
CREATE TABLE airfare_observations (
    observation_id UUID PRIMARY KEY,
    source VARCHAR(32) NOT NULL,
    source_url TEXT,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    airline VARCHAR(64) NOT NULL,
    flight_number VARCHAR(32) NOT NULL,
    origin CHAR(3) NOT NULL,
    destination CHAR(3) NOT NULL,
    route VARCHAR(10) NOT NULL,
    travel_date DATE NOT NULL,
    departure_time VARCHAR(5),
    arrival_time VARCHAR(5),
    stops INT DEFAULT 0,
    cabin_class VARCHAR(32),
    fare_class VARCHAR(32),
    fare_type VARCHAR(32),
    base_fare NUMERIC(10,2),
    taxes NUMERIC(10,2),
    user_development_fee NUMERIC(10,2),
    convenience_fee NUMERIC(10,2),
    other_fees NUMERIC(10,2),
    total_fare NUMERIC(10,2),
    currency CHAR(3) DEFAULT 'INR',
    availability_status VARCHAR(20) DEFAULT 'available',
    seats_available INT,
    advance_purchase_days INT,
    advance_purchase_window VARCHAR(10),
    raw_fare_text TEXT,
    cleaning_status VARCHAR(15) DEFAULT 'CLEAN',
    outlier_flag BOOLEAN DEFAULT FALSE,
    duplicate_flag BOOLEAN DEFAULT FALSE,
    missing_fields TEXT
);

-- 3. Create Performance Indexes for MoSPI Index Analytics
CREATE INDEX idx_fares_route_date ON airfare_observations (route, travel_date);
CREATE INDEX idx_fares_airline ON airfare_observations (airline);
CREATE INDEX idx_fares_window ON airfare_observations (advance_purchase_window);

-- 4. Execute Fast CSV COPY Import
\copy airfare_observations FROM 'data-collector/data/processed/airfare_observations.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');
```

---

## ⚙️ Cleaning, Normalization & Quality Rules

1. **Deduplication Logic**:
   - Unique key generated via SHA-256 of `source|airline|flight_number|origin|destination|travel_date|departure_time|fare_class`.
   - Duplicates are marked with `duplicate_flag = true` (never dropped).
2. **Outlier Detection**:
   - Uses Interquartile Range (IQR) on `total_fare`: Fares outside $[Q_1 - 1.5 \times IQR, Q_3 + 1.5 \times IQR]$ set `outlier_flag = true`.
3. **Missing Value Integrity**:
   - Unavailable monetary breakdown fields (e.g. `convenience_fee`) remain `NULL` rather than fake `0` values to avoid distorting CPI price index calculations.
