import pandas as pd
import random
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s — %(message)s')
log = logging.getLogger(__name__)


BASE_PATH = Path('../1_mock_data_catalog_generator/data/')

INPUT_CUSTOMERS = BASE_PATH / 'output/clustering/customer_warehouse_assignment.csv'
INPUT_PRODUCTS  = BASE_PATH / 'output/material_master/material_master.csv'
OUTPUT_PATH     = BASE_PATH / 'output/orders'


### --- FUNCTIONS ------------
def load_customers(path: Path) -> pd.DataFrame:
    """ Load customer master and select only neccesary columns """

    df = pd.read_csv(path)
    df['warehouse_id'] = df['warehouse'].str.split(' · ').str[0]
    return df[['warehouse_id', 'customer_id']]

def load_products(path: Path) -> list:
    """ Load material master and select only active products """

    df = pd.read_csv(path)
    products = df.loc[df['is_active'], 'product_id'].tolist() 
    return products

def sample_customers(df: pd.DataFrame) -> pd.DataFrame:
    """ For each DF (only one warehouse_id) select randomly n customers"""

    n = min(random.choice([20, 25, 30, 35, 40]), len(df))
    return df.sample(n=n)

def generate_order_ids(n_clients: int, date_str: str) -> list:
    """Generate order_id randomly for each customer: date in string + a 4 digit num"""

    nums = random.sample(range(10000, 99999), k=n_clients)
    return [int(f"{date_str}{num}") for num in nums]

def generate_route_map(warehouses: list, date_str: str) -> dict:
    """Generate an route id for each warehouse, unique for each day"""
    return {
        wh: f"R-{date_str}-{random.randint(10, 99)}"
        for wh in warehouses
    }


def assign_customer_products(row: pd.Series, products_id: list) -> pd.DataFrame:
    """Assign for each customer N materias with n quantities"""

    # Select randomly n products for each clients
    n = random.randint(1, len(products_id))
    selected = random.sample(products_id, k=n)

    # Select randomly quantities for each product
    quantities = [random.choice(range(5, 51, 5)) for _ in selected]

    return pd.DataFrame({
        'date'        : row['date'],
        'warehouse_id': row['warehouse_id'],
        'customer_id' : row['customer_id'],
        'order_id'    : row['order_id'],
        'route_id'    : row['route_id'],
        'product_id'  : selected,
        'quantity'    : quantities
    })


def build_orders(df_samples: pd.DataFrame, products_id: list) -> pd.DataFrame:
    """Join every customer with products and qunatities and return a complete DF"""

    df_orders = pd.DataFrame()

    for _, row in df_samples.iterrows():
        df_ = assign_customer_products(row, products_id)
        df_orders = pd.concat([df_orders, df_], ignore_index=True)

    return df_orders

def visit_list_generator():
    """
    Daily Visit List Generator.

    Generates a randomized daily visit list for each warehouse by:
        1. Sampling N random customers per warehouse from the master data.
        2. Assigning a random selection of products with random quantities to each sampled customer.
        3. Merging both datasets and exporting the result as a CSV file.
    """
    today    = datetime.now()
    date_str = today.strftime("%Y%m%d")

    log.info(f"---- Starting visit list pipe: {today} ----- ")

    log.info(f"Load customer and materials master")
    # Load: customer and material masters
    df_customer   = load_customers(INPUT_CUSTOMERS)
    products_id = load_products(INPUT_PRODUCTS)

    # Sample customer by warehouse for order day
    df_samples = (
        df_customer
        .groupby('warehouse_id')
        .apply(sample_customers, include_groups=False)
        .reset_index(level=0)
        .reset_index(drop=True)
    )
    df_samples['date']     = today
    df_samples['order_id'] = generate_order_ids(len(df_samples), date_str)
    df_samples['route_id'] = df_samples['warehouse_id'].map(
        generate_route_map(df_samples['warehouse_id'].unique(), date_str)
    )

    # Join customer and products
    log.info(f"Generate orders")
    df_orders = build_orders(df_samples, products_id)
    log.info(f"Visit list generator complete succesfully!!! ")