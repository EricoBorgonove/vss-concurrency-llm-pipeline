"""Fila de candidatos para analise futura por LLM."""

import csv
import datetime as dt
from pathlib import Path

from pipeline_runner.github_findings import read_findings
from pipeline_runner.paths import REPORTS_DIR

GITHUB_LLM_QUEUE_FILE = REPORTS_DIR / "github_llm_queue.csv"
QUEUE_FIELDS = [
    "id",
    "finding_id",
    "link_id",
    "file_path",
    "line",
    "category",
    "severity",
    "priority",
    "review_status",
    "selection_reason",
    "prompt",
    "created_at",
]


def selection_reason(row):
    status = row.get("status", "")
    priority = row.get("priority", "")
    if status == "confirmado":
        return "achado confirmado na revisao"
    if status == "suspeito" and priority == "alta":
        return "achado suspeito com prioridade alta"
    return ""


def should_select_finding(row):
    return bool(selection_reason(row))


def build_prompt(row):
    context = row.get("context", "").strip() or row.get("evidence", "").strip()
    return "\n".join(
        [
            "Analise o achado de seguranca abaixo em codigo C/C++.",
            "",
            f"Arquivo: {row.get('file_path', '')}",
            f"Linha: {row.get('line', '')}",
            f"Categoria: {row.get('category', '')}",
            f"Severidade: {row.get('severity', '')}",
            f"Prioridade: {row.get('priority', '')}",
            f"Status de revisao: {row.get('status', '')}",
            f"Mensagem: {row.get('message', '')}",
            "",
            "Contexto:",
            context,
            "",
            "Tarefas:",
            "1. Explique se o trecho indica vulnerabilidade real ou falso positivo.",
            "2. Liste quais condicoes tornam o caso exploravel ou seguro.",
            "3. Sugira uma correcao minima em C/C++ quando houver risco.",
            "4. Informe quais ferramentas poderiam validar a conclusao.",
        ]
    )


def next_queue_id(index):
    return f"llm_candidate_{index:06d}"


def build_queue_rows(findings, created_at=None, limit=None):
    created_at = created_at or dt.datetime.now().isoformat(timespec="seconds")
    selected = [row for row in findings if should_select_finding(row)]
    selected.sort(
        key=lambda row: (
            0 if row.get("status") == "confirmado" else 1,
            0 if row.get("priority") == "alta" else 1,
            row.get("link_id", ""),
            row.get("file_path", ""),
            int(row.get("line", "0") or "0"),
        )
    )
    if limit is not None:
        selected = selected[:limit]

    rows = []
    for index, finding in enumerate(selected, start=1):
        rows.append(
            {
                "id": next_queue_id(index),
                "finding_id": finding.get("id", ""),
                "link_id": finding.get("link_id", ""),
                "file_path": finding.get("file_path", ""),
                "line": finding.get("line", ""),
                "category": finding.get("category", ""),
                "severity": finding.get("severity", ""),
                "priority": finding.get("priority", ""),
                "review_status": finding.get("status", ""),
                "selection_reason": selection_reason(finding),
                "prompt": build_prompt(finding),
                "created_at": created_at,
            }
        )
    return rows


def write_queue(rows, csv_file=GITHUB_LLM_QUEUE_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_queue_from_findings(
    findings_file=None,
    output_file=GITHUB_LLM_QUEUE_FILE,
    created_at=None,
    limit=None,
):
    findings = read_findings(findings_file) if findings_file else read_findings()
    rows = build_queue_rows(findings, created_at=created_at, limit=limit)
    write_queue(rows, output_file)
    return rows
