#!/usr/bin/env python3
"""Gera um relatorio CSV simples a partir dos logs em outputs/."""

import argparse
import csv
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


def parse_log(log_path):
    data = {
        "tool": "",
        "benchmark": "",
        "log_file": str(log_path.relative_to(PROJECT_ROOT)),
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
        key = (row["tool"], row["classification"])
        summary[key] = summary.get(key, 0) + 1

    return [
        {
            "tool": tool,
            "classification": classification,
            "count": count,
        }
        for (tool, classification), count in sorted(summary.items())
    ]


def write_summary_csv(rows, summary_output_file):
    summary_output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["tool", "classification", "count"]
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
