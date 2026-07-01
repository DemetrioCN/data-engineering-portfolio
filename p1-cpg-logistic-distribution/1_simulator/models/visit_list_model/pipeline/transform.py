import pandas as pd
import random

def sample_customers(df: pd.DataFrame) -> pd.DataFrame:
    """ For each DF (only one warehouse_id) select randomly n customers"""

    n = min(random.choice([20, 25, 30, 35, 40]), len(df))
    return df.sample(n=n)

def generate_order_ids(n_clients: int, date_str: str) -> list:
    """Generate order_id randomly for each customer: date in string + a 5 digit num"""

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
        'date'           : row['date'],
        'warehouse_code' : row['warehouse_code'],
        'customer_id'    : row['customer_id'],
        'order_id'       : row['order_id'],
        'route_id'       : row['route_id'],
        'sequence'       : row['sequence'],
        'product_id'     : selected,
        'quantity'       : quantities
    })

def build_orders(df_samples: pd.DataFrame, products_id: list) -> pd.DataFrame:
    """Join every customer with products and qunatities and return a complete DF"""

    frames = [
        assign_customer_products(row, products_id)
        for _, row in df_samples.iterrows()
    ]

    return pd.concat(frames, ignore_index=True)

def transform(df_customer, products_id, today):
    date_str = today.strftime("%Y%m%d")

    # Sample customer by warehouse for order day
    df_samples = (
        df_customer
        .groupby('warehouse_code')
        .apply(sample_customers, include_groups=False)
        .reset_index(level=0)
        .reset_index(drop=True)
        )
    df_samples['date']     = today.date()
    df_samples['order_id'] = generate_order_ids(len(df_samples), date_str)
    df_samples['route_id'] = df_samples['warehouse_code'].map(
    generate_route_map(df_samples['warehouse_code'].unique(), date_str)
    )

    # Sequence per route — reindex preserves original row alignment
    df_samples['sequence'] = (
        df_samples
        .sort_values(['route_id', 'customer_id'], ascending=[True, False])
        .groupby('route_id')
        .cumcount()
        .add(1)
        .reindex(df_samples.index)
    )

    # Join customer and products
    df_orders = build_orders(df_samples, products_id)

    return df_orders