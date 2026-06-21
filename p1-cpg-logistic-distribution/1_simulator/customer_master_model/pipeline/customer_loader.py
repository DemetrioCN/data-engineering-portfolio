"""
Load step – persists the enriched DataFrame to file
"""

import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
from config.customers_params import OUTPUT_DIR, OUTPUT_FORMAT

logger = logging.getLogger(__name__)


def load(
    df: pd.DataFrame,
    filename: str,
    output_dir: str | Path = OUTPUT_DIR,
    fmt: str = OUTPUT_FORMAT
) -> Path:
    """Write df to output_dir.
    """
    if fmt not in {"csv"}:
        raise ValueError(f"Unsupported output format '{fmt}'. Use 'csv'")

    output_dir.mkdir(parents=True, exist_ok=True)

    filename  = f"{filename}.{fmt}"
    out_path  = output_dir / filename

    df.to_csv(out_path, index=False, encoding="utf-8")

    logger.info("Saved %d rows → %s", len(df), out_path.resolve())
    return out_path
