"""
02_transform.py — SILVER Layer
================================
Parse Bronze HTML and clean text. No LLM — speaker is null for all lines.
 
Input  : bojack/bronze/season={n}/S{n}E{n}.html  +  S{n}E{n}_meta.json
Output : bojack/silver/season={n}/S{n}E{n}.json
 
Each Silver JSON has this structure:
{
  "episode_id":  "S01E01",
  "season_num":  1,
  "episode_num": 1,
  "title":       "BoJack Horseman: The BoJack Horseman Story, Chapter One",
  "lines": [
    {"timestamp": "00:00:13", "speaker": null, "text": "Mondays.",  "type": "dialogue"},
    {"timestamp": "00:00:13", "speaker": null, "text": "[sighs]",   "type": "stage_direction"}
  ]
}
 
Checkpoint: if the Silver .json already exists → skip.
Resume:     re-running picks up where it left off.
"""
 

import json
import logging
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import TRANSFORM_LOG_FILE, BRONZE_DIR, SILVER_DIR, DELAY_BETWEEN_EPISODES

#  LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(TRANSFORM_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


#  STEP 1 — Parse Bronze HTML into clean blocks
def parse_html(html: str) -> list[dict]:
    """
    Real HTML structure from Bronze:
 
        <article>
            <a class="timestamp" href="netflix.com?t=9">00:00:09</a>
            <p>Horsin' Around is filmed...</p>
            <a class="timestamp" href="netflix.com?t=13">00:00:13</a>
            <p>[sighs] Mondays.</p>
        </article>
 
    Timestamps are <a class="timestamp"> siblings of <p>, NOT inside <p>.
    Iterates direct children of <article> in document order.
    """
    soup = BeautifulSoup(html, "html.parser")
 
    re_an8       = re.compile(r"\{\\an\d\}")            # {\an8} subtitle code
    re_timestamp = re.compile(r"^\d{2}:\d{2}:\d{2}$")  # HH:MM:SS
    re_stage     = re.compile(r"(\[[^\]]+\])")           # [sighs], [laughs], ...
 
    blocks     = []
    current_ts = None
 
    def emit(text: str) -> None:
        text = text.strip()
        if text and current_ts is not None:
            blocks.append({"timestamp": current_ts, "raw_text": text})
 
    article = soup.find("article")
    if not article:
        return blocks
 
    for element in article.children:
        if not hasattr(element, "name") or element.name is None:
            continue
 
        # Timestamp: <a class="timestamp">00:00:09</a>
        if element.name == "a" and "timestamp" in element.get("class", []):
            ts = element.get_text(strip=True)
            if re_timestamp.match(ts):
                current_ts = ts
            continue
 
        # Dialogue / stage direction: <p>...</p>
        if element.name == "p":
            text = re.sub(r"\s+", " ", element.get_text(separator=" ")).strip()
            if not text:
                continue
            text = re_an8.sub("", text).strip()
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            # Split "[sighs] Mondays." → ["[sighs]", "Mondays."]
            parts = re_stage.split(text)
            for part in parts:
                emit(part)
 
    return blocks
 
 
#  STEP 2 — Classify line types 
def classify_line(text: str) -> str:
    """
    Determines the line type using deterministic rules.
 
    Types:
        stage_direction  →  [sighs], [laughs], [funky electronic music]
        narration        →  lines starting with "In YYYY,"
        dialogue         →  everything else
    """
    stripped = text.strip()
 
    if re.match(r"^\[.+\]$", stripped):
        return "stage_direction"
 
    if re.match(r"^In \d{4},", stripped):
        return "narration"
 
    return "dialogue"
 
 
def classify_blocks(blocks: list[dict]) -> list[dict]:
    """Adds 'type' to each block. Returns a new list."""
    return [
        {**block, "type": classify_line(block["raw_text"])}
        for block in blocks
    ]
 
 

#  STEP 3 — Build Silver lines (no LLM — speaker is null) 
def build_lines(blocks: list[dict]) -> list[dict]:
    """
    Converts classified blocks into Silver line format.
    speaker is null for all lines — no LLM involved.
    """
    return [
        {
            "timestamp": b["timestamp"],
            "speaker":   None,
            "text":      b["raw_text"],
            "type":      b["type"],
        }
        for b in blocks
    ]
 

#  STEP 4 — Save to Silver
def save_to_silver(meta: dict, lines: list[dict]) -> None:
    """Writes the cleaned episode to Silver."""
    season_dir = SILVER_DIR / f"season={meta['season_num']}"
    season_dir.mkdir(parents=True, exist_ok=True)
 
    output = {
        "episode_id":  meta["episode_id"],
        "season_num":  meta["season_num"],
        "episode_num": meta["episode_num"],
        "title":       meta["title"],
        "lines":       lines,
    }
 
    out_path = season_dir / f"{meta['episode_id']}.json"
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"  ✓ Saved → {out_path}")
 
 
#  CHECKPOINT 
def already_transformed(episode_id: str, season_num: int) -> bool:
    """Returns True if the Silver JSON for this episode already exists."""
    path = SILVER_DIR / f"season={season_num}" / f"{episode_id}.json"
    return path.exists()
 
 
#  PROCESS ONE EPISODE 
def transform_episode(html_path: Path, meta_path: Path) -> bool:
    """
    Bronze → Silver for a single episode:
 
        1. Read HTML + meta from Bronze
        2. Parse HTML into text blocks
        3. Classify line types
        4. Build Silver lines (speaker = null)
        5. Save to Silver
    """
    meta       = json.loads(meta_path.read_text(encoding="utf-8"))
    html       = html_path.read_text(encoding="utf-8")
    episode_id = meta["episode_id"]
 
    log.info(f"  [{episode_id}] {meta['title'][:60]}")
 
    # 1. Parse
    blocks = parse_html(html)
    log.info(f"    Parsed {len(blocks)} blocks from HTML")
 
    if not blocks:
        log.warning(f"    No blocks found — skipping {episode_id}")
        return False
 
    # 2. Classify
    blocks = classify_blocks(blocks)
    dialogue_count = sum(1 for b in blocks if b["type"] == "dialogue")
    stage_count    = sum(1 for b in blocks if b["type"] == "stage_direction")
    log.info(f"    Types — dialogue: {dialogue_count}  stage: {stage_count}")
 
    # 3. Build lines + save
    lines = build_lines(blocks)
    save_to_silver(meta, lines)
    return True
 
 
#  MAIN 
def main():
    log.info("=" * 60)
    log.info("TRANSFORM — Silver layer")
    log.info("=" * 60)
 
    bronze_episodes = sorted(BRONZE_DIR.glob("season=*/*.html"))
 
    if not bronze_episodes:
        log.error("No HTML files found in Bronze. Run 01_extract.py first.")
        return
 
    pending = [
        p for p in bronze_episodes
        if not already_transformed(
            p.stem,
            int(p.parent.name.replace("season=", ""))
        )
    ]
    skipped = len(bronze_episodes) - len(pending)
 
    log.info(f"  Bronze episodes          : {len(bronze_episodes)}")
    log.info(f"  Already in Silver (skip) : {skipped}")
    log.info(f"  Pending                  : {len(pending)}")
    log.info("-" * 60)
 
    if not pending:
        log.info("Nothing new to transform. Silver is complete.")
        return
 
    succeeded = 0
    failed    = 0
 
    for i, html_path in enumerate(pending, 1):
        meta_path = html_path.with_name(html_path.stem + "_meta.json")
 
        if not meta_path.exists():
            log.warning(f"  Missing meta for {html_path.name} — skipping")
            failed += 1
            continue
 
        log.info(f"[{i:02d}/{len(pending):02d}] Transforming {html_path.stem}...")
        ok = transform_episode(html_path, meta_path)
 
        if ok:
            succeeded += 1
        else:
            failed += 1
 
        if i < len(pending):
            time.sleep(DELAY_BETWEEN_EPISODES)
 
    log.info("=" * 60)
    log.info(f"SUMMARY  ✓ {succeeded} transformed  ✗ {failed} failed")
 
    total_silver = len(list(SILVER_DIR.glob("season=*/*.json")))
    log.info(f"Silver total: {total_silver} episodes on disk")
 
    if failed:
        log.warning(f"  {failed} episode(s) failed. Re-run the script to retry them.")
    else:
        log.info("Silver complete. You can now run 03_serve_pdf.py")
    log.info("=" * 60)
 
 
if __name__ == "__main__":
    main()
