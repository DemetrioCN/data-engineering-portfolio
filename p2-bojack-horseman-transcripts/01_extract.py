"""
01_extract.py — BRONZE Layer
==============================
Download each episode in HTML and save in local storage like a bucket AWS S3 structure

Input  : queerworm.github.io (web)
Output : bojack/bronze/season={n}/S{n}E{n}.html
         bojack/bronze/season={n}/S{n}E{n}_meta.json
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import BASE_URL, BRONZE_DIR, LOG_FILE, HEADERS, DELAY_BETWEEN_REQUESTS, REQUEST_TIMEOUT 


# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def fetch_episode_list() -> list[dict]:
    """
    Downloads the index page and extracts the full list of episodes.

    The page has this structure:
        #### Season 1
        [Episode 1 - Title](https://...101.html)
        [Episode 2 - Title](https://...102.html)
        #### Season 2
        ...

    Returns:
        [
          {
            "episode_id":  "S01E01",
            "season_num":  1,
            "episode_num": 1,
            "title":       "Episode 1 - BoJack Horseman: ...",
            "url":         "https://queerworm.github.io/transcripts/bojack/101.html"
          },
          ...
        ]
    """
    log.info(f"Downloading index: {BASE_URL}")

    resp = requests.get(BASE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    soup       = BeautifulSoup(resp.text, "html.parser")
    episodes   = []
    season_num = 0

    for tag in soup.find_all(["h4", "a"]):

        # Detect season header
        # <h4>Season 1</h4>  (the first <h4> is "Home", regex won't match it)
        if tag.name == "h4":
            text  = tag.get_text(strip=True)
            match = re.search(r"Season\s+(\d+)", text, re.IGNORECASE)
            if match:
                season_num = int(match.group(1))
            continue

        # Detect episode link
        # URL format: https://.../bojack/101.html
        if tag.name == "a" and season_num > 0:
            href = tag.get("href", "")

            # Keep only episode links: end in NNN.html
            if not re.search(r"\d{3}\.html$", href):
                continue

            # Extract episode number from filename (101 → ep 1)
            filename    = Path(href).stem    # "101"
            episode_num = int(filename[-2:]) # last 2 digits

            episode_id = f"S{season_num:02d}E{episode_num:02d}"
            title      = tag.get_text(strip=True)

            episodes.append({
                "episode_id":  episode_id,
                "season_num":  season_num,
                "episode_num": episode_num,
                "title":       title,
                "url":         BASE_URL + href,
            })

    log.info(f"  → {len(episodes)} episodes found")
    return episodes

 
def already_downloaded(episode: dict) -> bool:
    """
    Returns True if the .html for this episode already exists in Bronze.
    If it exists → skip. If not → download.
    """
    html_path = (
        BRONZE_DIR
        / f"season={episode['season_num']}"
        / f"{episode['episode_id']}.html"
    )
    return html_path.exists()


def save_to_bronze(episode: dict) -> bool:
    """
    Downloads the episode HTML and saves two files to Bronze:

        bronze/season={n}/{episode_id}.html       ← raw HTML, immutable
        bronze/season={n}/{episode_id}_meta.json  ← capture metadata

    Returns True on success, False on failure.
    """
    url        = episode["url"]
    season_dir = BRONZE_DIR / f"season={episode['season_num']}"
    season_dir.mkdir(parents=True, exist_ok=True)

    html_path = season_dir / f"{episode['episode_id']}.html"
    meta_path = season_dir / f"{episode['episode_id']}_meta.json"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        # Save raw HTML 
        html_path.write_text(resp.text, encoding="utf-8")

        # Save capture metadata 
        meta = {
            "episode_id":    episode["episode_id"],
            "season_num":    episode["season_num"],
            "episode_num":   episode["episode_num"],
            "title":         episode["title"],
            "url":           url,
            "scraped_at":    datetime.now(timezone.utc).isoformat(),
            "status_code":   resp.status_code,
            "content_bytes": len(resp.content),
        }
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        log.info(
            f"  ✓ {episode['episode_id']}  "
            f"{episode['title'][:55]}  "
            f"({meta['content_bytes']:,} bytes)"
        )
        return True

    except requests.RequestException as e:
        log.error(f"  ✗ {episode['episode_id']}  ERROR: {e}")
        # If the HTML file is incomplete, remove it so the checkpoint
        # does not mark it as done on the next run
        if html_path.exists():
            html_path.unlink()
        return False


def main():
    log.info("=" * 60)
    log.info("EXTRACT — Bronze layer")
    log.info("=" * 60)
 
    # 1. Fetch full episode list from the index
    episodes = fetch_episode_list()
 
    # 2. Split into pending vs already downloaded
    pending = [ep for ep in episodes if not already_downloaded(ep)]
    skipped = len(episodes) - len(pending)
 
    log.info(f"  Pending             : {len(pending)}")
    log.info(f"  Already in Bronze (skip) : {skipped}")
    log.info("-" * 60)
 
    if not pending:
        log.info("Nothing new to download. Bronze is complete.")
        return
 
    # 3. Download pending episodes
    succeeded = 0
    failed    = 0
 
    for i, ep in enumerate(pending, 1):
        log.info(f"[{i:02d}/{len(pending):02d}] Downloading {ep['episode_id']}...")
        ok = save_to_bronze(ep)
 
        if ok:
            succeeded += 1
        else:
            failed += 1
 
        # Pause between requests (skip after the last one)
        if i < len(pending):
            time.sleep(DELAY_BETWEEN_REQUESTS)
 
    # 4. Final summary
    log.info("=" * 60)
    log.info(f"SUMMARY  ✓ {succeeded} downloaded  ✗ {failed} failed")
 
    total_html = len(list(BRONZE_DIR.glob("season=*/*.html")))
    log.info(f"Bronze total: {total_html} episodes")
 
    if failed:
        log.warning(f"  {failed} episode(s) failed. Re-run the script to retry them.")
    else:
        log.info("Bronze complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()