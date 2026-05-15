"""
Geo helpers used by the enricher step with city and state from coordinate
"""

import pandas as pd
import reverse_geocoder as rg


def add_city_and_state(df: pd.DataFrame, lat_col: str, lon_col: str) -> pd.DataFrame:
    """Reverse-geocode lat/lon and append city and state columns.
    """
    coords = list(zip(df[lat_col], df[lon_col]))
    results = rg.search(coords)
    df = df.copy()
    df["city"]  = [r["name"]   for r in results]
    df["state"] = [r["admin1"] for r in results]
    return df