import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from model import VisitEvent
from config import VISIT_LIST_SCHEMA

log = logging.getLogger(__name__)


# ─── CSV ──────────────────────────────────────────────────────────────────────

def load_latest_csv(input_dir: Path) -> pd.DataFrame:
    """Load the most recent CSV found inside input_dir."""
    files = sorted(input_dir.rglob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")
    last_file = files[-1]
    log.info("Loading CSV: %s", last_file)
    return pd.read_csv(last_file, dtype=VISIT_LIST_SCHEMA)


# ─── Caché ────────────────────────────────────────────────────────────────────

def get_cache_path(cache_dir: Path, process_date: datetime) -> Path:
    """
    Build cache file path for this execution.
    Pattern: year=YYYY/month=MM/day=DD/YYYYMMDD_N_visit_list.json
    """
    partition = cache_dir / f"year={process_date.year}" / f"month={process_date.month:02d}" / f"day={process_date.day:02d}"
    partition.mkdir(parents=True, exist_ok=True)

    date_prefix = process_date.strftime("%Y%m%d")
    existing    = sorted(partition.glob(f"{date_prefix}_*_visit_list.json"), 
                         key=lambda f: int(f.stem.split("_")[1]) # Order by N, noy alphabetically
                         )
    next_number = len(existing) + 1

    return partition / f"{date_prefix}_{next_number}_visit_list.json"


def load_cache(cache_dir: Path, process_date: datetime) -> dict:
    """
    Load the most recent cache file for process_date.
    Returns empty dict if none exists (first run of the day).
    """
    date_prefix = process_date.strftime("%Y%m%d")
    partition = cache_dir / f"year={process_date.year}" / f"month={process_date.month:02d}" / f"day={process_date.day:02d}"
    files       = sorted(
                    partition.glob(f"{date_prefix}_*_visit_list.json"),
                    key=lambda f: int(f.stem.split("_")[1]) # Order by N, noy alphabetically
                    )

    if not files:
        log.info("No cache found for %s - starting fresh.", date_prefix)
        return {}

    latest = files[-1]
    log.info("Loading cache: %s", latest)

    with open(latest, "r") as f:
        data = json.load(f)

    return {
        route_id: (
            v["sequence"],
            datetime.fromisoformat(v["last_departure_time"]),
        )
        for route_id, v in data.items()
    }


def write_cache(cache_dir: Path, cache_data: dict, process_date: datetime):
    """Write a new cache file for this execution with the state of all routes."""
    cache_path = get_cache_path(cache_dir, process_date)

    with open(cache_path, "w") as f:
        json.dump(cache_data, f, indent=2)

    log.info("Cache written: %s", cache_path)


# ─── Eventos ──────────────────────────────────────────────────────────────────

def write_events(events: list[VisitEvent], output_path: Path, process_date: datetime):
    """
    Write all events from this execution into a single JSON file.
    Pattern: year=YYYY/month=MM/day=DD/YYYYMMDD_N_visit_events.json
    """
    if not events:
        log.warning("No events to write.")
        return

    partition = output_path / f"year={process_date.year}" / f"month={process_date.month:02d}" / f"day={process_date.day:02d}"
    partition.mkdir(parents=True, exist_ok=True)

    date_prefix = process_date.strftime("%Y%m%d")
    existing    = sorted(partition.glob(f"{date_prefix}_*_visit_events.json"),
                         key=lambda f: int(f.stem.split("_")[1]) # Order by N, noy alphabetically
                         )
    next_number = len(existing) + 1

    filepath = partition / f"{date_prefix}_{next_number}_visit_events.json"
    payload  = [json.loads(event.model_dump_json()) for event in events]

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log.info("Events written: %s (%s events)", filepath, len(events))