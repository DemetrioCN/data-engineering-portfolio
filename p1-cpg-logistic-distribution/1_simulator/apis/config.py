from pathlib import Path

INPUT_DIR      = Path("../data/transactional/visit_list/")
CACHE_DIR      = Path("../data/cache/api_visit_list/")
OUTPUT_DIR     = Path("../data/data_events/visit_list/")
INIT_DAY       = "08:00:00"
NUM_NEXT_EVENT = 4

TRANSIT_MINUTES  = (5, 15, 5)   # Transit between customers
VISIT_MINUTES    = (15, 30, 5)   # Attention time
CLOSE_MINUTES    = (2,  8, 1)   # exit


VISIT_LIST_SCHEMA = {
    "date":           "string",
    "warehouse_code": "string",
    "customer_id":    "string",
    "order_id":       "string",
    "route_id":       "string",
    "sequence":       "int64",
    "quantity":       "int64",
    "product_id":     "string",
}