import pandas as pd
from pathlib import Path
from config.visit_list_params import INPUT_CUSTOMERS, INPUT_PRODUCTS

def get_latest_file(folder: Path, pattern = "*.csv") -> Path:
    """Return the most recent file in a folder based on the YYYYMMDD prefix.
    """
    files = sorted(folder.glob(pattern), reverse=True)

    if not files:
        raise FileNotFoundError(f"No files found in '{folder}' matching '{pattern}'")
    return files[0]

def load_customers(path: Path) -> pd.DataFrame:
    """ Load customer master and select only neccesary columns """
    
    latest_file = get_latest_file(path)
    df = pd.read_csv(latest_file, dtype={"customer_id": "string", "warehouse_code":"string"})
    return df[['warehouse_code', 'customer_id']]

def load_products(path: Path) -> list:
    """ Load material master and select only active products """
    latest_file = get_latest_file(path)
    df = pd.read_csv(latest_file)
    products = df.loc[df['is_active'], 'product_id'].tolist() 
    return products

def extract() -> tuple[pd.DataFrame, list]:
    df_customer = load_customers(INPUT_CUSTOMERS)
    products_id = load_products(INPUT_PRODUCTS)

    return df_customer, products_id