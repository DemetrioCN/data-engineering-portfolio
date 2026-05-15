# Customer base pipeline generator
The customer base generator creates a catalog for the company. It contains useful information that companies usually generate for SAP ecosystem, especially in logistics.
In this case we use OpenStreetMap to easily locates branches across Mexico and their coordinate. Fictitious data suchs as loyalty classification, customer_id, geofence radius, etc. are also generate. Client IDs start with 0 - this is a common convention for handling this type of data, it is a way to handle this kind of data, as it often causes problems in pipelines when not handled correctly throughout the processes.

---

## Pipeline

```
Overpass API (OSM)
      │
      ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Extract    │────▶│   Enrich     │────▶│    Load      │
│             │     │              │     │              │
│ query brand │     │ reverse-geo  │     │ CSV          │
│ names from  │     │ assign region│     │ timestamped  │
│ OSM ways    │     │ CRM segment  │     │ output file  │
└─────────────┘     └──────────────┘     └──────────────┘
```

---

## Project structure

```
1_mock_data_customer_base_catalog/
├── config/
│   ├── settings.py     # timeouts, output format, segment distribution, brand list + state and warehouse mapping
├── pipeline/
│   ├── extractor.py    # Extract: Overpass API → raw DataFrame
│   ├── enricher.py     # Transform: geocode, region, segment, IDs
│   └── loader.py       # Load: write CSV
├── utils/
│   ├── http_client.py  # retry-aware Overpass HTTP client
│   └── geo.py          # reverse-geocoder wrapper
├── data/
│   ├── output/         # pipeline output
├── main.py             # Entrypoint
```

---

## Setup

**Requirements:** Python 3.11+

```bash
# 1. Create a virtual env with python3
python3 -m venv venv

# 2. Activate venv
source venv/bin/activate

# 3. Install dependencias from requirements.txt file
pip3 install -r requirements.txt
```

---

## Usage

```bash
# Run with all brands configured in config/brands.py
python main.py

```

The output file is written to `data/output/` with a timestamp:
`customer_base_20250112_143022.csv`

---
## Output schema

| Column              | Type    | Description                                    |
|---------------------|---------|------------------------------------------------|
| `name`              | str     | Store name from OSM tags                       |
| `brand`             | str     | Brand tag from OSM                             |
| `opening_hours`     | str     | OSM opening hours string                       |
| `lat`               | float   | Latitude                                       |
| `lon`               | float   | Longitude                                      |
| `city`              | str     | City from reverse geocoding                    |
| `state`             | str     | State from reverse geocoding                   |
| `warehouse_id`      | str     | Regional warehouse: CED001 / CED002 / CED003   |
| `customer_id`       | str     | Unique 10-digit identifier (starts with `0`)   |
| `segment`           | str     | Loyalty tier: bronze / silver / gold           |
| `geofence_radius_m` | int     | Geofence radius in metres (default: 150)       |

---

## Configuration

Edit `config/settings.py` to change timeouts, output format, or segment distribution. Add/remove brands or update the state → warehouse mapping.

---

## Data source

Store locations are sourced from
[OpenStreetMap](https://www.openstreetmap.org/) under the
[ODbL licence](https://opendatacommons.org/licenses/odbl/).
Reverse geocoding uses the
[`reverse_geocoder`](https://github.com/thampiman/reverse-geocoder) library
(offline, no API key required).
[How to use OpenStreeMaps](https://pybit.es/articles/openstreetmaps-overpass-api-and-python/)