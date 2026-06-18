"""
03_serve_pdf.py — GOLD Layer
==============================
Two-column print-optimized PDF. One PDF per season.

Input  : bojack-horseman/silver/season={n}/S{n}E{n}.json
Output : bojack-horseman/gold/pdf/season={n}/S0n_BoJack_Horseman.pdf

Usage:
    python 03_serve_pdf.py              # all seasons
    python 03_serve_pdf.py --season 1   # specific season
"""

import argparse
import json
import logging
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    KeepTogether,
)

from config import SERVER_LOG_FILE,SILVER_DIR, GOLD_DIR, SERVER_LOG_FILE, PAGE_W, PAGE_H, MARGIN_OUTER, MARGIN_INNER, MARGIN_TOP, MARGIN_BOT, COL_GAP, COL_W

#  LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(SERVER_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

#  STYLES
def build_styles() -> dict:
    base = getSampleStyleSheet()

    # Season header — top of first page only
    season_title = ParagraphStyle(
        "season_title",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=colors.HexColor("#1a2e52"),
        spaceAfter=2,
        spaceBefore=0,
    )

    # Episode header — inline, no page break
    episode_title = ParagraphStyle(
        "episode_title",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.HexColor("#1a2e52"),
        spaceBefore=7,
        spaceAfter=1,
    )

    # Timestamp — tiny, above each line
    timestamp = ParagraphStyle(
        "timestamp",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=6,
        textColor=colors.HexColor("#bbbbbb"),
        spaceBefore=1,
        spaceAfter=0,
        leading=7,
    )

    # Dialogue — main body
    dialogue = ParagraphStyle(
        "dialogue",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#111111"),
        spaceBefore=0,
        spaceAfter=2,
        leading=11,
    )

    # Stage direction — italic gray
    stage = ParagraphStyle(
        "stage",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        textColor=colors.HexColor("#888888"),
        spaceBefore=0,
        spaceAfter=2,
        leading=10,
    )

    # Narration — italic dark gray
    narration = ParagraphStyle(
        "narration",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=colors.HexColor("#444444"),
        spaceBefore=0,
        spaceAfter=2,
        leading=11,
    )

    return {
        "season_title": season_title,
        "episode_title": episode_title,
        "timestamp":  timestamp,
        "dialogue":   dialogue,
        "stage":      stage,
        "narration":  narration,
    }


#  HELPERS
def safe(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def skip_line(text: str) -> bool:
    return text.strip() in {"♪ ♪", "♪", "-", "–", ""}


#  PAGE TEMPLATES  (cover = 1 col, content = 2 col)
def make_doc(out_path: str) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=MARGIN_OUTER,
        rightMargin=MARGIN_OUTER,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOT,
    )

    body_h = PAGE_H - MARGIN_TOP - MARGIN_BOT

    # Cover: single full-width frame
    cover_frame = Frame(
        MARGIN_OUTER, MARGIN_BOT,
        PAGE_W - 2 * MARGIN_OUTER, body_h,
        id="cover",
    )

    # Content: two equal columns
    left_frame = Frame(
        MARGIN_OUTER, MARGIN_BOT,
        COL_W, body_h,
        id="left",
    )
    right_frame = Frame(
        MARGIN_OUTER + COL_W + COL_GAP, MARGIN_BOT,
        COL_W, body_h,
        id="right",
    )

    doc.addPageTemplates([
        PageTemplate(id="Cover",   frames=[cover_frame]),
        PageTemplate(id="Content", frames=[left_frame, right_frame]),
    ])
    return doc


#  COVER PAGE
def cover_page(season_num: int, ep_count: int, styles: dict) -> list:
    cover_title = ParagraphStyle(
        "ct", fontName="Helvetica-Bold", fontSize=26,
        textColor=colors.HexColor("#1a2e52"), alignment=1, spaceAfter=6,
    )
    cover_sub = ParagraphStyle(
        "cs", fontName="Helvetica", fontSize=12,
        textColor=colors.HexColor("#555555"), alignment=1, spaceAfter=4,
    )
    cover_note = ParagraphStyle(
        "cn", fontName="Helvetica", fontSize=9,
        textColor=colors.HexColor("#aaaaaa"), alignment=1,
    )

    return [
        Spacer(1, 1.4 * inch),
        Paragraph("BoJack Horseman", cover_title),
        Spacer(1, 0.18 * inch),
        Paragraph(f"Season {season_num} — Complete Transcripts", cover_sub),
        Spacer(1, 0.15 * inch),
        HRFlowable(width="50%", thickness=1.2,
                   color=colors.HexColor("#1a2e52"), hAlign="CENTER"),
        Spacer(1, 0.12 * inch),
        Paragraph(f"{ep_count} episodes", cover_note),
        NextPageTemplate("Content"),
        PageBreak(),
    ]


#  SEASON HEADER  (first thing in Content pages)
def season_header(season_num: int, styles: dict) -> list:
    return []


#  EPISODE → FLOWABLES
def episode_to_flowables(episode: dict, styles: dict) -> list:
    """
    Episode title + all lines, kept together at the top so the title
    never strands alone at the bottom of a column.
    """
    ep_num   = episode.get("episode_num", "")
    title    = episode.get("title", "")
    # Strip "Episode N - " prefix if present to save space
    import re
    title = re.sub(r"^Episode \d+\s*[-–]\s*", "", title).strip()

    header = [
        Paragraph(f"Ep {ep_num} — {safe(title)}", styles["episode_title"]),
        HRFlowable(width="100%", thickness=0.4,
                   color=colors.HexColor("#cccccc"), spaceAfter=2),
    ]

    lines_flow = []
    for line in episode.get("lines", []):
        text      = line.get("text", "").strip()
        line_type = line.get("type", "dialogue")
        timestamp = line.get("timestamp", "")

        if skip_line(text):
            continue

        if timestamp:
            lines_flow.append(Paragraph(timestamp, styles["timestamp"]))

        style_key = {
            "dialogue":       "dialogue",
            "stage_direction": "stage",
            "narration":      "narration",
        }.get(line_type, "dialogue")

        lines_flow.append(Paragraph(safe(text), styles[style_key]))

    # Keep episode header with its first few lines so it never orphans
    first_chunk = header + lines_flow[:6]
    rest        = lines_flow[6:]

    return [KeepTogether(first_chunk)] + rest


#  BUILD ONE SEASON PDF
def build_season_pdf(season_num: int) -> bool:
    silver_season = SILVER_DIR / f"season={season_num}"
    episode_files = sorted(silver_season.glob("*.json"))

    if not episode_files:
        log.warning(f"  No Silver files found for season {season_num}")
        return False

    gold_season = GOLD_DIR / f"season={season_num}"
    gold_season.mkdir(parents=True, exist_ok=True)
    out_path = str(gold_season / f"S{season_num:02d}_BoJack_Horseman.pdf")

    log.info(f"  Season {season_num} — {len(episode_files)} episodes → {out_path}")

    doc    = make_doc(out_path)
    styles = build_styles()
    story  = []

    # Cover (single column template)
    story += cover_page(season_num, len(episode_files), styles)

    # Episodes
    for i, ep_path in enumerate(episode_files):
        episode    = json.loads(ep_path.read_text(encoding="utf-8"))
        line_count = len(episode.get("lines", []))
        log.info(f"    [{i+1:02d}/{len(episode_files)}] {episode.get('episode_id')} — {line_count} lines")

        if i > 0:
            story.append(PageBreak())   # each episode starts on a new page

        story += episode_to_flowables(episode, styles)

    doc.build(story)
    log.info(f"  ✓ Saved → {out_path}")
    return True


#  MAIN
def main():
    parser = argparse.ArgumentParser(description="Generate PDFs from Silver layer")
    parser.add_argument("--season", type=int, default=None)
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("SERVE PDF — Gold layer")
    log.info("=" * 60)

    if args.season:
        seasons = [args.season]
    else:
        seasons = sorted(
            int(d.name.replace("season=", ""))
            for d in SILVER_DIR.glob("season=*")
            if d.is_dir()
        )

    if not seasons:
        log.error("No seasons found in Silver. Run 02_transform.py first.")
        return

    log.info(f"  Seasons: {seasons}")
    log.info("-" * 60)

    succeeded = failed = 0
    for season_num in seasons:
        ok = build_season_pdf(season_num)
        succeeded += ok
        failed    += not ok

    log.info("=" * 60)
    log.info(f"SUMMARY  ✓ {succeeded} generated  ✗ {failed} failed")
    log.info("=" * 60)


if __name__ == "__main__":
    main()