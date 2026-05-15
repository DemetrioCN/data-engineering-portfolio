"""
Global settings for the CUSTOMER MASTER pipeline.
Edit this file to configure timeouts, servers, and output format, brands and chanfe regional warehouse mapping.
"""

# Overpass API: it try with two options. 
OVERPASS_SERVERS: list[str] = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

APP_NAME: str = "customer_base_generator"
MAX_RETRIES: int = 3
TIMEOUT: int = 120          # seconds per request
RETRY_WAIT: int = 10        # seconds between retries
RATE_LIMIT_WAIT: int = 60   # seconds to wait on HTTP 429

# Pipeline config
SLEEP_BETWEEN_BRANDS: int = 5   # seconds between brand queries
GEOFENCE_RADIUS_M: int = 150    # metres

# Output
OUTPUT_FORMAT: str = "csv"
OUTPUT_DIR: str = "data/output/customer_master"

# Segment distribution to classify clients with loyalty
SEGMENT_DISTRIBUTION: dict[str, float] = {
    "bronze": 0.34,
    "silver": 0.45,
    "gold":   0.21,
}

# BRANDS list of store names to query via Overpass
BRANDS: list[str] = [
    "Walmart",
    "Liverpool",
    "Coppel",
   # "Costco",
   # "Soriana",
   # "IKEA",
   # "Chedraui",
   # "Bodega Aurrera",
]

# MEXICO_REGIONS – maps Mexican state names to warehouse IDs (CED001/002/003)
MEXICO_REGIONS: dict[str, str] = {
    # ── North ─────────────────────────────────────────────────────────────────
    "Baja California":     "CED002",
    "Baja California Sur": "CED002",
    "Sonora":              "CED002",
    "Chihuahua":           "CED002",
    "Coahuila":            "CED002",
    "Nuevo Leon":          "CED002",
    "Tamaulipas":          "CED002",
    "Sinaloa":             "CED002",
    "Durango":             "CED002",
    "California":          "CED002",
    # ── Center ────────────────────────────────────────────────────────────────
    "Nayarit":             "CED001",
    "Zacatecas":           "CED001",
    "San Luis Potosi":     "CED001",
    "Jalisco":             "CED001",
    "Aguascalientes":      "CED001",
    "Guanajuato":          "CED001",
    "Queretaro":           "CED001",
    "Colima":              "CED001",
    "Michoacan":           "CED001",
    "Mexico":              "CED001",
    "Estado de Mexico":    "CED001",
    "Mexico City":         "CED001",
    "Ciudad de Mexico":    "CED001",
    "Morelos":             "CED001",
    "Hidalgo":             "CED001",
    "Tlaxcala":            "CED001",
    "Puebla":              "CED001",
    "Veracruz":            "CED001",
    # ── South ─────────────────────────────────────────────────────────────────
    "Guerrero":            "CED003",
    "Oaxaca":              "CED003",
    "Chiapas":             "CED003",
    "Tabasco":             "CED003",
    "Campeche":            "CED003",
    "Yucatan":             "CED003",
    "Quintana Roo":        "CED003",
}
