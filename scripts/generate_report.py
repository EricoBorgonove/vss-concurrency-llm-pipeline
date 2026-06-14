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

    if tool == "tsan" and data.get("run_returncode") == "66":
        return "inconclusivo"

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


def benchmark_category(benchmark):
    parts = Path(benchmark).parts
    if "benchmarks" in parts:
        index = parts.index("benchmarks")
        if len(parts) > index + 1:
            return parts[index + 1]
    return ""


def dashboard_rows(rows):
    enriched_rows = []
    for row in rows:
        enriched = dict(row)
        enriched["category"] = benchmark_category(row.get("benchmark", ""))
        enriched_rows.append(enriched)
    return enriched_rows


def build_category_metrics_from_rows(rows):
    metrics = {}
    for row in rows:
        category = row.get("category") or benchmark_category(row.get("benchmark", ""))
        if not category:
            category = "nao informado"
        item = metrics.setdefault(
            category,
            {
                "benchmarks": set(),
                "execution_count": 0,
            },
        )
        benchmark = row.get("benchmark", "")
        if benchmark:
            item["benchmarks"].add(benchmark)
        item["execution_count"] += 1

    return [
        {
            "category": category,
            "benchmark_count": len(item["benchmarks"]),
            "execution_count": item["execution_count"],
            "total_duration_seconds": "nao informado",
            "avg_duration_seconds": "nao informado",
            "min_duration_seconds": "nao informado",
            "max_duration_seconds": "nao informado",
        }
        for category, item in sorted(metrics.items())
    ]


def build_benchmark_metrics_from_rows(rows):
    return [
        {
            "run_date": row.get("execution_date", ""),
            "category": row.get("category") or benchmark_category(row.get("benchmark", "")),
            "tool": row.get("tool", ""),
            "benchmark": row.get("benchmark", ""),
            "duration_seconds": "nao informado",
            "returncode": row.get("run_returncode") or row.get("returncode", ""),
        }
        for row in sorted(
            rows,
            key=lambda item: (
                item.get("category") or benchmark_category(item.get("benchmark", "")),
                item.get("tool", ""),
                item.get("benchmark", ""),
            ),
        )
    ]


def unique_values(rows, field):
    return sorted({row.get(field, "") for row in rows if row.get(field, "")})


def render_options(values):
    return "".join(f"<option value=\"{escape(value)}\">{escape(value)}</option>" for value in values)


def render_dashboard_cards(rows):
    total = len(rows)
    detected = sum(1 for row in rows if row.get("classification") == "detectado")
    not_detected = sum(1 for row in rows if row.get("classification") == "nao detectado")
    inconclusive = sum(1 for row in rows if row.get("classification") == "inconclusivo")
    divergent = sum(
        1
        for row in rows
        if row.get("expectation_match") == "divergente"
        or row.get("tool_expectation_match") == "divergente"
    )
    execution_errors = sum(1 for row in rows if row.get("classification") == "erro de execucao")
    cards = [
        ("Execucoes", total, "Total de resultados consolidados"),
        ("Detectados", detected, "Problemas observados pelas ferramentas"),
        ("Nao detectados", not_detected, "Casos sem evidencia de falha"),
        ("Inconclusivos", inconclusive, "Resultados sem conclusao suficiente"),
        ("Divergentes", divergent, "Resultados contra a expectativa"),
        ("Erros", execution_errors, "Falhas operacionais de execucao"),
    ]
    return "".join(
        "<section class=\"metric-card\">"
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(value)}</strong>"
        f"<small>{escape(description)}</small>"
        "</section>"
        for label, value, description in cards
    )


def render_filter_controls(rows):
    return f"""
    <section class="filters" aria-label="Filtros do dashboard">
      <label>Ferramenta
        <select id="filter-tool">
          <option value="">Todas</option>
          {render_options(unique_values(rows, "tool"))}
        </select>
      </label>
      <label>Categoria
        <select id="filter-category">
          <option value="">Todas</option>
          {render_options(unique_values(rows, "category"))}
        </select>
      </label>
      <label>Classificacao
        <select id="filter-classification">
          <option value="">Todas</option>
          {render_options(unique_values(rows, "classification"))}
        </select>
      </label>
      <label>Comparacao
        <select id="filter-match">
          <option value="">Todas</option>
          {render_options(unique_values(rows, "expectation_match"))}
        </select>
      </label>
      <label>Busca
        <input id="filter-search" type="search" placeholder="benchmark, log ou erro">
      </label>
      <button id="clear-filters" type="button">Limpar</button>
      <output id="visible-count">{len(rows)} registros visiveis</output>
    </section>
    """


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


def render_dashboard_detail_table(rows, fieldnames):
    if not rows:
        return "<p>Nenhum registro encontrado.</p>"

    header_cells = "".join(f"<th>{escape(field)}</th>" for field in fieldnames)
    body_rows = []
    for row in rows:
        search_text = " ".join(str(row.get(field, "")) for field in fieldnames)
        cells = []
        for field in fieldnames:
            value = row.get(field, "")
            if field == "log_file" and value:
                href = f"../{value}" if str(value).startswith("outputs/") else str(value)
                cells.append(f"<td><a href=\"{escape(href)}\">{escape(value)}</a></td>")
            else:
                cells.append(f"<td>{escape(value)}</td>")
        body_rows.append(
            "<tr "
            f"data-tool=\"{escape(row.get('tool', ''))}\" "
            f"data-category=\"{escape(row.get('category', ''))}\" "
            f"data-classification=\"{escape(row.get('classification', ''))}\" "
            f"data-match=\"{escape(row.get('expectation_match', ''))}\" "
            f"data-search=\"{escape(search_text.lower())}\">"
            f"{''.join(cells)}</tr>"
        )

    return (
        "<table id=\"detail-table\">\n"
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
    rows = dashboard_rows(rows)
    category_metrics_rows = category_metrics_rows or build_category_metrics_from_rows(rows)
    benchmark_metrics_rows = benchmark_metrics_rows or build_benchmark_metrics_from_rows(rows)
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
        "category",
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
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard Pipeline VSS-LLM</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3f6f8;
      --surface: #ffffff;
      --line: #d9e2ec;
      --text: #1f2933;
      --muted: #52606d;
      --accent: #2563eb;
      --header: #e4edf7;
    }}
    body {{
      font-family: Inter, Arial, sans-serif;
      margin: 0;
      color: var(--text);
      background: var(--bg);
    }}
    main {{
      width: min(1440px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }}
    h1, h2 {{
      margin-bottom: 8px;
    }}
    h1 {{
      font-size: 28px;
    }}
    .meta {{
      color: var(--muted);
      margin-bottom: 24px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin: 18px 0 24px;
    }}
    .metric-card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric-card span, .metric-card small {{
      color: var(--muted);
      display: block;
    }}
    .metric-card strong {{
      display: block;
      font-size: 28px;
      margin: 6px 0;
    }}
    .filters {{
      align-items: end;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      margin: 16px 0 24px;
      padding: 14px;
    }}
    label {{
      color: var(--muted);
      display: grid;
      font-size: 13px;
      gap: 6px;
    }}
    select, input, button {{
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--text);
      font: inherit;
      min-height: 36px;
      padding: 7px 9px;
    }}
    button {{
      background: var(--accent);
      border-color: var(--accent);
      color: #ffffff;
      cursor: pointer;
    }}
    output {{
      color: var(--muted);
      min-height: 36px;
      padding: 9px 0;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 16px 0 32px;
      background: var(--surface);
      font-size: 14px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--header);
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
    a {{
      color: var(--accent);
    }}
  </style>
</head>
<body>
  <main>
    <h1>Dashboard Pipeline VSS-LLM</h1>
    <p class="meta">Gerado em: {escape(generated_at)} | Logs processados: {len(rows)}</p>
    <div class="note">
      <strong>Leitura:</strong> <code>expected_behavior</code> indica se o benchmark era esperado
      como vulneravel, correto ou nao informado. <code>expectation_match</code> indica se o
      resultado observado ficou conforme, divergente, inconclusivo ou nao avaliado.
      <code>expected_tool_behavior</code> registra a expectativa especifica para a ferramenta.
    </div>
    <section class="cards" aria-label="Indicadores principais">
      {render_dashboard_cards(rows)}
    </section>
    <h2>Resultados Detalhados</h2>
    {render_filter_controls(rows)}
    <div class="table-wrap">
      {render_dashboard_detail_table(rows, detail_fields)}
    </div>
    <h2>Resumo</h2>
    <div class="table-wrap">{render_html_table(summary_rows, summary_fields)}</div>
    <h2>Metricas por Categoria</h2>
    <div class="table-wrap">{render_html_table(category_metrics_rows, category_metric_fields)}</div>
    <h2>Metricas por Benchmark</h2>
    <div class="table-wrap">{render_html_table(benchmark_metrics_rows, benchmark_metric_fields)}</div>
  </main>
  <script>
    const filters = {{
      tool: document.getElementById('filter-tool'),
      category: document.getElementById('filter-category'),
      classification: document.getElementById('filter-classification'),
      match: document.getElementById('filter-match'),
      search: document.getElementById('filter-search')
    }};
    const rows = Array.from(document.querySelectorAll('#detail-table tbody tr'));
    const visibleCount = document.getElementById('visible-count');

    function normalize(value) {{
      return (value || '').toString().toLowerCase();
    }}

    function applyFilters() {{
      const selected = {{
        tool: filters.tool.value,
        category: filters.category.value,
        classification: filters.classification.value,
        match: filters.match.value,
        search: normalize(filters.search.value)
      }};
      let visible = 0;
      rows.forEach((row) => {{
        const matches =
          (!selected.tool || row.dataset.tool === selected.tool) &&
          (!selected.category || row.dataset.category === selected.category) &&
          (!selected.classification || row.dataset.classification === selected.classification) &&
          (!selected.match || row.dataset.match === selected.match) &&
          (!selected.search || normalize(row.dataset.search).includes(selected.search));
        row.style.display = matches ? '' : 'none';
        if (matches) visible += 1;
      }});
      visibleCount.value = `${{visible}} registros visiveis`;
    }}

    Object.values(filters).forEach((field) => {{
      field.addEventListener('input', applyFilters);
      field.addEventListener('change', applyFilters);
    }});
    document.getElementById('clear-filters').addEventListener('click', () => {{
      Object.values(filters).forEach((field) => field.value = '');
      applyFilters();
    }});
    applyFilters();
  </script>
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
