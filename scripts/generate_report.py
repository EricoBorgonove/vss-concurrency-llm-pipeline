#!/usr/bin/env python3
"""Gera um relatorio CSV simples a partir dos logs em outputs/."""

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"
RESULTS_FILE = REPORTS_DIR / "results.csv"
SUMMARY_FILE = REPORTS_DIR / "summary.csv"
TOOLS = ("esbmc", "asan", "tsan", "deadlock", "afl")
DETECTED_MARKERS = (
    "AddressSanitizer:",
    "ThreadSanitizer:",
    "VERIFICATION FAILED",
    "Violated property",
    "data race",
    "heap-buffer-overflow",
    "tempo limite excedido",
)
UNAVAILABLE_MARKERS = (
    "executavel esbmc nao encontrado",
    "compilador c nao encontrado",
    "ferramenta afl++ nao encontrada",
)
EXECUTION_ERROR_MARKERS = (
    "PARSING ERROR",
    "No solver backends built into ESBMC",
    "Tempo limite excedido",
    "falha na compilacao",
    "erro ao ler log",
)
LOG_TIMESTAMP_PATTERN = re.compile(r"_(\d{8}-\d{6})$")
EXPECTED_VULNERABLE_SUFFIXES = ("_error.c",)
EXPECTED_SAFE_SUFFIXES = ("_safe.c", "_fixed.c", "_pass.c")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Gera CSVs consolidados a partir dos logs do pipeline."
    )
    parser.add_argument(
        "--tools",
        default=",".join(TOOLS),
        help="Lista de ferramentas separadas por virgula. Padrao: todas.",
    )
    parser.add_argument(
        "--output",
        default=str(RESULTS_FILE),
        help="Caminho do CSV detalhado. Padrao: reports/results.csv.",
    )
    parser.add_argument(
        "--summary-output",
        default=str(SUMMARY_FILE),
        help="Caminho do CSV resumido. Padrao: reports/summary.csv.",
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Considera apenas o log mais recente por ferramenta e benchmark.",
    )
    return parser


def parse_tools(tools_arg):
    selected_tools = tuple(tool.strip() for tool in tools_arg.split(",") if tool.strip())
    invalid_tools = [tool for tool in selected_tools if tool not in TOOLS]
    if invalid_tools:
        raise ValueError(f"ferramenta(s) desconhecida(s): {', '.join(invalid_tools)}")
    return selected_tools


def classify_result(log_text, data):
    text = log_text.lower()
    error = data["error"].lower()

    if any(marker.lower() in text or marker.lower() in error for marker in UNAVAILABLE_MARKERS):
        return "ferramenta indisponivel"

    if any(marker.lower() in text for marker in DETECTED_MARKERS):
        return "detectado"

    if "tool: deadlock-timeout" in text and "returncode: 124" in text:
        return "detectado"

    if any(marker.lower() in text or marker.lower() in error for marker in EXECUTION_ERROR_MARKERS):
        return "erro de execucao"

    if data["compile_returncode"] and data["compile_returncode"] != "0":
        return "erro de execucao"

    return "nao detectado"


def extract_execution_date(log_path):
    match = LOG_TIMESTAMP_PATTERN.search(log_path.stem)
    if not match:
        return ""

    timestamp = dt.datetime.strptime(match.group(1), "%Y%m%d-%H%M%S")
    return timestamp.isoformat(timespec="seconds")


def infer_expected_behavior(benchmark):
    name = Path(benchmark).name
    if name.endswith(EXPECTED_VULNERABLE_SUFFIXES):
        return "vulneravel"
    if name.endswith(EXPECTED_SAFE_SUFFIXES):
        return "correto"
    return "nao informado"


def evaluate_expectation(expected_behavior, classification):
    if expected_behavior == "nao informado":
        return "nao avaliado"

    if classification in ("erro de execucao", "ferramenta indisponivel"):
        return "inconclusivo"

    if expected_behavior == "vulneravel":
        return "conforme esperado" if classification == "detectado" else "divergente"

    if expected_behavior == "correto":
        return "conforme esperado" if classification == "nao detectado" else "divergente"

    return "nao avaliado"


def parse_log(log_path):
    data = {
        "tool": "",
        "benchmark": "",
        "log_file": str(log_path.relative_to(PROJECT_ROOT)),
        "execution_date": extract_execution_date(log_path),
        "expected_behavior": "",
        "expectation_match": "",
        "returncode": "",
        "compile_returncode": "",
        "run_returncode": "",
        "classification": "",
        "error": "",
    }
    section = "header"

    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        data["error"] = f"erro ao ler log: {exc}"
        data["classification"] = classify_result("", data)
        data["expected_behavior"] = infer_expected_behavior(data["benchmark"])
        data["expectation_match"] = evaluate_expectation(
            data["expected_behavior"],
            data["classification"],
        )
        return data

    log_text = "\n".join(lines)

    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]")
            continue

        if line.startswith("tool: "):
            data["tool"] = line.removeprefix("tool: ").strip()
            continue

        if line.startswith("benchmark: "):
            data["benchmark"] = line.removeprefix("benchmark: ").strip()
            continue

        if line.startswith("returncode: "):
            value = line.removeprefix("returncode: ").strip()
            if section == "compile":
                data["compile_returncode"] = value
            elif section in ("run", "fuzz"):
                data["run_returncode"] = value
            elif not data["returncode"]:
                data["returncode"] = value
            continue

        if section == "error" and line.strip():
            data["error"] = line.strip()
            section = "error_captured"

    data["classification"] = classify_result(log_text, data)
    data["expected_behavior"] = infer_expected_behavior(data["benchmark"])
    data["expectation_match"] = evaluate_expectation(
        data["expected_behavior"],
        data["classification"],
    )
    return data


def collect_rows(tools):
    rows = []
    for tool in tools:
        tool_dir = OUTPUTS_DIR / tool
        if not tool_dir.is_dir():
            continue
        for log_path in sorted(tool_dir.glob("*.log")):
            rows.append(parse_log(log_path))
    return rows


def filter_latest_rows(rows):
    latest_rows = {}
    for row in rows:
        key = (row["tool"], row["benchmark"])
        current = latest_rows.get(key)
        if current is None or row["log_file"] > current["log_file"]:
            latest_rows[key] = row

    return sorted(latest_rows.values(), key=lambda row: (row["tool"], row["benchmark"]))


def write_csv(rows, output_file):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tool",
        "benchmark",
        "log_file",
        "execution_date",
        "expected_behavior",
        "expectation_match",
        "returncode",
        "compile_returncode",
        "run_returncode",
        "classification",
        "error",
    ]
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows):
    summary = {}
    for row in rows:
        key = (
            row["tool"],
            row.get("expected_behavior", "nao informado"),
            row.get("expectation_match", "nao avaliado"),
            row["classification"],
        )
        if key not in summary:
            summary[key] = {
                "count": 0,
                "first_execution_date": "",
                "latest_execution_date": "",
            }

        item = summary[key]
        item["count"] += 1
        execution_date = row.get("execution_date", "")
        if execution_date:
            if not item["first_execution_date"] or execution_date < item["first_execution_date"]:
                item["first_execution_date"] = execution_date
            if not item["latest_execution_date"] or execution_date > item["latest_execution_date"]:
                item["latest_execution_date"] = execution_date

    return [
        {
            "tool": tool,
            "expected_behavior": expected_behavior,
            "expectation_match": expectation_match,
            "classification": classification,
            "count": item["count"],
            "first_execution_date": item["first_execution_date"],
            "latest_execution_date": item["latest_execution_date"],
        }
        for (tool, expected_behavior, expectation_match, classification), item in sorted(
            summary.items()
        )
    ]


def write_summary_csv(rows, summary_output_file):
    summary_output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tool",
        "expected_behavior",
        "expectation_match",
        "classification",
        "count",
        "first_execution_date",
        "latest_execution_date",
    ]
    with summary_output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(build_summary(rows))


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        tools = parse_tools(args.tools)
        results_file = Path(args.output)
        summary_file = Path(args.summary_output)
        rows = collect_rows(tools)
        if args.latest_only:
            rows = filter_latest_rows(rows)
        write_csv(rows, results_file)
        write_summary_csv(rows, summary_file)
        print(f"Relatorio salvo em: {results_file}")
        print(f"Resumo salvo em: {summary_file}")
        print(f"Total de logs processados: {len(rows)}")
        return 0
    except Exception as exc:
        print(f"Erro ao gerar relatorio: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
