from pathlib import Path

BASE_PATH_CATALOG = Path('../../data/catalog')
INPUT_CUSTOMERS = BASE_PATH_CATALOG / 'customer_master'
INPUT_PRODUCTS  = BASE_PATH_CATALOG / 'material_master'

OUTPUT_PATH = Path('../../data/transactional/visit_list/')
OUTPUT_FORMAT = "csv"
FILE_NAME = "visit_list"
