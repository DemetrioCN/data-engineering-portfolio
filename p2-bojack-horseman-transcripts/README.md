# BoJack Horseman — Transcript Pipeline

Data Engineering portfolio project implementing **Medallion Architecture** (Bronze → Silver → Gold) to extract and serve the complete transcripts of BoJack Horseman as print-ready PDFs. All data lives on disk simulating AWS S3 — no databases, no cloud.

---

## Architecture

```
Web → Bronze (HTML) → Silver (JSON) → Gold (PDF)
      01_extract    02_transform     03_serve_pdf
```

| Layer | Location | Content |
|---|---|---|
| Bronze | `bojack-horseman/bronze/season={n}/` | Raw HTML + metadata. Immutable. |
| Silver | `bojack-horseman/silver/season={n}/` | Clean JSON, classified by line type. |
| Gold | `bojack-horseman/gold/pdf/season={n}/` | Print-ready PDF, one per season. |

---

## Setup

```bash
pip install requests beautifulsoup4 reportlab
```

---

## Running the pipeline

```bash
python 01_extract.py       # Web → Bronze
python 02_transform.py     # Bronze → Silver
python 03_serve_pdf.py     # Silver → Gold (all seasons)
```

Each script is independent and resumes automatically if interrupted — it skips files that already exist in the target layer.

---

## Silver schema

```json
{
  "episode_id": "S01E01",
  "season_num": 1,
  "episode_num": 1,
  "title": "BoJack Horseman: The BoJack Horseman Story, Chapter One",
  "lines": [
    { "timestamp": "00:00:13", "speaker": null, "text": "Mondays.", "type": "dialogue" },
    { "timestamp": "00:00:13", "speaker": null, "text": "[sighs]",  "type": "stage_direction" }
  ]
}
```

Line types: `dialogue` · `stage_direction` · `narration`

---

## Stack

| Tool | Role |
|---|---|
| requests + BeautifulSoup4 | Scraping (Bronze) |
| reportlab | PDF generation (Gold) |
| pathlib | S3-style path management |

---

## Source

Transcripts from [queerworm.github.io/transcripts/bojack](https://queerworm.github.io/transcripts/bojack/). Educational and portfolio use only.


## Nextstep
1. Integrate LLM to identify speakers.