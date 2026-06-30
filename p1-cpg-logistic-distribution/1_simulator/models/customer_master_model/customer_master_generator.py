"""
Generator for mock data to create a base client catalog classify by loyalty.
"""

import logging
from config.customers_params import BRANDS, OUTPUT_DIR, OUTPUT_FORMAT
from pipeline.customer_extractor import extract
from pipeline.customer_transformer import transform
from pipeline.customer_loader import load
from datetime import datetime
import sys


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_customer_master() -> int:
    """Execute the full ETL pipeline. Returns 0 on success, 1 on failure."""
    logger.info("Starting CUSTOMER MASTER pipeline")

    # Extract
    df_raw = extract(brands=BRANDS)
    if df_raw.empty:
        logger.error("Extraction returned no data. Aborting pipeline.")
        return 1

    # Transform
    try:
        df_transformed, df_warehouse = transform(df_raw)
    except Exception as e:
        logger.error("Transform failed: %s", e)
        return 1

    if df_transformed.empty or df_warehouse.empty:
        logger.error("Transform returned empty data. Aborting pipeline.")
        return 1

    today    = datetime.now()
    date_str = today.strftime("%Y%m%d")

    # Load
    try:
        customer_out_path = load(df_transformed, filename=f'{date_str}_customer_master', output_dir=OUTPUT_DIR / "customer_master", fmt=OUTPUT_FORMAT)
        warehouse_out_path = load(df_warehouse, filename=f'{date_str}_warehouse_master', output_dir=OUTPUT_DIR / "warehouse_master", fmt=OUTPUT_FORMAT)
    except Exception as e:
        logger.error("Load failed: %s", e)
        return 1

    logger.info("Done → %s | %s", customer_out_path, warehouse_out_path)
    return 0


if __name__ == "__main__":
    sys.exit(run_customer_master())
