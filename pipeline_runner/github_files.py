"""Descoberta e registro de arquivos C/C++ em repositorios GitHub baixados."""

import csv
import datetime as dt
from pathlib import Path

from pipeline_runner.paths import PROJECT_ROOT, REPORTS_DIR, display_path

GITHUB_FILES_FILE = REPORTS_DIR / "github_files.csv"
CODE_EXTENSIONS = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hxx"}
IGNORED_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "dist",
    "node_modules",
    "third_party",
    "vendor",
}
FILE_FIELDS = [
    "id",
    "link_id",
    "file_path",
    "extension",
    "size_bytes",
    "status",
    "error",
    "created_at",
]


def ensure_files_file(csv_file=GITHUB_FILES_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    if csv_file.exists():
        return

    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FILE_FIELDS)
        writer.writeheader()


def read_files(csv_file=GITHUB_FILES_FILE):
    csv_file = Path(csv_file)
    if not csv_file.exists():
        return []

    with csv_file.open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def write_files(rows, csv_file=GITHUB_FILES_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FILE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def file_counts_by_link(rows=None):
    counts = {}
    for row in rows if rows is not None else read_files():
        link_id = row.get("link_id", "")
        if link_id:
            counts[link_id] = counts.get(link_id, 0) + 1
    return counts


def remove_files_for_link(link_id, csv_file=GITHUB_FILES_FILE):
    rows = [row for row in read_files(csv_file) if row.get("link_id") != link_id]
    write_files(rows, csv_file)
    return rows


def is_ignored_dir(path):
    return any(part in IGNORED_DIRS for part in path.parts)


def discover_code_files(root_path):
    root_path = Path(root_path)
    if not root_path.exists():
        raise ValueError(f"caminho local nao encontrado: {display_path(root_path)}")
    if not root_path.is_dir():
        raise ValueError(f"caminho local deve ser diretorio: {display_path(root_path)}")

    files = []
    for path in sorted(root_path.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root_path)
        if is_ignored_dir(relative):
            continue
        if path.suffix.lower() in CODE_EXTENSIONS:
            files.append(path)
    return files


def next_file_id(link_id, index):
    return f"{link_id}_file_{index:06d}"


def replace_files_for_link(link_id, files, csv_file=GITHUB_FILES_FILE, created_at=None):
    created_at = created_at or dt.datetime.now().isoformat(timespec="seconds")
    existing_rows = [row for row in read_files(csv_file) if row.get("link_id") != link_id]
    new_rows = []
    for index, path in enumerate(files, start=1):
        new_rows.append(
            {
                "id": next_file_id(link_id, index),
                "link_id": link_id,
                "file_path": display_path(path),
                "extension": path.suffix.lower(),
                "size_bytes": str(path.stat().st_size),
                "status": "descoberto",
                "error": "",
                "created_at": created_at,
            }
        )

    rows = [*existing_rows, *new_rows]
    write_files(rows, csv_file)
    return new_rows


def resolve_local_path(local_path):
    path = Path(local_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
