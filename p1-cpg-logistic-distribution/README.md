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
 

# 4 Delivery Simulator API
 
Simulates delivery visit events from a `visit_list` CSV. Reads customer routes, processes them in batches of `NUM_NEXT_EVENT` visits per route, and persists the results as JSON. State is maintained across runs via a file-based cache.

## 4.1 Core logic
 
### `run_simulation()`
 
Full pipeline entry point — called by both `run_full_day.sh` and the `run_scheduler.sh`.
 
1. Loads the latest `visit_list` CSV from `INPUT_DIR`.
2. Aggregates rows by `customer_id` (sums `quantity`, takes `first` for all other fields).
3. Loads the day's cache from `CACHE_DIR` — empty dict on first run.
4. For each route, calls `process_route()` and collects events and updated cache state.
5. Writes all events to a single dated JSON file and persists the updated cache.

### `process_route()`
 
Processes the next `NUM_NEXT_EVENT` pending visits for one route.
 
- Reads `sequence` and `last_departure_time` from cache (defaults to `INIT_DAY` on first run).
- Filters `df` to rows with `sequence > cache_sequence` and takes the first `N`.
- If no pending visits, returns `[]` and the preserved cache state — this ensures the cache is always written with the full state of all routes, including exhausted ones.
- Simulates each visit in sequence order, chaining departure times.


### `simulate_visit()`
 
Simulates a single delivery visit. Time chain:
 
```
last_departure → arrival → signature → departure
```
 
| Step | Function | Range (config) |
|---|---|---|
| Transit | `assign_arrival_time` | `TRANSIT_MINUTES` |
| At customer | `assign_signature_time` | `VISIT_MINUTES` |
| Close & leave | `assign_departure_time` | `CLOSE_MINUTES` |
 
Delivery outcome: 70% full delivery, 20% partial, 10% zero.
Payment method: random `cash` or `card`.
 
---
 
## 4.2 Storage
 
All storage is file-based, partitioned by date.
 
**Cache** — tracks last processed `sequence` and `last_departure_time` per route:
```
{CACHE_DIR}/year=YYYY/month=MM/day=DD/YYYYMMDD_N_visit_list.json
```
 
**Events** — one file per simulation run:
```
{OUTPUT_DIR}/year=YYYY/month=MM/day=DD/YYYYMMDD_N_visit_events.json
```
 
Files are numbered sequentially (`N = 1, 2, 3...`). Sorting by `N` uses `int(f.stem.split("_")[1])` — not alphabetical — to avoid ordering bugs with numbers ≥ 10.
 
---
 
## 4.3 Endpoints
 
| Method | Path | Description |
|---|---|---|
| `POST` | `/simulate/batch` | Run one simulation immediately. Returns generated events. |
| `POST` | `/simulate/scheduler/start?interval_minutes=N` | Start scheduled runs every N minutes. |
| `POST` | `/simulate/scheduler/stop` | Stop the scheduler without shutting down the server. |
| `GET` | `/simulate/scheduler/status` | Returns `{active, next_run}`. |
| `GET` | `/events` | Returns events from the most recent run. |
 
The scheduler stops itself automatically when `run_simulation()` returns 0 events — all routes exhausted.
 
---
 
## 4.4 Run modes
 
**Scheduler mode** (`run_scheduler.sh`) — simulates incrementally every N minutes, mimicking real-time delivery progress. Stops automatically when all routes are exhausted.
 
```bash
./run_scheduler.sh 30   # every 30 minutes
./run_scheduler.sh 1    # every 1 minute (fast testing)
```
 
**Full day mode** (`run_full_day.sh`) — calls `/simulate/batch` in a loop until 0 events are returned, processing the entire day at once.
 
```bash
./run_full_day.sh
```
 
---
 
## 4.5 Event schema (`VisitEvent`)
 
| Field | Type | Description |
|---|---|---|
| `date` | `str` | Visit date |
| `customer_id` | `str` | FK to `customer_master` |
| `route_id` | `str` | Route identifier |
| `order_id` | `str` | Order identifier |
| `warehouse_code` | `str` | FK to `warehouse_master` |
| `quantity` | `int` | Planned quantity |
| `delivery_quantity` | `int \| None` | Actual delivered quantity |
| `arrival_time` | `datetime \| None` | Time of arrival at customer |
| `signature_time` | `datetime \| None` | Time of signature |
| `departure_time` | `datetime \| None` | Time of departure |
| `payment_method` | `cash \| card \| None` | Payment method used |
 