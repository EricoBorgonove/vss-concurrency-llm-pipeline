"""Triagem estatica simples para arquivos C/C++ vindos do GitHub."""

import csv
import datetime as dt
import re
from pathlib import Path

from pipeline_runner.github_files import resolve_local_path
from pipeline_runner.paths import REPORTS_DIR

GITHUB_FINDINGS_FILE = REPORTS_DIR / "github_findings.csv"
FINDING_FIELDS = [
    "id",
    "link_id",
    "file_id",
    "tool",
    "file_path",
    "line",
    "category",
    "severity",
    "status",
    "message",
    "evidence",
    "created_at",
]
PATTERNS = [
    {
        "regex": re.compile(r"\bgets\s*\("),
        "category": "memory_corruption",
        "severity": "alta",
        "message": "uso de gets permite escrita sem limite no buffer",
    },
    {
        "regex": re.compile(r"\bstrcpy\s*\("),
        "category": "memory_corruption",
        "severity": "alta",
        "message": "uso de strcpy pode copiar dados alem do destino",
    },
    {
        "regex": re.compile(r"\bstrcat\s*\("),
        "category": "memory_corruption",
        "severity": "media",
        "message": "uso de strcat pode concatenar dados alem do destino",
    },
    {
        "regex": re.compile(r"\bsprintf\s*\("),
        "category": "memory_corruption",
        "severity": "alta",
        "message": "uso de sprintf sem limite pode exceder o buffer",
    },
    {
        "regex": re.compile(r"\bmemcpy\s*\("),
        "category": "memory_corruption",
        "severity": "media",
        "message": "uso de memcpy exige validacao explicita de tamanho",
    },
    {
        "regex": re.compile(r"\bpthread_create\s*\("),
        "category": "data_race",
        "severity": "media",
        "message": "criacao de thread indica necessidade de revisar estado compartilhado",
    },
    {
        "regex": re.compile(r"\bpthread_mutex_lock\s*\("),
        "category": "deadlock",
        "severity": "media",
        "message": "uso de mutex exige revisao de ordem de aquisicao de locks",
    },
    {
        "regex": re.compile(r"\bassert\s*\("),
        "category": "assertion_violation",
        "severity": "baixa",
        "message": "assertiva identifica propriedade que pode ser analisada por ferramenta",
    },
]
STRING_PATTERN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def strip_comments_and_strings(line, in_block_comment=False):
    result = []
    index = 0
    while index < len(line):
        if in_block_comment:
            end = line.find("*/", index)
            if end == -1:
                return "", True
            index = end + 2
            in_block_comment = False
            continue

        if line.startswith("/*", index):
            in_block_comment = True
            index += 2
            continue

        if line.startswith("//", index):
            break

        result.append(line[index])
        index += 1

    cleaned = "".join(result)
    cleaned = STRING_PATTERN.sub('""', cleaned)
    return cleaned, in_block_comment


def ensure_findings_file(csv_file=GITHUB_FINDINGS_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    if csv_file.exists():
        return

    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FINDING_FIELDS)
        writer.writeheader()


def read_findings(csv_file=GITHUB_FINDINGS_FILE):
    csv_file = Path(csv_file)
    if not csv_file.exists():
        return []

    with csv_file.open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def write_findings(rows, csv_file=GITHUB_FINDINGS_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FINDING_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def finding_counts_by_link(rows=None):
    counts = {}
    for row in rows if rows is not None else read_findings():
        link_id = row.get("link_id", "")
        if link_id:
            counts[link_id] = counts.get(link_id, 0) + 1
    return counts


def remove_findings_for_link(link_id, csv_file=GITHUB_FINDINGS_FILE):
    rows = [row for row in read_findings(csv_file) if row.get("link_id") != link_id]
    write_findings(rows, csv_file)
    return rows


def analyze_source_text(text):
    findings = []
    in_block_comment = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        cleaned, in_block_comment = strip_comments_and_strings(line, in_block_comment)
        stripped = cleaned.strip()
        if not stripped:
            continue
        for pattern in PATTERNS:
            if pattern["regex"].search(cleaned):
                findings.append(
                    {
                        "line": str(line_number),
                        "category": pattern["category"],
                        "severity": pattern["severity"],
                        "message": pattern["message"],
                        "evidence": stripped[:240],
                    }
                )
    return findings


def analyze_file_row(file_row):
    path = resolve_local_path(file_row["file_path"])
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [
            {
                "line": "",
                "category": "unknown",
                "severity": "baixa",
                "message": f"erro ao ler arquivo: {exc}",
                "evidence": "",
            }
        ]
    return analyze_source_text(text)


def next_finding_id(link_id, index):
    return f"{link_id}_finding_{index:06d}"


def replace_findings_for_link(link_id, file_rows, csv_file=GITHUB_FINDINGS_FILE, created_at=None):
    created_at = created_at or dt.datetime.now().isoformat(timespec="seconds")
    existing_rows = [row for row in read_findings(csv_file) if row.get("link_id") != link_id]
    new_rows = []

    for file_row in file_rows:
        for finding in analyze_file_row(file_row):
            new_rows.append(
                {
                    "id": next_finding_id(link_id, len(new_rows) + 1),
                    "link_id": link_id,
                    "file_id": file_row.get("id", ""),
                    "tool": "static-patterns",
                    "file_path": file_row.get("file_path", ""),
                    "line": finding["line"],
                    "category": finding["category"],
                    "severity": finding["severity"],
                    "status": "suspeito",
                    "message": finding["message"],
                    "evidence": finding["evidence"],
                    "created_at": created_at,
                }
            )

    rows = [*existing_rows, *new_rows]
    write_findings(rows, csv_file)
    return new_rows
