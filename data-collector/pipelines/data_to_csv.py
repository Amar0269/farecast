"""Build one M1 -> M3 CSV from the preserved Yatra raw snapshots."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


# Allows:
#   python pipelines\m1_to_m3_yatra_csv.py
# or:
#   python -m pipelines.m1_to_m3_yatra_csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from models.fare import FareObservation
from processors.cleaner import DataCleaner
from processors.validator import DataValidator
from scrapers.yatra import YatraSource


# ============================================================
# M1 VALIDATION MATRIX
# 6 routes × 5 advance-purchase windows = 30 snapshots
# ============================================================

TARGETS: Dict[Tuple[str, str, str], int] = {

    # DEL -> BOM
    ("DEL", "BOM", "2026-09-18"): 1,
    ("DEL", "BOM", "2026-09-24"): 7,
    ("DEL", "BOM", "2026-10-02"): 15,
    ("DEL", "BOM", "2026-10-17"): 30,
    ("DEL", "BOM", "2026-11-01"): 45,

    # DEL -> BLR
    ("DEL", "BLR", "2026-09-18"): 1,
    ("DEL", "BLR", "2026-09-24"): 7,
    ("DEL", "BLR", "2026-10-02"): 15,
    ("DEL", "BLR", "2026-10-17"): 30,
    ("DEL", "BLR", "2026-11-01"): 45,

    # BOM -> BLR
    ("BOM", "BLR", "2026-09-18"): 1,
    ("BOM", "BLR", "2026-09-24"): 7,
    ("BOM", "BLR", "2026-10-02"): 15,
    ("BOM", "BLR", "2026-10-17"): 30,
    ("BOM", "BLR", "2026-11-01"): 45,

    # DEL -> CCU
    ("DEL", "CCU", "2026-09-18"): 1,
    ("DEL", "CCU", "2026-09-24"): 7,
    ("DEL", "CCU", "2026-10-02"): 15,
    ("DEL", "CCU", "2026-10-17"): 30,
    ("DEL", "CCU", "2026-11-01"): 45,

    # BLR -> HYD
    ("BLR", "HYD", "2026-09-18"): 1,
    ("BLR", "HYD", "2026-09-24"): 7,
    ("BLR", "HYD", "2026-10-02"): 15,
    ("BLR", "HYD", "2026-10-17"): 30,
    ("BLR", "HYD", "2026-11-01"): 45,

    # MAA -> DEL
    ("MAA", "DEL", "2026-09-18"): 1,
    ("MAA", "DEL", "2026-09-24"): 7,
    ("MAA", "DEL", "2026-10-02"): 15,
    ("MAA", "DEL", "2026-10-17"): 30,
    ("MAA", "DEL", "2026-11-01"): 45,
}


def parse_timestamp(value: str) -> datetime:
    """Convert ISO timestamp to datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def find_latest_successful_snapshots(raw_dir: Path):
    """
    Find the latest successful raw Yatra snapshot
    for each of the 30 required route/date combinations.
    """

    latest = {}

    for path in raw_dir.glob("*.json"):

        try:
            with path.open("r", encoding="utf-8") as file:
                artifact = json.load(file)

            metadata = artifact.get("metadata", {})

            key = (
                str(metadata.get("origin", "")).upper().strip(),
                str(metadata.get("destination", "")).upper().strip(),
                str(metadata.get("travel_date", "")).strip(),
            )

            # Ignore anything outside our 30-case matrix
            if key not in TARGETS:
                continue

            # Only successful collection snapshots
            if str(metadata.get("status", "")).upper() != "SUCCESS":
                continue

            raw_payload = artifact.get("raw_payload")

            if not isinstance(raw_payload, str) or len(raw_payload) < 100:
                continue

            collection_timestamp = metadata.get("collection_timestamp")

            if not collection_timestamp:
                continue

            timestamp = parse_timestamp(str(collection_timestamp))

            previous = latest.get(key)

            if previous is None or timestamp > previous["timestamp"]:

                latest[key] = {
                    "path": path,
                    "metadata": metadata,
                    "raw_payload": raw_payload,
                    "timestamp": timestamp,
                }

        except Exception as exc:
            print(f"Skipping {path.name}: {exc}")

    return latest


def build_csv():

    # --------------------------------------------------------
    # Input/output locations
    # --------------------------------------------------------

    raw_dir = PROJECT_ROOT / "data" / "raw" / "yatra"

    output_dir = PROJECT_ROOT / "data" / "data_csv"

    output_path = output_dir / "yatra_data.csv"

    if not raw_dir.exists():
        raise SystemExit(
            f"Raw Yatra directory not found:\n{raw_dir}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Find all 30 required snapshots
    # --------------------------------------------------------

    snapshots = find_latest_successful_snapshots(raw_dir)

    missing = [
        key
        for key in TARGETS
        if key not in snapshots
    ]

    if missing:

        print("\nMISSING SUCCESSFUL YATRA SNAPSHOTS:\n")

        for origin, destination, travel_date in missing:

            days = TARGETS[
                (origin, destination, travel_date)
            ]

            print(
                f"  {origin}-{destination} "
                f"{travel_date} "
                f"T+{days}"
            )

        raise SystemExit(
            f"\nCannot create final M3 handoff.\n"
            f"Only {len(snapshots)}/30 route/date snapshots are available."
        )

    # --------------------------------------------------------
    # Use existing M1 Yatra parser
    # --------------------------------------------------------

    source = YatraSource()

    all_rows = []

    # Deterministic ordering
    ordered_targets = sorted(
        TARGETS,
        key=lambda item: (
            item[0],
            item[1],
            TARGETS[item],
            item[2],
        ),
    )

    # --------------------------------------------------------
    # Parse every one of the 30 snapshots
    # --------------------------------------------------------

    for origin, destination, travel_date in ordered_targets:

        days = TARGETS[
            (origin, destination, travel_date)
        ]

        snapshot = snapshots[
            (origin, destination, travel_date)
        ]

        metadata = snapshot["metadata"]

        print(
            f"Processing "
            f"{origin}-{destination} "
            f"{travel_date} "
            f"T+{days} ..."
        )

        # Parse the raw Yatra HTML
        observations = source.parse_html(
            snapshot["raw_payload"],
            origin,
            destination,
            travel_date,
        )

        if not observations:

            raise SystemExit(
                f"Parser produced 0 observations for "
                f"{origin}-{destination} "
                f"{travel_date} "
                f"(T+{days})."
            )

        cleaned = []

        # ----------------------------------------------------
        # Apply M1 cleaning + normalization
        # ----------------------------------------------------

        for obs in observations:

            obs.collection_timestamp = (
                metadata["collection_timestamp"]
            )

            obs.advance_purchase_days = days

            obs.advance_purchase_window = (
                f"T+{days}"
            )

            DataCleaner.clean_observation(
                obs,
                collection_date_override=(
                    metadata["collection_timestamp"]
                ),
            )

            # Explicitly preserve the intended window
            obs.advance_purchase_days = days

            obs.advance_purchase_window = (
                f"T+{days}"
            )

            cleaned.append(obs)

        # ----------------------------------------------------
        # M1 validation
        # ----------------------------------------------------

        DataValidator.deduplicate(cleaned)

        DataValidator.flag_outliers(cleaned)

        all_rows.extend(cleaned)

        print(
            f"  -> {len(cleaned)} observations"
        )

    # --------------------------------------------------------
    # CSV schema
    # --------------------------------------------------------

    fields = list(
        FareObservation.model_fields.keys()
    )

    # --------------------------------------------------------
    # Stable ordering for M3
    # --------------------------------------------------------

    all_rows.sort(
        key=lambda obs: (
            obs.origin,
            obs.destination,
            obs.advance_purchase_days
            if obs.advance_purchase_days is not None
            else 999,
            obs.airline,
            obs.flight_number,
            obs.departure_time
            or "",
            obs.total_fare
            if obs.total_fare is not None
            else float("inf"),
            obs.fare_class
            or "",
        )
    )

    # --------------------------------------------------------
    # Write one final CSV
    # --------------------------------------------------------

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()

        for obs in all_rows:

            writer.writerow(
                obs.to_csv_dict()
            )

    # --------------------------------------------------------
    # Final quality statistics
    # --------------------------------------------------------

    missing_fares = sum(
        obs.total_fare is None
        for obs in all_rows
    )

    duplicates = sum(
        obs.duplicate_flag
        for obs in all_rows
    )

    outliers = sum(
        obs.outlier_flag
        for obs in all_rows
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print("\n========================================")
    print("M1 -> M3 CSV CREATED")
    print("========================================")

    print(
        f"Route/date snapshots: 30/30"
    )

    print(
        f"Total observations:   {len(all_rows)}"
    )

    print(
        f"Missing total fares:  {missing_fares}"
    )

    print(
        f"Duplicate flags:      {duplicates}"
    )

    print(
        f"Outlier flags:        {outliers}"
    )

    print(
        f"CSV:                  {output_path}"
    )

    print("========================================")


if __name__ == "__main__":
    build_csv()