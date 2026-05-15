"""Material master ETL pipeline."""

import logging
import sys
from config.materials_params import PRODUCT_CATALOG_DATA, OUTPUT_DIR, OUTPUT_FORMAT
from pipeline.material_etl import extract, transform, load


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_material_master() -> int:
    """Execute the full ETL pipeline. Returns 0 on success, 1 on failure."""
    logger.info("Starting MATERIAL MASTER pipeline")

    # Extract
    df_raw = extract(data=PRODUCT_CATALOG_DATA)
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
    sys.exit(run_material_master())
