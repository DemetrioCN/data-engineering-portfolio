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

    log.info(f"Load customer and materials master")
    # Extract: customer and material masters
    df_customer, products_id = extract()

    # Transforms
    df_orders = transform(df_customer, products_id, date)

    # Load
    load(df_orders, date)
    log.info(f"Visit list generator complete succesfully!!! ")


if __name__ == "__main__":
    sys.exit(visit_list_generator())