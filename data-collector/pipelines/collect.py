"""
Main Data Collection & Cleaning Pipeline (Member 1 - SIH26056).
Orchestrates collection, raw preservation, normalization, validation, deduplication, and export.
"""

import os
import json
import csv
import logging
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import yaml

from models.fare import FareObservation, CollectionStatus
from scrapers.base import ScrapeResult
from scrapers.indigo import IndigoSource
from scrapers.easemytrip import EaseMyTripSource
from scrapers.ixigo import IxigoSource
from scrapers.yatra import YatraSource
from scrapers.airindia import AirIndiaSource
from scrapers.airindiaexpress import AirIndiaExpressSource
from scrapers.akasa import AkasaSource
from scrapers.spicejet import SpiceJetSource
from scrapers.cleartrip import CleartripSource
from scrapers.goibibo import GoibiboSource
from scrapers.makemytrip import MakeMyTripSource
from processors.cleaner import DataCleaner
from processors.validator import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("AirfarePipeline")


def load_config(config_path: str = "config/routes.yaml") -> Dict[str, Any]:
    """Loads route and source configuration from YAML."""
    if not os.path.exists(config_path):
        logger.warning(f"Config file {config_path} not found. Using default config.")
        return {
            "routes": [],
            "advance_purchase_days": [1, 7, 15, 30, 45],
            "sources": ["yatra"]
        }
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def calculate_travel_dates(
    collection_date: datetime,
    advance_days: List[int]
) -> List[Dict[str, Any]]:
    """Calculates future travel dates given advance purchase windows."""
    window_dates = []
    for d in advance_days:
        t_date = collection_date + timedelta(days=d)
        window_dates.append({
            "advance_days": d,
            "window": f"T+{d}",
            "travel_date": t_date.strftime("%Y-%m-%d")
        })
    return window_dates


def preserve_raw_data(
    raw_dir: str,
    scrape_result: ScrapeResult
) -> str:
    """
    Preserves raw data response to data/raw/ directory without overwriting.
    Creates structured JSON artifact containing metadata and raw HTML payload.
    """
    os.makedirs(raw_dir, exist_ok=True)
    ts_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{scrape_result.source}_{scrape_result.origin}_{scrape_result.destination}_{scrape_result.travel_date}_{ts_slug}.json"
    filepath = os.path.join(raw_dir, filename)

    raw_export = {
        "metadata": {
            "source": scrape_result.source,
            "origin": scrape_result.origin,
            "destination": scrape_result.destination,
            "travel_date": scrape_result.travel_date,
            "collection_timestamp": scrape_result.collection_timestamp,
            "status": scrape_result.status.value,
            "observation_count": len(scrape_result.observations),
            "error_message": scrape_result.error_message
        },
        "raw_payload": scrape_result.raw_payload
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(raw_export, f, indent=2)

    logger.info(f"Raw data preserved: {filepath}")
    return filepath


def export_processed_data(
    processed_dir: str,
    observations: List[FareObservation],
    export_prefix: str = "airfare_observations"
) -> Dict[str, str]:
    """Exports processed observations to standardized CSV and JSON datasets."""
    os.makedirs(processed_dir, exist_ok=True)
    date_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    # Standard primary dataset files required by Member 2 / backend
    std_csv_path = os.path.join(processed_dir, "airfare_observations.csv")
    std_json_path = os.path.join(processed_dir, "airfare_observations.json")
    
    # Timestamped archive files
    archive_csv_path = os.path.join(processed_dir, f"{export_prefix}_{date_slug}.csv")
    archive_json_path = os.path.join(processed_dir, f"{export_prefix}_{date_slug}.json")

    schema_fields = list(FareObservation.model_fields.keys())

    # Write primary CSV
    for path in (std_csv_path, archive_csv_path):
        write_header = not os.path.exists(path) or os.path.getsize(path) == 0
        with open(path, "w" if write_header else "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=schema_fields)
            if write_header:
                writer.writeheader()
            for obs in observations:
                writer.writerow(obs.to_csv_dict())

    # Write primary JSON
    json_records = [obs.model_dump() for obs in observations]
    for path in (std_json_path, archive_json_path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(json_records, f, indent=2)

    logger.info(f"Clean processed dataset exported: CSV={std_csv_path}, JSON={std_json_path}")
    return {"csv": std_csv_path, "json": std_json_path}


def collect_fares(
    source: str = "yatra",
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    travel_date: Optional[str] = None,
    raw_dir: str = "data/raw",
    processed_dir: str = "data/processed"
) -> List[FareObservation]:
    """
    Main collection routine for a single route & date query.
    1. Instantiates appropriate source adapter
    2. Runs search
    3. Preserves raw response
    4. Normalizes & cleans observations
    5. Deduplicates within source
    6. Flags price outliers
    7. Exports CSV/JSON
    """
    if not travel_date:
        raise ValueError("travel date must be provided explicitly")

    src_lower = source.lower()
    if src_lower == "indigo":
        adapter = IndigoSource()
    elif src_lower == "easemytrip":
        adapter = EaseMyTripSource()
        raw_dir = os.path.join(raw_dir, "easemytrip")
    elif src_lower == "ixigo":
        adapter = IxigoSource()
        raw_dir = os.path.join(raw_dir, "ixigo")
    elif src_lower == "yatra":
        adapter = YatraSource()
        raw_dir = os.path.join(raw_dir, "yatra")
    elif src_lower == "airindia":
        adapter = AirIndiaSource()
        raw_dir = os.path.join(raw_dir, "airindia")
    elif src_lower in ("airindiaexpress", "air_india_express"):
        adapter = AirIndiaExpressSource()
        raw_dir = os.path.join(raw_dir, "airindiaexpress")
    elif src_lower in ("akasa", "akasaair"):
        adapter = AkasaSource()
        raw_dir = os.path.join(raw_dir, "akasa")
    elif src_lower == "spicejet":
        adapter = SpiceJetSource()
        raw_dir = os.path.join(raw_dir, "spicejet")
    elif src_lower == "cleartrip":
        adapter = CleartripSource()
        raw_dir = os.path.join(raw_dir, "cleartrip")
    elif src_lower == "goibibo":
        adapter = GoibiboSource()
        raw_dir = os.path.join(raw_dir, "goibibo")
    elif src_lower in ("makemytrip", "mmt"):
        adapter = MakeMyTripSource()
        raw_dir = os.path.join(raw_dir, "makemytrip")
    else:
        logger.error(f"Source adapter '{source}' is not implemented yet.")
        return []

    result = adapter.search(origin=origin, destination=destination, travel_date=travel_date)

    preserve_raw_data(raw_dir, result)

    if result.status != CollectionStatus.SUCCESS or not result.observations:
        logger.warning(f"Collection for {source} {origin}->{destination} on {travel_date} ended with status: {result.status.value}")
        return []

    cleaned_observations = []
    for obs in result.observations:
        cleaned_obs = DataCleaner.clean_observation(obs)
        cleaned_observations.append(cleaned_obs)

    deduped_observations = DataValidator.deduplicate(cleaned_observations)
    final_observations = DataValidator.flag_outliers(deduped_observations)

    export_processed_data(processed_dir, final_observations)

    logger.info(f"Successfully processed {len(final_observations)} observations for {origin}->{destination}")
    return final_observations


def run_matrix_collection(config_path: str = "config/routes.yaml", target_source: Optional[str] = None) -> List[FareObservation]:
    """
    Executes collection across all routes and advance purchase windows configured in routes.yaml.
    Generates a comprehensive collection summary manifest file in data/processed/collection_runs/.
    """
    start_time = datetime.now(timezone.utc)
    run_id = f"run_{start_time.strftime('%Y%m%d_%H%M%S')}"

    config = load_config(config_path)
    routes = config.get("routes", [])
    advance_days = config.get("advance_purchase_days", [1, 7, 15, 30, 45])
    sources = [target_source] if target_source else config.get("sources", ["yatra"])

    all_observations: List[FareObservation] = []

    per_route_counts = {f"{r['origin']}-{r['destination']}": 0 for r in routes}
    per_window_counts = {f"T+{d}": 0 for d in advance_days}
    per_source_counts = {src: 0 for src in sources}

    searches_attempted = 0
    successful_searches = 0
    blocked_searches = 0
    failed_searches = 0
    no_result_searches = 0

    for src in sources:
        for route in routes:
            orig = route["origin"]
            dest = route["destination"]
            route_str = f"{orig}-{dest}"
            windows = calculate_travel_dates(start_time, advance_days)

            for win in windows:
                t_date = win["travel_date"]
                win_str = win["window"]
                searches_attempted += 1

                obs_list = collect_fares(
                    source=src,
                    origin=orig,
                    destination=dest,
                    travel_date=t_date
                )

                if obs_list:
                    successful_searches += 1
                    all_observations.extend(obs_list)
                    count = len(obs_list)
                    per_route_counts[route_str] = per_route_counts.get(route_str, 0) + count
                    per_window_counts[win_str] = per_window_counts.get(win_str, 0) + count
                    per_source_counts[src] = per_source_counts.get(src, 0) + count
                else:
                    blocked_searches += 1

    end_time = datetime.now(timezone.utc)

    # Post-process all collected observations (deduplicate across full matrix & flag outliers)
    cleaned_matrix = [DataCleaner.clean_observation(obs) for obs in all_observations]
    deduped_matrix = DataValidator.deduplicate(cleaned_matrix)
    final_matrix = DataValidator.flag_outliers(deduped_matrix)

    duplicate_count = sum(1 for obs in final_matrix if obs.duplicate_flag)
    outlier_count = sum(1 for obs in final_matrix if obs.outlier_flag)

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
        "total_real_observations_collected": len(final_matrix),
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

    # Also update primary processed dataset
    export_processed_data("data/processed", final_matrix)

    logger.info(f"Matrix collection completed. Manifest saved to {manifest_path}")
    logger.info(f"Total Observations Collected: {len(final_matrix)}")
    return final_matrix


def main():
    parser = argparse.ArgumentParser(description="MoSPI Airfare Price Index Data Collector")
    parser.add_argument("--source", type=str, default="yatra", help="Target source (e.g. indigo, yatra, easemytrip)")
    parser.add_argument("--origin", type=str, default=None, help="Origin IATA code")
    parser.add_argument("--destination", type=str, default=None, help="Destination IATA code")
    parser.add_argument("--travel-date", type=str, default=None, help="Travel date YYYY-MM-DD")
    parser.add_argument("--config", type=str, default="config/routes.yaml", help="Path to config file")
    parser.add_argument("--run-matrix", action="store_true", help="Run matrix collection across all routes and advance purchase dates")

    args = parser.parse_args()

    if args.run_matrix:
        run_matrix_collection(config_path=args.config, target_source=args.source if args.source != "indigo" else None)
    else:
        collect_fares(
            source=args.source,
            origin=args.origin,
            destination=args.destination,
            travel_date=args.travel_date
        )


if __name__ == "__main__":
    main()
