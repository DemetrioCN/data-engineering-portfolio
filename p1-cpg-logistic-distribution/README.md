# CPG-LOGISTIC-DISTRIBUTION

## Overview
AI-Tacos is an emerging AI company based in Mexico. AI-Tacos sells profesional robots that prepare all kinds of tacos available across Mexico. The process is oil-free: you simply add the meat, corn for tortillas and vegetables, and the robot uses air-frying technology to produce delicious tacos.

After a period of rapid growth, AI-Tacos needed to build its data ecosystem from scratch. This project delivers that foundation: a centralized data platform on Azure + Databricks, real-time operational monitoring, executive KPI dashboards, and the analytical infrastructure needed to support a data science team.


## Bussines Requirements
AI-Tacos operates a B2B distribution model across multiple warehouses in Mexico.

The company recently equipped its fleet with two external data sources:
|System|Type|Description|
|--------|--------|--------|
|TrackTruck|Telemetry Platform + REST API|Provides real-time GPS location and truck event data|
|GPSVisit|Android App + REST API|Allows drivers to log completed client visits in the field|


#### Requirements
1. **Centralized Data Lake (Delta Lake)** <br>
Consolidate all data sources into a single, governed repository. The platform must be built on Azure and Databricks, as mandated by the company's technology stack decision.

2. **Real-Time Operational Monitoring**<br>
Build a web application that allows operations teams to track trucks and driver activity in near real-time, including visit logs captured through the GPSVisit mobile app.

3. **KPI Dashboard**<br>
In other application, deliver an executive dashboard tracking and visit.<br>
    - Completed service visits
    - Units sold (robots)
    - Revenue

4. **Advanced Analytics Layer**<br>
Support the company's newly hired data scientist by providing access to clean, curated, production-ready data. This includes surfacing operational patterns to support predictive and prescriptive analytics work.



<br>

# Simulator

## 1.1 Material master pipeline -> /1_simulator/models/material_master_model

Generates synthetic data for the material master catalog. Reads product definitions from a config file, applies schema validation, and persists the result as a dated CSV file.

---

### Extract

- Source: product catalog defined in `config`.
- Reads static dummy records — no external API call required.
- Each record maps to one row in the output schema.

### Transform

Apply schema simple transformation.

| Field | pandas type | Description |
|---|---|---|
| `product_id` | `string` | Unique product identifier. Format: `TRBT-{NNN}` |
| `sku` | `string` | Stock keeping unit. Format: `TRBT-{SLUG}` |
| `name` | `string` | Human-readable product name |
| `description` | `string` | Max 200 chars |
| `price` | `float64` | Unit price. Must be `> 0` |
| `currency` | `string` | ISO 4217 currency code (e.g. `USD`) |
| `weight_kg` | `float64` | Gross weight in kilograms |
| `dimensions_cm` | `string` | `WxDxH` in centimeters. |
| `is_active` | `boolean` | Whether product is active in catalog |

### Load

- **Output path:** `~/data/material_master/{DATE}_material_master.csv`
- `{DATE}` is substituted with the current date at runtime in `YYYYMMDD` format.
- **Example:** `~/data/material_master/20260629_material_master.csv`
- Format: CSV with header row, UTF-8 encoding.

---

## 2.1 Customer master pipeline -> /1_simulator/models/customer_master_model

Generates a mock client catalog classified by loyalty segment. Store locations are pulled from OpenStreetMap (Overpass API) by brand, enriched with geocoding and clustering, then split into two related outputs: a customer master and a warehouse master.

---
 
### Extract
 
- Source: [Overpass API](https://overpass-api.de/) (OpenStreetMap), queried per brand via `brand:wikidata` tag.
- Iterates over `BRANDS` (a `{brand_name: wikidata_id}` dict from config), one Overpass query per brand, scoped to the `country` boundary (default `México`).
- A fixed `SLEEP_BETWEEN_BRANDS` delay is applied between queries to avoid rate-limiting.
- Each result row keeps `name`, `brand`, `opening_hours`, `lat`, `lon`. Elements missing coordinates are dropped.
- Deduplicates on `(lat, lon)` — the same physical store can otherwise appear twice if returned by overlapping OSM ways.
- If a brand returns no results, logs a warning and continues with the next brand rather than aborting.


### Transform
 
Enriches raw locations in five steps, then splits the result into two separate DataFrames:
 
| Step | Operation | Adds |
|---|---|---|
| 1 | Reverse-geocode `lat`/`lon` | `city`, `state` |
| 2 | Cluster into warehouse regions | `warehouse`, `warehouse_id` |
| 3 | Generate unique client IDs | `customer_id` |
| 4 | Assign loyalty segment | `segment` (`bronze` / `silver` / `gold`) |
| 5 | Add geofence radius | `geofence_radius_m` (constant from config) |
 
**`customer_id` generation:** random 10-digit string, always prefixed with `"0"`. Uniqueness enforced via a `set` until the target length is reached.
 
**`segment` assignment:** distribution-controlled, not uniform-random. `SEGMENT_DISTRIBUTION` (config) defines target proportions per segment (e.g. `bronze: 0.5, silver: 0.3, gold: 0.2`); counts are rounded to match `len(df)`, then shuffled.
 
**Warehouse clustering:** delegated to `models.warehouse_clustering.run_clustering`, an external model that groups customer locations into regional warehouses and returns two related DataFrames — customer-level and warehouse-level — joined by `warehouse_code`.

#### Output schema — `customer_master`
 
| Field | Description |
|---|---|
| `name` | Store name |
| `brand` | Brand name |
| `opening_hours` | Raw OSM `opening_hours` tag |
| `lat`, `lon` | Coordinates |
| `city`, `state` | Reverse-geocoded from coordinates |
| `customer_id` | Unique 10-digit identifier |
| `segment` | `bronze` / `silver` / `gold` |
| `geofence_radius_m` | Constant from config |
| `warehouse_code` | FK to `warehouse_master.warehouse_code` |
 
#### Output schema — `warehouse_master`
 
| Field | Description |
|---|---|
| `warehouse_id` | Unique warehouse identifier |
| `warehouse_code` | Short code, derived from `warehouse_name` |
| `warehouse_name` | Full warehouse/region name |
| `lat`, `lon` | Warehouse coordinates |
 
### Load
 
- **Output paths:**
  - `{OUTPUT_DIR}/customer_master/{DATE}_customer_master.csv`
  - `{OUTPUT_DIR}/warehouse_master/{DATE}_warehouse_master.csv`
- `{DATE}` is substituted with the current date at runtime in `YYYYMMDD` format.
- `load()` creates `output_dir` if it doesn't exist.
- Format: CSV with header row, UTF-8 encoding. Only `csv` is currently supported. 
- Each call to `load()` writes one DataFrame; the pipeline calls it twice (once per output).
---


## 3.1 Visit list pipeline -> /1_simulator/models/visit_list_model

Generates a daily random visit and order list per warehouse. Reads the latest customer_master and material_master CSVs, samples a subset of customers per warehouse, assigns products and quantities to each, and writes the result as a single dated CSV organized by month.


### Extract
 
Reads the most recent file in each input folder (resolved by `YYYYMMDD` filename prefix, descending sort).
 
 
### Transform
 
| Step | What it does |
|---|---|
| Sample customers | Random `[20, 25, 30, 35, 40]` customers per warehouse |
| Generate IDs | `order_id`: `YYYYMMDD` + random 5-digit number via `random.sample`. `route_id`: `R-{YYYYMMDD}-{NN}` per warehouse |
| Assign sequence | Customers ordered by `customer_id` desc within each route, numbered `1..N` |
| Expand to order lines | Each customer gets `1..M` random products with quantities in `[5, 10, …, 50]` |
 
### Load
 
- **Output:** `{OUTPUT_PATH}/{YYYY-MM}/{DATE}_{FILE_NAME}.csv`

#### Output schema
 
| Field | Description |
|---|---|
| `date` | Visit date (`YYYY-MM-DD`) |
| `warehouse_code` | FK → `customer_master` |
| `customer_id` | 10-digit string, FK → `customer_master` |
| `order_id` | Unique order identifier for the day |
| `route_id` | Route per warehouse. Format: `R-{YYYYMMDD}-{NN}` |
| `sequence` | Visit order within the route |
| `product_id` | FK → `material_master` |
| `quantity` | Units ordered. Multiple of 5, range `5–50` |
 
