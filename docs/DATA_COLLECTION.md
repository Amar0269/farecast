# Data Collection & Indian Domestic Airfare Matrix Pipeline (SIH26056)

**Problem Statement**: SIH26056 — Real-time Airfare Price Index for India (MoSPI / DIID)  
**Author**: Lead Engineer (Member 1 - Data Collection + Cleaning)

---

## 📌 Architecture Overview

The SIH26056 Data Collector features a **Yatra Route Discovery Engine** that builds a full, real-world **Indian Domestic Route Catalog** rather than restricting collection to hard-coded routes.

```
Yatra Route Discovery Engine
  │
  ▼
Full Indian Domestic Route Catalog (data/processed/route_catalog.csv)
  │
  ▼
Lead-Time Window Matrix (T+1, T+7, T+15, T+30, T+45)
  │
  ▼
Batch & Resumable Collector Engine (pipelines/bulk_collector.py)
  │
  ▼
ALL Flight/Fare Extraction per Search (parse_json_payload + DOM parser)
  │
  ▼
Data Cleaner & Normalizer (processors/cleaner.py)
  │
  ▼
SHA-256 Deduplication & IQR Outlier Flagging (processors/validator.py)
  │
  ▼
32-Field Production Dataset & Collection Audit Manifests
```

---

## 🛫 1. Route Discovery & Catalog

The collector dynamically discovers and validates domestic Indian origin-destination airport pairs from Yatra:

- **Discovered Indian Domestic Airports**: 43 major and secondary Indian airports (`DEL`, `BOM`, `BLR`, `CCU`, `HYD`, `MAA`, `AMD`, `PNQ`, `GOI`, `GOX`, `COK`, `TRV`, `IXC`, `LKO`, `PAT`, `GAU`, `BBI`, `VNS`, `IXB`, `BDQ`, `IDR`, `NAG`, `RPR`, `SXR`, `IXJ`, `ATQ`, `VTZ`, `IXE`, `TRZ`, `CJB`, `IXM`, `IXA`, `IMF`, `DIB`, `STV`, `UDR`, `JDH`, `DED`, `IXR`, `GWL`, `KUU`, `DHM`).
- **Route Matrix**: 630 directional routes.
- **Directionality Preserved**: `DEL-BOM` and `BOM-DEL` are distinct directional routes.
- **Filtering**: Excludes international routes, invalid IATA codes, self-loops, and malformed pairs.

### Route Classification
1. **SIH Representative Reference Routes (6 Routes)**:
   - `DEL-BOM`, `DEL-BLR`, `BOM-BLR`, `DEL-CCU`, `BLR-HYD`, `MAA-DEL`
   - Preserved as benchmark index reference routes.
2. **Full Discovered Indian Domestic Route Universe (630 Directional Routes)**:
   - Complete coverage of Indian domestic civil aviation network listed on Yatra.

Catalog output files:
- `data/processed/route_catalog.csv`
- `data/processed/route_catalog.json`

---

## 📅 2. Advance-Purchase Window Matrix

For every route in the catalog, searches are executed across 5 standardized lead-time windows:
- **T+1** (Next-day departure)
- **T+7** (1 week advance)
- **T+15** (2 weeks advance)
- **T+30** (1 month advance)
- **T+45** (1.5 months advance)

Calculation: `travel_date = collection_date + advance_purchase_days`

---

## 🔍 3. All-Flight Extraction Policy

For every successful search query:
- Extracts **ALL** returned flight and fare observations (not just the cheapest flight or first result).
- Preserves complete fare breakdowns: `base_fare`, `taxes`, `user_development_fee`, `total_fare`.
- If zero flights are listed, records `NO_RESULTS`.
- If access is blocked, records `SOURCE_BLOCKED`.
- Never invents synthetic or fake observations.

---

## ⚡ 4. Batch Execution & Resumable Collection Engine

The collector includes a CLI supporting paced batch runs and checkpointing:

```bash
# 1. Discover routes & generate route catalog
python pipelines/bulk_collector.py --discover-routes

# 2. Run bulk collection with limits and delay pacing
python pipelines/bulk_collector.py --run-bulk --limit-routes 10 --limit-windows 5 --delay 0.5 --source yatra

# 3. Resume interrupted collection seamlessly
python pipelines/bulk_collector.py --run-bulk --resume
```

### CLI Arguments
- `--discover-routes`: Generates the domestic route catalog.
- `--run-bulk`: Runs bulk airfare collection.
- `--limit-routes N`: Limits collection to first N routes.
- `--limit-windows N`: Limits advance purchase windows (e.g. 5 for T+1..T+45).
- `--resume`: Resumes from `data/processed/checkpoints/checkpoint_state.json`.
- `--delay SECONDS`: Configurable rate-limiting delay between searches (default: 0.2s).
- `--source SOURCE`: Source adapter name (default: `yatra`).

---

## 🧹 5. Data Cleaning & 32-Field Schema Compliance

All observations are normalized and cleaned into the strict 32-field `FareObservation` Pydantic model:
- Deterministic SHA-256 deduplication (sets `duplicate_flag=True`, preserves historical records).
- Interquartile Range (IQR) price outlier detection (sets `outlier_flag=True`, never deletes outliers).
- Preserves raw server payload in `raw_fare_text`.
- Recomputes missing field metadata in `missing_fields`.

Primary production outputs:
- `data/processed/airfare_observations.csv`
- `data/processed/airfare_observations.json`
