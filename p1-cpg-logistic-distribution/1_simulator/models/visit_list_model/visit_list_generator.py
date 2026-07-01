from datetime import datetime
import logging
import sys

from pipeline.extract import extract
from pipeline.transform import transform
from pipeline.load import load

logging.basicConfig(level=logging.INFO, format='%(asctime)s — %(message)s')
log = logging.getLogger(__name__)

def visit_list_generator():
    """
    Daily Visit List Generator.

    Generates a randomized daily visit list for each warehouse by:
        1. Sampling N random customers per warehouse from the master data.
        2. Assigning a random selection of products with random quantities to each sampled customer.
        3. Merging both datasets and exporting the result as a CSV file.
    """
    date    = datetime.now()
    
    log.info(f"---- Starting visit list pipe: {date} ----- ")

    # Extract: customer and material masters
    log.info(f"Load customer and materials master")
    
    try:
        df_customer, products_id = extract()
    except Exception as e:
        log.error("Extract failed: %s", e)
        return 1
    
    if df_customer.empty:
        log.error("Extract returned no customers. Aborting pipeline.")
        return 1
    
    if not products_id:
        log.error("Extract returned no products. Aborting pipeline.")
        return 1

    # Transforms
    log.info(f"Transform proccess starting")
    try:
        df_orders = transform(df_customer, products_id, date)
    except Exception as e:
        log.error("Transform returned no data. Aborting pipeline")
        return 1
    
    if df_orders.empty:
        log.error("Transform returned no data. Aborting pipeline")
        return 1
    
    # Load
    log.info(f"Load proccess starting")
    try:
        load(df_orders, date)
    except Exception as e:
        log.error("Load failed: %s", e)
        return 1
    
    log.info(f"Visit list generator complete!!!")
    return 0

if __name__ == "__main__":
    sys.exit(visit_list_generator())