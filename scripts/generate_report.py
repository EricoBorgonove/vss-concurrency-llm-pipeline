#!/usr/bin/env python3
"""Gera um relatorio CSV simples a partir dos logs em outputs/."""

import argparse
import csv
import datetime as dt
import html
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_runner.metadata import (
    expected_behavior_for,
    expected_tool_behavior_for,
    read_benchmark_metadata,
)

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"
RESULTS_FILE = REPORTS_DIR / "results.csv"
SUMMARY_FILE = REPORTS_DIR / "summary.csv"
HTML_FILE = REPORTS_DIR / "report.html"
BENCHMARK_METRICS_FILE = REPORTS_DIR / "benchmark_metrics.csv"
CATEGORY_METRICS_FILE = REPORTS_DIR / "category_metrics.csv"
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
    "FATAL: ThreadSanitizer",
    "Tempo limite excedido",
    "falha na compilacao",
    "erro ao ler log",
)
LOG_TIMESTAMP_PATTERN = re.compile(r"_(\d{8}-\d{6})$")
EXPECTED_VULNERABLE_SUFFIXES = ("_error.c",)
EXPECTED_SAFE_SUFFIXES = ("_safe.c", "_fixed.c", "_pass.c")
PROJECT_ROOT_TEXT = str(PROJECT_ROOT)
TOOL_ALIASES = {"afl++": "afl", "deadlock-timeout": "deadlock"}


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
        "--html-output",
        default=str(HTML_FILE),
        help="Caminho do relatorio HTML. Padrao: reports/report.html.",
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
    tool = data.get("tool", "")

    if any(marker.lower() in text or marker.lower() in error for marker in UNAVAILABLE_MARKERS):
        return "ferramenta indisponivel"

    if "fatal: threadsanitizer" in text or "fatal: threadsanitizer" in error:
        return "erro de execucao"

    if any(marker.lower() in text for marker in DETECTED_MARKERS):
        return "detectado"

    if "tool: deadlock-timeout" in text and "returncode: 124" in text:
        return "detectado"

    if tool == "afl++":
        crashes_match = re.search(r"(\d+)\s+crashes saved", text)
        if crashes_match and int(crashes_match.group(1)) > 0:
            return "detectado"
        if (
            "program crashed with one of the test cases provided" in text
            or "results in a crash" in text
        ):
            return "detectado"
        if "time limit was reached" in text and "0 crashes saved" in text:
            return "inconclusivo"

    if any(marker.lower() in text or marker.lower() in error for marker in EXECUTION_ERROR_MARKERS):
        return "erro de execucao"

    if data["compile_returncode"] and data["compile_returncode"] != "0":
        return "erro de execucao"

    if data.get("run_returncode", "").startswith("-"):
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


def get_expected_behavior(benchmark, metadata=None):
    return expected_behavior_for(benchmark, metadata) or infer_expected_behavior(benchmark)


def normalize_tool_name(tool):
    return TOOL_ALIASES.get(tool, tool)


def get_expected_tool_behavior(tool, benchmark, metadata=None):
    expected = expected_tool_behavior_for(normalize_tool_name(tool), benchmark, metadata)
    return expected or "nao informado"


def normalize_project_path(value):
    if not value:
        return value

    project_prefix = PROJECT_ROOT_TEXT + "/"
    if value.startswith(project_prefix):
        return value.removeprefix(project_prefix)

    return value


def display_path(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def evaluate_expectation(expected_behavior, classification):
    if expected_behavior == "nao informado":
        return "nao avaliado"

    if classification in ("erro de execucao", "ferramenta indisponivel"):
        return "inconclusivo"
    if classification == "inconclusivo":
        return "inconclusivo"

    if expected_behavior == "vulneravel":
        return "conforme esperado" if classification == "detectado" else "divergente"

    if expected_behavior == "correto":
        return "conforme esperado" if classification == "nao detectado" else "divergente"

    return "nao avaliado"


def evaluate_tool_expectation(expected_tool_behavior, classification):
    if expected_tool_behavior in ("", "nao informado", "nao_aplicavel"):
        return "nao avaliado"

    if classification in ("erro de execucao", "ferramenta indisponivel"):
        return "inconclusivo"
    if classification == "inconclusivo":
        return "inconclusivo"

    if expected_tool_behavior == "inconclusivo":
        return "inconclusivo"

    if expected_tool_behavior == "detectar":
        return "conforme esperado" if classification == "detectado" else "divergente"

    if expected_tool_behavior == "nao_detectar":
        return "conforme esperado" if classification == "nao detectado" else "divergente"

    return "nao avaliado"


def parse_log(log_path, metadata=None):
    data = {
        "tool": "",
        "benchmark": "",
        "log_file": str(log_path.relative_to(PROJECT_ROOT)),
        "execution_date": extract_execution_date(log_path),
        "expected_behavior": "",
        "expectation_match": "",
        "expected_tool_behavior": "",
        "tool_expectation_match": "",
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
        data["expected_behavior"] = get_expected_behavior(data["benchmark"], metadata)
        data["expectation_match"] = evaluate_expectation(
            data["expected_behavior"],
            data["classification"],
        )
        data["expected_tool_behavior"] = get_expected_tool_behavior(
            data["tool"],
            data["benchmark"],
            metadata,
        )
        data["tool_expectation_match"] = evaluate_tool_expectation(
            data["expected_tool_behavior"],
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
            data["benchmark"] = normalize_project_path(
                line.removeprefix("benchmark: ").strip()
            )
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
    data["expected_behavior"] = get_expected_behavior(data["benchmark"], metadata)
    data["expectation_match"] = evaluate_expectation(
        data["expected_behavior"],
        data["classification"],
    )
    data["expected_tool_behavior"] = get_expected_tool_behavior(
        data["tool"],
        data["benchmark"],
        metadata,
    )
    data["tool_expectation_match"] = evaluate_tool_expectation(
        data["expected_tool_behavior"],
        data["classification"],
    )
    return data


def collect_rows(tools):
    rows = []
    metadata = read_benchmark_metadata()
    for tool in tools:
        tool_dir = OUTPUTS_DIR / tool
        if not tool_dir.is_dir():
            continue
        for log_path in sorted(tool_dir.glob("*.log")):
            rows.append(parse_log(log_path, metadata))
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
        "expected_tool_behavior",
        "tool_expectation_match",
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
            row.get("expected_tool_behavior", "nao informado"),
            row.get("tool_expectation_match", "nao avaliado"),
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
            "expected_tool_behavior": expected_tool_behavior,
            "tool_expectation_match": tool_expectation_match,
            "classification": classification,
            "count": item["count"],
            "first_execution_date": item["first_execution_date"],
            "latest_execution_date": item["latest_execution_date"],
        }
        for (
            tool,
            expected_behavior,
            expectation_match,
            expected_tool_behavior,
            tool_expectation_match,
            classification,
        ), item in sorted(summary.items())
    ]


def write_summary_csv(rows, summary_output_file):
    summary_output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tool",
        "expected_behavior",
        "expectation_match",
        "expected_tool_behavior",
        "tool_expectation_match",
        "classification",
        "count",
        "first_execution_date",
        "latest_execution_date",
    ]
    with summary_output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(build_summary(rows))


def read_csv_if_exists(path):
    if not path.is_file():
        return []

    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def escape(value):
    return html.escape(str(value), quote=True)


def render_html_table(rows, fieldnames):
    if not rows:
        return "<p>Nenhum registro encontrado.</p>"

    header_cells = "".join(f"<th>{escape(field)}</th>" for field in fieldnames)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape(row.get(field, ''))}</td>" for field in fieldnames)
        body_rows.append(f"<tr>{cells}</tr>")

    return (
        "<table>\n"
        f"<thead><tr>{header_cells}</tr></thead>\n"
        f"<tbody>{''.join(body_rows)}</tbody>\n"
        "</table>"
    )


def write_html_report(
    rows,
    html_output_file,
    category_metrics_rows=None,
    benchmark_metrics_rows=None,
):
    html_output_file.parent.mkdir(parents=True, exist_ok=True)
    summary_rows = build_summary(rows)
    category_metrics_rows = category_metrics_rows or []
    benchmark_metrics_rows = benchmark_metrics_rows or []
    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    summary_fields = [
        "tool",
        "expected_behavior",
        "expectation_match",
        "expected_tool_behavior",
        "tool_expectation_match",
        "classification",
        "count",
        "first_execution_date",
        "latest_execution_date",
    ]
    detail_fields = [
        "tool",
        "benchmark",
        "execution_date",
        "expected_behavior",
        "expectation_match",
        "expected_tool_behavior",
        "tool_expectation_match",
        "classification",
        "log_file",
        "error",
    ]
    category_metric_fields = [
        "category",
        "benchmark_count",
        "execution_count",
        "total_duration_seconds",
        "avg_duration_seconds",
        "min_duration_seconds",
        "max_duration_seconds",
    ]
    benchmark_metric_fields = [
        "run_date",
        "category",
        "tool",
        "benchmark",
        "duration_seconds",
        "returncode",
    ]
    content = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Relatorio Pipeline VSS-LLM</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 32px;
      color: #1f2933;
      background: #f7f9fb;
    }}
    h1, h2 {{
      margin-bottom: 8px;
    }}
    .meta {{
      color: #52606d;
      margin-bottom: 24px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 16px 0 32px;
      background: #ffffff;
      font-size: 14px;
    }}
    th, td {{
      border: 1px solid #d9e2ec;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #e4edf7;
      color: #102a43;
      position: sticky;
      top: 0;
    }}
    tr:nth-child(even) {{
      background: #f9fbfd;
    }}
    .note {{
      background: #ffffff;
      border-left: 4px solid #486581;
      padding: 12px 16px;
      margin-bottom: 24px;
    }}
  </style>
</head>
<body>
  <h1>Relatorio Pipeline VSS-LLM</h1>
  <p class="meta">Gerado em: {escape(generated_at)} | Logs processados: {len(rows)}</p>
  <div class="note">
    <strong>Leitura:</strong> <code>expected_behavior</code> indica se o benchmark era esperado
    como vulneravel, correto ou nao informado. <code>expectation_match</code> indica se o
    resultado observado ficou conforme, divergente, inconclusivo ou nao avaliado.
    <code>expected_tool_behavior</code> registra a expectativa especifica para a ferramenta.
  </div>
  <h2>Resumo</h2>
  {render_html_table(summary_rows, summary_fields)}
  <h2>Métricas por Categoria</h2>
  {render_html_table(category_metrics_rows, category_metric_fields)}
  <h2>Métricas por Benchmark</h2>
  {render_html_table(benchmark_metrics_rows, benchmark_metric_fields)}
  <h2>Resultados Detalhados</h2>
  {render_html_table(rows, detail_fields)}
</body>
</html>
"""
    html_output_file.write_text(content, encoding="utf-8")


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        tools = parse_tools(args.tools)
        results_file = Path(args.output)
        summary_file = Path(args.summary_output)
        html_file = Path(args.html_output)
        rows = collect_rows(tools)
        if args.latest_only:
            rows = filter_latest_rows(rows)
        category_metrics_rows = read_csv_if_exists(CATEGORY_METRICS_FILE)
        benchmark_metrics_rows = read_csv_if_exists(BENCHMARK_METRICS_FILE)
        write_csv(rows, results_file)
        write_summary_csv(rows, summary_file)
        write_html_report(
            rows,
            html_file,
            category_metrics_rows=category_metrics_rows,
            benchmark_metrics_rows=benchmark_metrics_rows,
        )
        print(f"Relatorio salvo em: {display_path(results_file)}")
        print(f"Resumo salvo em: {display_path(summary_file)}")
        print(f"Relatorio HTML salvo em: {display_path(html_file)}")
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
