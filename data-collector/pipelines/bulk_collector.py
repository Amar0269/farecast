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
from pipelines.collect import load_config

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


def validate_dataset_integrity(dataset: List[FareObservation], catalog: List[Dict[str, Any]]) -> bool:
    """
    Validates production dataset integrity.
    Fails if:
    - route does not match origin-destination
    - route not in catalog
    - DEL-BOM observations copied into another route
    """
    valid_routes = {item["route"] for item in catalog}

    for obs in dataset:
        expected_route = f"{obs.origin}-{obs.destination}"
        if obs.route != expected_route:
            raise ValueError(f"Integrity check failed: observation route {obs.route} != {expected_route}")

        if obs.route not in valid_routes:
            raise ValueError(f"Integrity check failed: route {obs.route} not in route catalog")

    logger.info("Dataset Integrity Check Passed Successfully.")
    return True


def run_bulk_collection(
    limit_routes: Optional[int] = None,
    limit_windows: Optional[int] = None,
    resume: bool = True,
    delay_seconds: float = 2.0,
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

    config = load_config()
    advance_days = config.get("advance_purchase_days", [1, 7, 15, 30, 45])

    if limit_windows:
        advance_days = advance_days[:limit_windows]

    checkpoint_state = CheckpointManager.load_checkpoint() if resume else {"completed_searches": []}
    completed_keys: Set[str] = set(checkpoint_state.get("completed_searches", []))

    # Load existing production dataset to prevent data loss or duplication
    existing_observations = load_existing_production_observations()
    collected_new_observations: List[FareObservation] = []

    yatra_adapter = YatraSource(config.get("source_settings", {}).get("yatra", {}))

    searches_attempted = 0
    successful_searches = 0
    blocked_searches = 0
    failed_searches = 0
    no_result_searches = 0

    per_search_records: List[Dict[str, Any]] = []
    routes_successful: Set[str] = set()
    routes_attempted: Set[str] = set()

    theoretical_searches = len(catalog) * len(advance_days)
    logger.info(f"Starting bulk collection on {len(catalog)} routes and {len(advance_days)} windows ({theoretical_searches} theoretical searches)...")

    for item in catalog:
        orig = item["origin_code"]
        dest = item["destination_code"]
        route_str = item["route"]
        routes_attempted.add(route_str)

        windows = calculate_travel_dates(start_time, advance_days)

        for win in windows:
            t_date = win["travel_date"]
            win_str = win["window"]
            lead_days = win["advance_days"]
            search_key = f"{source}|{orig}|{dest}|{t_date}|{win_str}"
            search_url = yatra_adapter._build_search_url(orig, dest, t_date)

            if resume and search_key in completed_keys:
                logger.info(f"[SKIPPED] Search already completed: {search_key}")
                continue

            searches_attempted += 1
            logger.info(f"[MATRIX] route={route_str} window={win_str} travel_date={t_date} url={search_url}")

            scrape_res = yatra_adapter.search(origin=orig, destination=dest, travel_date=t_date)
            obs_count = 0

            if scrape_res.status == CollectionStatus.SUCCESS and scrape_res.observations:
                successful_searches += 1
                obs_count = len(scrape_res.observations)
                routes_successful.add(route_str)
                logger.info(f"[SUCCESS] Collected {obs_count} observations for {route_str} on {t_date} ({win_str}).")

                for obs in scrape_res.observations:
                    cleaned_obs = DataCleaner.clean_observation(
                        obs,
                        collection_date_override=scrape_res.collection_timestamp
                    )
                    cleaned_obs.advance_purchase_days = lead_days
                    cleaned_obs.advance_purchase_window = win_str
                    cleaned_obs.update_missing_fields()
                    collected_new_observations.append(cleaned_obs)

            elif scrape_res.status == CollectionStatus.SOURCE_BLOCKED:
                blocked_searches += 1
                logger.warning(f"[BLOCKED] Search blocked for {route_str} on {t_date} ({win_str}).")
            elif scrape_res.status == CollectionStatus.NO_RESULTS:
                no_result_searches += 1
                logger.info(f"[NO_RESULTS] Zero flights returned for {route_str} on {t_date} ({win_str}).")
            else:
                failed_searches += 1
                logger.error(f"[FAILED] Search failed for {route_str} on {t_date} ({win_str}): {scrape_res.error_message}")

            per_search_records.append({
                "route": route_str,
                "origin": orig,
                "destination": dest,
                "travel_date": t_date,
                "advance_purchase_days": lead_days,
                "advance_purchase_window": win_str,
                "status": scrape_res.status.value,
                "observation_count": obs_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            CheckpointManager.save_checkpoint(search_key)
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    # Combine existing historical observations with newly collected observations
    all_combined = existing_observations + collected_new_observations
    cleaned_all = [DataCleaner.clean_observation(o) for o in all_combined]
    deduped_all = DataValidator.deduplicate(cleaned_all)
    final_dataset = DataValidator.flag_outliers(deduped_all)

    # Perform strict dataset integrity check
    validate_dataset_integrity(final_dataset, catalog)

    # Export merged production dataset
    export_processed_data("data/processed", final_dataset)

    end_time = datetime.now(timezone.utc)
    duplicate_count = sum(1 for obs in final_dataset if obs.duplicate_flag)
    outlier_count = sum(1 for obs in final_dataset if obs.outlier_flag)

    # Lead-time totals across final production dataset
    lead_time_totals = {
        "T+1": sum(1 for o in final_dataset if o.advance_purchase_window == "T+1"),
        "T+7": sum(1 for o in final_dataset if o.advance_purchase_window == "T+7"),
        "T+15": sum(1 for o in final_dataset if o.advance_purchase_window == "T+15"),
        "T+30": sum(1 for o in final_dataset if o.advance_purchase_window == "T+30"),
        "T+45": sum(1 for o in final_dataset if o.advance_purchase_window == "T+45"),
    }

    manifest_data = {
        "run_id": run_id,
        "collection_timestamps": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        "sources": [source],
        "route_count": len(catalog),
        "window_count": len(advance_days),
        "theoretical_search_count": theoretical_searches,
        "searches_attempted": searches_attempted,
        "successful_searches": successful_searches,
        "blocked_searches": blocked_searches,
        "failed_searches": failed_searches,
        "no_result_searches": no_result_searches,
        "routes_attempted": len(routes_attempted),
        "routes_successful": len(routes_successful),
        "routes_zero_successful": len(catalog) - len(routes_successful),
        "total_real_observations_collected": len(final_dataset),
        "duplicate_count": duplicate_count,
        "outlier_count": outlier_count,
        "lead_time_totals": lead_time_totals,
        "per_search_records": per_search_records
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
    parser.add_argument("--delay", type=float, default=2.0, help="Pacing delay between requests in seconds")
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
