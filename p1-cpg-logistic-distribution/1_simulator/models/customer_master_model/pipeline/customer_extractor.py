"""
Extract step – fetches raw store locations from the Overpass API.
"""

import logging
import time
import pandas as pd
from config.customers_params import SLEEP_BETWEEN_BRANDS
from utils.http_client import post_overpass_query

logger = logging.getLogger(__name__)

# Overpass query template – searches nodes by wikidata_id inside the administrative boundary of the given country.
# Return the result in JSON in maximum 60 seconds. 
_QUERY_TEMPLATE =  """
    [out:json][timeout:60];
    area["name"="{country}"]["admin_level"="2"];
    (
    way["brand:wikidata"="{wikidata_id}"](area);
    );
    out center body;
    """


def _parse_elements(data: dict, brand_name: str) -> list[dict]:
    """Extract relevant fields from a raw Overpass response dict."""
    records: list[dict] = []

    for element in data.get("elements", []):
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")

        if not lat or not lon:
            continue

        tags = element.get("tags", {})
        records.append({
            "name":            tags.get("name", ""),
            "brand":           tags.get("brand", ""),
            "opening_hours":   tags.get("opening_hours", ""),
            "lat":             lat,
            "lon":             lon,
        })

    return records


def extract(brands: list[str], country: str = "México") -> pd.DataFrame:
    """Query Overpass for every brand and return a DataFrame.
    """
    all_records = []
    failed_brands = []

    for brand, qid in brands.items():
        logger.info("Extracting: %s…", brand)
        query = _QUERY_TEMPLATE.format(country=country, wikidata_id=qid )
        data  = post_overpass_query(query)

        if data is None:
            logger.error("  → API failed for '%s' after all retries.", brand)
            failed_brands.append(brand)
        elif data.get("elements"):
            records = _parse_elements(data, brand)
            all_records.extend(records)
            logger.info("  → %d locations found for '%s'.", len(records), brand)
        else:
            logger.info("  → Query succeeded but no stores found for '%s'.", brand)

        time.sleep(SLEEP_BETWEEN_BRANDS)

    if failed_brands:
        logger.warning("Brands with failed extraction: %s", failed_brands)

    df = pd.DataFrame(all_records)

    if df.empty:
        logger.warning("Extraction returned no data.")
        return df

    df = df.drop_duplicates(subset=["lat", "lon"]).reset_index(drop=True)
    logger.info("Extracted %d rows with %d columns", len(df), len(df.columns))
    return df
