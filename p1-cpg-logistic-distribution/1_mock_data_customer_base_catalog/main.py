"""
Generator for mock data to create a base client catalog classify by loyalty.
"""

import logging
from config.settings import BRANDS, OUTPUT_DIR, OUTPUT_FORMAT
from pipeline.extractor import extract
from pipeline.transformer import transform
from pipeline.loader import load

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run() -> int:
    """Execute the full ETL pipeline. Returns 0 on success, 1 on failure."""
    logger.info("═" * 60)

    # Extract
    df_raw = extract(brands=BRANDS)
    if df_raw.empty:
        logger.error("Extraction returned no data. Aborting pipeline.")
        return 1

    # Transform
    df_transformed = transform(df_raw)

    # Load
    out_path = load(df_transformed, output_dir=OUTPUT_DIR, fmt=OUTPUT_FORMAT)
    logger.info("Done → %s", out_path)
    return 0


if __name__ == "__main__":
    run()
