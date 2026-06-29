"""
Complete pipeline for generate product catalog – it's very simple, for that way a simple script it's enough.
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from config.materials_params import OUTPUT_DIR, OUTPUT_FORMAT, SCHEMA

logger = logging.getLogger(__name__)


def extract(data: dict) -> pd.DataFrame:
    COLUMNS = [
        "product_id", "sku", "name", "description",
        "price", "currency", "weight_kg", "dimensions_cm",
        "is_active"]

    df = pd.DataFrame(data)

    # Check for missing expected columns
    missing = [col for col in COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Check for unexpected extra columns
    extra = [col for col in df.columns if col not in COLUMNS]
    if extra:
        logger.warning("Dropping unexpected columns: %s", extra)

    # Select and reorder to expected schema
    df = df[COLUMNS]

    logger.info("Extracted %d rows with %d columns", len(df), len(df.columns))
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:

    df = df.astype(SCHEMA)
    logger.info("Transform complete. Active products: %d", df["is_active"].sum())
    return df


def load(df: pd.DataFrame, output_dir: str | Path = OUTPUT_DIR, fmt: str = OUTPUT_FORMAT, filename="material_master") -> Path:
    """Write df to output_dir. """

    if fmt not in {"csv"}:
        raise ValueError(f"Unsupported output format '{fmt}'. Use 'csv'")

    date_str = datetime.now().strftime("%Y-%m-%d").replace('-', '') 
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path  = output_dir / f"{date_str}_{filename}.{fmt}"

    df.to_csv(out_path, index=False, encoding="utf-8")

    logger.info("Saved %d rows → %s", len(df), out_path.resolve())
    return out_path