"""Resumo textual e tabelas de terminal do pipeline."""

import csv
import datetime as dt
import sys

from .paths import OUTPUT_DIR, REPORT_SUMMARY_FILE, sanitize_text

SUMMARY_HEADERS = {
    "tool": "Ferramenta",
    "expected_behavior": "Esperado",
    "expectation_match": "Comparacao",
    "classification": "Resultado",
    "count": "Qtd",
    "first_execution_date": "Primeira execucao",
    "latest_execution_date": "Ultima execucao",
}
EXPECTED_BEHAVIOR_LABELS = {
    "vulneravel": "Vulneravel",
    "correto": "Correto",
    "nao informado": "Nao informado",
}
EXPECTATION_MATCH_LABELS = {
    "conforme esperado": "Conforme",
    "divergente": "Divergente",
    "inconclusivo": "Inconclusivo",
    "nao avaliado": "Nao avaliado",
}
CLASSIFICATION_LABELS = {
    "detectado": "Detectado",
    "nao detectado": "Nao detectado",
    "erro de execucao": "Erro de execucao",
    "ferramenta indisponivel": "Ferramenta indisponivel",
}


def make_summary_path():
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"pipeline_{timestamp}.txt"


def write_summary(summary_path, results):
    with summary_path.open("w", encoding="utf-8") as summary_file:
        summary_file.write("Pipeline VSS-LLM - resumo da rodada\n")
        summary_file.write(f"gerado_em: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        summary_file.write(f"total_tarefas: {len(results)}\n\n")

        for item in results:
            summary_file.write(f"[{item['name']}]\n")
            summary_file.write(f"command: {' '.join(item['command'])}\n")
            summary_file.write(f"category: {item['category'] or 'N/A'}\n")
            summary_file.write(f"benchmark: {item['benchmark'] or 'N/A'}\n")
            summary_file.write(f"started_at: {item['started_at']}\n")
            summary_file.write(f"finished_at: {item['finished_at']}\n")
            summary_file.write(f"duration_seconds: {item['duration_seconds']:.3f}\n")
            summary_file.write(f"returncode: {item['returncode']}\n")
            if item["stdout"]:
                summary_file.write("stdout:\n")
                summary_file.write(sanitize_text(item["stdout"]))
                if not item["stdout"].endswith("\n"):
                    summary_file.write("\n")
            if item["stderr"]:
                summary_file.write("stderr:\n")
                summary_file.write(sanitize_text(item["stderr"]))
                if not item["stderr"].endswith("\n"):
                    summary_file.write("\n")
            summary_file.write("\n")


def format_summary_date(value):
    if not value:
        return "-"

    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return value

    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def format_summary_rows(rows):
    columns = [
        "tool",
        "expected_behavior",
        "expectation_match",
        "classification",
        "count",
        "first_execution_date",
        "latest_execution_date",
    ]
    labels = {key: SUMMARY_HEADERS[key] for key in columns}
    formatted_rows = []

    for row in rows:
        formatted_rows.append(
            {
                "tool": row.get("tool", "-") or "-",
                "expected_behavior": EXPECTED_BEHAVIOR_LABELS.get(
                    row.get("expected_behavior", ""),
                    row.get("expected_behavior", "-") or "-",
                ),
                "expectation_match": EXPECTATION_MATCH_LABELS.get(
                    row.get("expectation_match", ""),
                    row.get("expectation_match", "-") or "-",
                ),
                "classification": CLASSIFICATION_LABELS.get(
                    row.get("classification", ""),
                    row.get("classification", "-") or "-",
                ),
                "count": row.get("count", "0") or "0",
                "first_execution_date": format_summary_date(
                    row.get("first_execution_date", "")
                ),
                "latest_execution_date": format_summary_date(
                    row.get("latest_execution_date", "")
                ),
            }
        )

    widths = {
        column: max(
            len(labels[column]),
            *(len(row[column]) for row in formatted_rows),
        )
        for column in columns
    }
    header = " | ".join(labels[column].ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)
    lines = [header, separator]

    for row in formatted_rows:
        lines.append(" | ".join(row[column].ljust(widths[column]) for column in columns))

    return "\n".join(lines)


def print_report_summary(summary_file=REPORT_SUMMARY_FILE):
    try:
        with summary_file.open(encoding="utf-8", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))
    except OSError as exc:
        print(f"Nao foi possivel ler o resumo CSV: {exc}", file=sys.stderr)
        return

    if not rows:
        print("Resumo CSV vazio.")
        return

    print("\nResumo consolidado da rodada")
    print(format_summary_rows(rows))
