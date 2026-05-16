"""
Enrich step – adds derived columns to the raw locations DataFrame.

Transformations applied in this step:
    1. Reverse-geocode lat/lon  →  city, state
    2. Assign warehouse region  →  warehouse_id  (based on state)
    3. Generate unique client IDs  →  customer_id
    4. Assign loyalty segment   →  segment  (bronze / silver / gold)
    5. Add geofence radius      →  geofence_radius_m
"""

import logging
import random
import string
import pandas as pd
from config.customer_params import GEOFENCE_RADIUS_M, SEGMENT_DISTRIBUTION
from utils.geo import add_city_and_state
from model.warehouse_clustering import run_clustering as _assign_region

logger = logging.getLogger(__name__)


def _generate_customer_ids(df_len: int) -> list[str]:
    """Return n unique 10-digit strings, each starting with '0'."""
    ids: set[str] = set()
    while len(ids) < df_len:
        suffix = "".join(random.choices(string.digits, k=9))
        ids.add("0" + suffix)
    return list(ids)


def _assign_segments(df_len: int) -> list[str]:
    """Return a shuffled list of segment labels respecting the configured distribution."""
    dist     = SEGMENT_DISTRIBUTION
    n_bronze = round(df_len * dist["bronze"])
    n_silver = round(df_len * dist["silver"])
    n_gold   = df_len - n_bronze - n_silver

    segments = ["bronze"] * n_bronze + ["silver"] * n_silver + ["gold"] * n_gold
    random.shuffle(segments)
    return segments


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all enrichment transformations and return the augmented DataFrame.
    """
    if df.empty:
        logger.warning("Transformer received an empty DataFrame – skipping.")
        return df

    logger.info("Reverse-geocoding %d locations…", len(df))
    df = add_city_and_state(df, lat_col="lat", lon_col="lon")

    logger.info("Generating client IDs…")
    df = df.copy()
    df["customer_id"] = _generate_customer_ids(len(df))

    logger.info("Assigning loyalty segments…")
    df["segment"] = _assign_segments(len(df))

    logger.info("Assigning warehouse regions…")
    df, df_warehouses = _assign_region(
                                df=df,
                                output_dir="data/output/clustering/",
                                save_plot=True)

    df["geofence_radius_m"] = GEOFENCE_RADIUS_M
    logger.info("Transform complete. DF size: %d", len(df))
    return df
