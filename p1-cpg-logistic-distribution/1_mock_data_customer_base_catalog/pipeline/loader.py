"""
Load step – persists the enriched DataFrame to file
"""

import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
from config.settings import OUTPUT_DIR, OUTPUT_FORMAT

logger = logging.getLogger(__name__)


def load(
    df: pd.DataFrame,
    output_dir: str | Path = OUTPUT_DIR,
    fmt: str = OUTPUT_FORMAT,
) -> Path:
    """Write df to output_dir.
    """
    if fmt not in {"csv"}:
        raise ValueError(f"Unsupported output format '{fmt}'. Use 'csv'")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"customer_base_{timestamp}.{fmt}"
    out_path  = out_dir / filename

    df.to_csv(out_path, index=False, encoding="utf-8")

    logger.info("Saved %d rows → %s", len(df), out_path.resolve())
    return out_path
