"""
Production Dataset Builder & Matrix Collector for Member 1 (SIH26056).
Executes 30-search matrix collection across configured routes and advance purchase windows.
Processes live & captured raw server payloads, cleans, normalizes, deduplicates, flags outliers,
and outputs data/processed/airfare_observations.csv, data/processed/airfare_observations.json,
and data/processed/collection_runs/manifest_<timestamp>.json.
"""

import os
import json
import glob
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from models.fare import FareObservation, CollectionStatus
from scrapers.yatra import YatraSource
from processors.cleaner import DataCleaner
from processors.validator import DataValidator
from pipelines.collect import load_config, calculate_travel_dates, export_processed_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("ProductionDatasetBuilder")


def build_production_dataset(config_path: str = "config/routes.yaml") -> Dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    run_id = f"run_{start_time.strftime('%Y%m%d_%H%M%S')}"

    config = load_config(config_path)
    routes = config.get("routes", [])
    advance_days = config.get("advance_purchase_days", [1, 7, 15, 30, 45])
    sources = ["yatra"]

    logger.info("Executing 30-search sampling matrix collection...")
    yatra_adapter = YatraSource( config.get("source_settings", {}).get("yatra", {}))

    all_raw_observations: List[FareObservation] = []

    searches_attempted = 0
    successful_searches = 0
    blocked_searches = 0
    failed_searches = 0
    no_result_searches = 0

    per_route_counts = {f"{r['origin']}-{r['destination']}": 0 for r in routes}
    per_window_counts = {f"T+{d}": 0 for d in advance_days}
    per_source_counts = {src: 0 for src in sources}

    # 1. Execute Matrix Queries
    for route in routes:
        orig = route["origin"]
        dest = route["destination"]
        route_str = f"{orig}-{dest}"
        windows = calculate_travel_dates(start_time, advance_days)

        for win in windows:
            t_date = win["travel_date"]
            win_str = win["window"]
            searches_attempted += 1

            scrape_res = yatra_adapter.search(origin=orig, destination=dest, travel_date=t_date)

            if scrape_res.status == CollectionStatus.SUCCESS and scrape_res.observations:
                successful_searches += 1
                for obs in scrape_res.observations:
                    cleaned_obs = DataCleaner.clean_observation(obs, collection_date_override=scrape_res.collection_timestamp)
                    all_raw_observations.append(cleaned_obs)
            elif scrape_res.status == CollectionStatus.SOURCE_BLOCKED:
                blocked_searches += 1
            else:
                failed_searches += 1

    # 2. Ingest captured server payload raw files for any offline or pre-rendered search responses
    raw_files = sorted(glob.glob("data/raw/yatra/*.json"))
    for rf in raw_files:
        try:
            with open(rf, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            meta = raw_data.get("metadata", {})
            payload = raw_data.get("raw_payload", "")
            if payload and len(payload) > 1000:
                orig = meta.get("origin")
                dest = meta.get("destination")
                t_date = meta.get("travel_date")
                col_ts = meta.get("collection_timestamp")
                if not orig or not dest or t_date:
                    logger.warning(f"Skipping raw file with incomplete metadata:{rf}")

                obs_list = yatra_adapter.parse_html(payload, orig, dest, t_date)
                for obs in obs_list:
                    cleaned_obs = DataCleaner.clean_observation(obs, collection_date_override=col_ts)
                    all_raw_observations.append(cleaned_obs)
        except Exception as e:
            logger.warning(f"Error parsing raw file {rf}: {e}")

    # 3. Full Matrix Deduplication & Outlier Detection
    deduped_observations = DataValidator.deduplicate(all_raw_observations)
    final_observations = DataValidator.flag_outliers(deduped_observations)

    # Re-tally per route, window, source counts from final clean production observations
    for obs in final_observations:
        r_key = obs.route
        w_key = obs.advance_purchase_window or "UNKNOWN"
        s_key = obs.source.lower()

        per_route_counts[r_key] = per_route_counts.get(r_key, 0) + 1
        per_window_counts[w_key] = per_window_counts.get(w_key, 0) + 1
        per_source_counts[s_key] = per_source_counts.get(s_key, 0) + 1

    duplicate_count = sum(1 for obs in final_observations if obs.duplicate_flag)
    outlier_count = sum(1 for obs in final_observations if obs.outlier_flag)

    end_time = datetime.now(timezone.utc)

    # 4. Generate Collection Manifest
    manifest_data = {
        "run_id": run_id,
        "collection_timestamps": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        "sources": sources,
        "routes": [f"{r['origin']}-{r['destination']}" for r in routes],
        "windows": [f"T+{d}" for d in advance_days],
        "searches_attempted": searches_attempted,
        "successful_searches": successful_searches,
        "blocked_searches": blocked_searches,
        "failed_searches": failed_searches,
        "no_result_searches": no_result_searches,
        "total_real_observations_collected": len(final_observations),
        "duplicate_count": duplicate_count,
        "outlier_count": outlier_count,
        "per_route_counts": per_route_counts,
        "per_window_counts": per_window_counts,
        "per_source_counts": per_source_counts
    }

    manifest_dir = "data/processed/collection_runs"
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, f"manifest_{start_time.strftime('%Y%m%d_%H%M%S')}.json")

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # 5. Export Primary Processed Dataset (CSV & JSON)
    export_processed_data("data/processed", final_observations)

    logger.info(f"Production dataset built successfully.")
    logger.info(f"Primary CSV: data/processed/airfare_observations.csv")
    logger.info(f"Primary JSON: data/processed/airfare_observations.json")
    logger.info(f"Manifest: {manifest_path}")
    logger.info(f"Total Real Observations: {len(final_observations)}")

    return manifest_data


if __name__ == "__main__":
    build_production_dataset()
