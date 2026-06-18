from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch


# ----- EXTRACT CONFIGURATION ------
BASE_URL    = "https://queerworm.github.io/transcripts/bojack/"
BRONZE_DIR  = Path("bojack-horseman/bronze")
EXTRACT_LOG_FILE    = "01_extract.log"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Apple M4) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

DELAY_BETWEEN_REQUESTS = 1.5   # segundos — respetuoso con el servidor
REQUEST_TIMEOUT        = 15    # segundos por petición


# ----- TRANSFORM CONFIGURATION --------
SILVER_DIR = Path("bojack-horseman/silver")
TRANSFORM_LOG_FILE   = "02_transform.log"
DELAY_BETWEEN_EPISODES = 0.5  # seconds



# ------ CONFIGURATION ----
GOLD_DIR   = Path("bojack-horseman/gold")
SERVER_LOG_FILE   = "03_serve_pdf.log"

# Page geometry (letter, print-optimized)
PAGE_W, PAGE_H = letter          # 8.5 x 11 in
MARGIN_OUTER   = 0.65 * inch
MARGIN_INNER   = 0.55 * inch
MARGIN_TOP     = 0.70 * inch
MARGIN_BOT     = 0.65 * inch
COL_GAP        = 0.25 * inch

COL_W = (PAGE_W - MARGIN_OUTER * 2 - COL_GAP) / 2   # ~3.5 in per column
