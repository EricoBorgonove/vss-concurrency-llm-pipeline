"""Controle CSV dos links do GitHub submetidos pelo usuario."""

import csv
import datetime as dt
from pathlib import Path

from pipeline_runner.paths import REPORTS_DIR

GITHUB_LINKS_FILE = REPORTS_DIR / "github_links.csv"
LINK_FIELDS = [
    "id",
    "submitted_at",
    "url",
    "url_type",
    "status",
    "local_path",
    "error",
    "started_at",
    "finished_at",
]


def normalize_url(url):
    return str(url or "").strip()


def ensure_links_file(csv_file=GITHUB_LINKS_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    if csv_file.exists():
        return

    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=LINK_FIELDS)
        writer.writeheader()


def read_links(csv_file=GITHUB_LINKS_FILE):
    csv_file = Path(csv_file)
    if not csv_file.exists():
        return []

    with csv_file.open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def next_link_id(rows):
    numbers = []
    for row in rows:
        value = row.get("id", "")
        if value.startswith("gh_"):
            try:
                numbers.append(int(value.removeprefix("gh_")))
            except ValueError:
                continue

    return f"gh_{(max(numbers) if numbers else 0) + 1:06d}"


def append_link(url, csv_file=GITHUB_LINKS_FILE, submitted_at=None):
    normalized_url = normalize_url(url)
    if not normalized_url:
        raise ValueError("url nao informada")

    csv_file = Path(csv_file)
    ensure_links_file(csv_file)
    rows = read_links(csv_file)
    row = {
        "id": next_link_id(rows),
        "submitted_at": submitted_at or dt.datetime.now().isoformat(timespec="seconds"),
        "url": normalized_url,
        "url_type": "",
        "status": "pendente",
        "local_path": "",
        "error": "",
        "started_at": "",
        "finished_at": "",
    }

    with csv_file.open("a", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=LINK_FIELDS)
        writer.writerow(row)

    return row
