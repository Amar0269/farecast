"""
Bulk Indian Domestic Airfare Collector & Resumable Checkpoint Engine (Member 1 - SIH26056).
Executes scaled batch collection across the discovered Indian domestic route catalog.
Supports pacing, rate-limiting, graceful error trapping, and progress checkpointing.
"""

import os
import json
import time
import logging
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set

from models.fare import FareObservation, CollectionStatus
from scrapers.yatra import YatraSource
from scrapers.route_discovery import RouteDiscovery
from processors.cleaner import DataCleaner
from processors.validator import DataValidator
from pipelines.collect import export_processed_data, calculate_travel_dates

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("BulkCollector")

CHECKPOINT_FILE = "data/processed/checkpoints/checkpoint_state.json"
PRIMARY_CSV = "data/processed/airfare_observations.csv"
PRIMARY_JSON = "data/processed/airfare_observations.json"


class CheckpointManager:
    @staticmethod
    def load_checkpoint() -> Dict[str, Any]:
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint file: {e}")
        return {"completed_searches": [], "last_updated": None}

    @staticmethod
    def save_checkpoint(completed_search_key: str):
        os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
        state = CheckpointManager.load_checkpoint()
        completed = set(state.get("completed_searches", []))
        completed.add(completed_search_key)
        state["completed_searches"] = sorted(list(completed))
        state["last_updated"] = datetime.now(timezone.utc).isoformat()

        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)


def load_existing_production_observations() -> List[FareObservation]:
    """Loads existing production observations to ensure historical data (including 604 observations) is preserved."""
    observations: List[FareObservation] = []
    if os.path.exists(PRIMARY_JSON):
        try:
            with open(PRIMARY_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    try:
                        obs = FareObservation(**item)
                        observations.append(obs)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Error loading existing primary JSON: {e}")
    logger.info(f"Loaded {len(observations)} existing production observations from {PRIMARY_JSON}.")
    return observations


def run_bulk_collection(
    limit_routes: Optional[int] = None,
    limit_windows: Optional[int] = None,
    resume: bool = True,
    delay_seconds: float = 0.2,
    source: str = "yatra"
) -> Dict[str, Any]:
    """
    Executes bulk airfare data collection across the discovered Indian domestic route catalog.
    Preserves all existing production observations, saves progress after each search,
    and outputs updated datasets and collection manifests.
    """
    start_time = datetime.now(timezone.utc)
    run_id = f"run_bulk_{start_time.strftime('%Y%m%d_%H%M%S')}"

    # 1. Ensure Route Catalog exists
    catalog_path = "data/processed/route_catalog.json"
    if not os.path.exists(catalog_path):
        logger.info("Route catalog not found. Executing route discovery first...")
        rd = RouteDiscovery(source_name=source)
        catalog = rd.generate_full_domestic_catalog()
        rd.export_catalog(catalog)
    else:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

    if limit_routes:
        catalog = catalog[:limit_routes]

    advance_days = [1, 7, 15, 30, 45]
    if limit_windows:
        advance_days = advance_days[:limit_windows]

    checkpoint_state = CheckpointManager.load_checkpoint() if resume else {"completed_searches": []}
    completed_keys: Set[str] = set(checkpoint_state.get("completed_searches", []))

    # Load existing production dataset to prevent data loss or duplication
    existing_observations = load_existing_production_observations()
    collected_new_observations: List[FareObservation] = []

    yatra_adapter = YatraSource()

    searches_attempted = 0
    successful_searches = 0
    blocked_searches = 0
    failed_searches = 0
    no_result_searches = 0

    per_route_counts = {item["route"]: 0 for item in catalog}
    per_window_counts = {f"T+{d}": 0 for d in advance_days}
    per_source_counts = {source: 0}

    logger.info(f"Starting bulk collection on {len(catalog)} routes and {len(advance_days)} advance purchase windows ({len(catalog)*len(advance_days)} total searches)...")

    for item in catalog:
        orig = item["origin_code"]
        dest = item["destination_code"]
        route_str = item["route"]

        windows = calculate_travel_dates(start_time, advance_days)

        for win in windows:
            t_date = win["travel_date"]
            win_str = win["window"]
            search_key = f"{source}|{orig}|{dest}|{t_date}"

            if resume and search_key in completed_keys:
                logger.info(f"Skipping already completed search: {search_key}")
                continue

            searches_attempted += 1
            logger.info(f"[{searches_attempted}] Searching {source.upper()}: {route_str} on {t_date} ({win_str})...")

            scrape_res = yatra_adapter.search(origin=orig, destination=dest, travel_date=t_date)

            if scrape_res.status == CollectionStatus.SUCCESS and scrape_res.observations:
                successful_searches += 1
                count = len(scrape_res.observations)
                logger.info(f"Successfully collected {count} observations for {route_str} on {t_date}.")

                for obs in scrape_res.observations:
                    cleaned_obs = DataCleaner.clean_observation(obs, collection_date_override=scrape_res.collection_timestamp)
                    collected_new_observations.append(cleaned_obs)

                per_route_counts[route_str] = per_route_counts.get(route_str, 0) + count
                per_window_counts[win_str] = per_window_counts.get(win_str, 0) + count
                per_source_counts[source] = per_source_counts.get(source, 0) + count
            elif scrape_res.status == CollectionStatus.SOURCE_BLOCKED:
                blocked_searches += 1
                logger.warning(f"Search blocked for {route_str} on {t_date}.")
            elif scrape_res.status == CollectionStatus.NO_RESULTS:
                no_result_searches += 1
            else:
                failed_searches += 1

            CheckpointManager.save_checkpoint(search_key)
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    # Combine existing historical observations with newly collected observations
    all_combined = existing_observations + collected_new_observations
    cleaned_all = [DataCleaner.clean_observation(o) for o in all_combined]
    deduped_all = DataValidator.deduplicate(cleaned_all)
    final_dataset = DataValidator.flag_outliers(deduped_all)

    # Export merged production dataset
    export_processed_data("data/processed", final_dataset)

    end_time = datetime.now(timezone.utc)
    duplicate_count = sum(1 for obs in final_dataset if obs.duplicate_flag)
    outlier_count = sum(1 for obs in final_dataset if obs.outlier_flag)

    manifest_data = {
        "run_id": run_id,
        "collection_timestamps": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        "sources": [source],
        "routes_discovered": len(catalog),
        "routes_attempted": len(catalog),
        "searches_attempted": searches_attempted,
        "successful_searches": successful_searches,
        "blocked_searches": blocked_searches,
        "failed_searches": failed_searches,
        "no_result_searches": no_result_searches,
        "total_real_observations_collected": len(final_dataset),
        "duplicate_count": duplicate_count,
        "outlier_count": outlier_count,
        "per_route_counts": {k: v for k, v in per_route_counts.items() if v > 0},
        "per_window_counts": {k: v for k, v in per_window_counts.items() if v > 0},
        "per_source_counts": per_source_counts
    }

    manifest_dir = "data/processed/collection_runs"
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, f"manifest_{start_time.strftime('%Y%m%d_%H%M%S')}.json")

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info("Bulk Collection Finished.")
    logger.info(f"Total Production Observations: {len(final_dataset)}")
    logger.info(f"Manifest written to: {manifest_path}")

    return manifest_data


def main():
    parser = argparse.ArgumentParser(description="Bulk Yatra Indian Domestic Airfare Collector")
    parser.add_argument("--discover-routes", action="store_true", help="Discover Indian domestic routes and generate catalog")
    parser.add_argument("--run-bulk", action="store_true", help="Run bulk collection across route catalog")
    parser.add_argument("--limit-routes", type=int, default=None, help="Limit number of routes to process")
    parser.add_argument("--limit-windows", type=int, default=None, help="Limit number of advance purchase windows")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from last checkpoint")
    parser.add_argument("--delay", type=float, default=0.2, help="Pacing delay between requests in seconds")
    parser.add_argument("--source", type=str, default="yatra", help="Target source adapter")

    args = parser.parse_args()

    if args.discover_routes:
        logger.info("Discovering Indian domestic routes...")
        rd = RouteDiscovery(source_name=args.source)
        catalog = rd.generate_full_domestic_catalog()
        rd.export_catalog(catalog)

    if args.run_bulk:
        run_bulk_collection(
            limit_routes=args.limit_routes,
            limit_windows=args.limit_windows,
            resume=args.resume,
            delay_seconds=args.delay,
            source=args.source
        )


if __name__ == "__main__":
    main()
