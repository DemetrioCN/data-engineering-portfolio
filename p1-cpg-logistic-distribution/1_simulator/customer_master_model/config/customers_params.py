"""
Global settings for the CUSTOMER MASTER pipeline.
Edit this file to configure timeouts, servers, and output format, brands and chanfe regional warehouse mapping.
"""
from pathlib import Path

# Overpass API: it try with two options. 
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

APP_NAME = "customer_base_generator"
MAX_RETRIES = 3
TIMEOUT = 120          # seconds per request
RETRY_WAIT = 10        # seconds between retries
RATE_LIMIT_WAIT = 60   # seconds to wait on HTTP 429

# Pipeline config
SLEEP_BETWEEN_BRANDS = 5   # seconds between brand queries
GEOFENCE_RADIUS_M = 150    # metres

# Output
OUTPUT_FORMAT = "csv"
OUTPUT_DIR = Path("../data_catalog/")


# Segment distribution to classify clients with loyalty
SEGMENT_DISTRIBUTION = {
    "bronze": 0.34,
    "silver": 0.45,
    "gold":   0.21,
}

# BRANDS dictionary of store and its wikidata id. It can find the wikidata id here https://nsi.guide/index.html?t=* 
BRANDS = {
    "Walmart": "Q483551",
    "Soriana": "Q735562",
    "Chedraui": "Q2961952"
}