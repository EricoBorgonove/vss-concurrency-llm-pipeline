"""Controle CSV dos links do GitHub submetidos pelo usuario."""

import csv
import datetime as dt
from pathlib import Path
from urllib.parse import urlparse

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


def classify_github_url(url):
    parsed = urlparse(normalize_url(url))
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if parsed.scheme != "https":
        return "", "url deve usar https"
    if host not in ("github.com", "www.github.com"):
        return "", "url deve ser do github.com"
    if len(path_parts) < 2:
        return "", "url deve informar usuario e repositorio"

    user, repo = path_parts[:2]
    if not user or not repo:
        return "", "url deve informar usuario e repositorio"

    if len(path_parts) == 2:
        return "repo", ""

    marker = path_parts[2]
    if marker == "blob" and len(path_parts) >= 5:
        return "file", ""
    if marker == "tree" and len(path_parts) >= 4:
        return "directory", ""

    return "", "url do github deve apontar para repositorio, arquivo ou diretorio"


def ensure_links_file(csv_file=GITHUB_LINKS_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    if csv_file.exists():
        return

    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=LINK_FIELDS)
        writer.writeheader()


def enrich_link_row(row):
    enriched = {field: row.get(field, "") for field in LINK_FIELDS}
    if enriched["url"] and not enriched["url_type"] and not enriched["error"]:
        url_type, error = classify_github_url(enriched["url"])
        enriched["url_type"] = url_type
        enriched["error"] = error
        if error:
            enriched["status"] = "falhou"
    return enriched


def read_links(csv_file=GITHUB_LINKS_FILE):
    csv_file = Path(csv_file)
    if not csv_file.exists():
        return []

    with csv_file.open(encoding="utf-8", newline="") as input_file:
        return [enrich_link_row(row) for row in csv.DictReader(input_file)]


def write_links(rows, csv_file=GITHUB_LINKS_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=LINK_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


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

    url_type, error = classify_github_url(normalized_url)
    csv_file = Path(csv_file)
    ensure_links_file(csv_file)
    rows = read_links(csv_file)
    row = {
        "id": next_link_id(rows),
        "submitted_at": submitted_at or dt.datetime.now().isoformat(timespec="seconds"),
        "url": normalized_url,
        "url_type": url_type,
        "status": "falhou" if error else "pendente",
        "local_path": "",
        "error": error,
        "started_at": "",
        "finished_at": "",
    }

    with csv_file.open("a", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=LINK_FIELDS)
        writer.writerow(row)

    return row


def update_link(link_id, updates, csv_file=GITHUB_LINKS_FILE):
    rows = read_links(csv_file)
    updated_row = None
    for row in rows:
        if row.get("id") == link_id:
            for field, value in updates.items():
                if field in LINK_FIELDS:
                    row[field] = value
            updated_row = row
            break

    if updated_row is None:
        raise ValueError(f"link nao encontrado: {link_id}")

    write_links(rows, csv_file)
    return updated_row


def get_link(link_id, csv_file=GITHUB_LINKS_FILE):
    for row in read_links(csv_file):
        if row.get("id") == link_id:
            return row
    raise ValueError(f"link nao encontrado: {link_id}")
