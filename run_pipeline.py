#!/usr/bin/env python3
"""Executa uma rodada completa das ferramentas implementadas no pipeline."""

import csv
import datetime as dt
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "pipeline"
REPORT_SUMMARY_FILE = PROJECT_ROOT / "reports" / "summary.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"
BENCHMARK_METRICS_FILE = REPORTS_DIR / "benchmark_metrics.csv"
CATEGORY_METRICS_FILE = REPORTS_DIR / "category_metrics.csv"
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

BENCHMARK_RULES = {
    "assertion_violation": (("esbmc", "scripts/run_esbmc.py", ()),),
    "memory_corruption": (
        ("asan", "scripts/run_asan.py", ()),
        ("afl", "scripts/run_afl.py", ()),
    ),
    "data_race": (("tsan", "scripts/run_tsan.py", ()),),
    "deadlock": (("deadlock", "scripts/run_deadlock.py", ("--timeout", "3")),),
}


def display_path(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def sanitize_text(text):
    text = text.replace(str(PROJECT_ROOT) + "/", "")
    temp_pattern = r"/var" + r"/folders/\S+/T/vss-"
    text = re.sub(temp_pattern + r"[^/\s,;\"<>]+/(\S+)", r"<tmp>/\1", text)
    return re.sub(temp_pattern + r"[^\s,;\"<>]+", "<tmp>", text)


def is_experiment_benchmark(path):
    ignored_suffixes = ("_fixed.c", "_pass.c")
    return path.suffix == ".c" and not path.name.endswith(ignored_suffixes)


def discover_tasks(benchmarks_dir=PROJECT_ROOT / "benchmarks"):
    tasks = []
    for category, tools in BENCHMARK_RULES.items():
        category_dir = benchmarks_dir / category
        if not category_dir.is_dir():
            continue

        for benchmark_path in sorted(category_dir.glob("*.c")):
            if not is_experiment_benchmark(benchmark_path):
                continue

            relative_benchmark = benchmark_path.relative_to(PROJECT_ROOT)
            for tool_name, script_path, extra_args in tools:
                tasks.append(
                    {
                        "name": f"{tool_name}_{category}_{benchmark_path.stem}",
                        "kind": "benchmark",
                        "category": category,
                        "tool": tool_name,
                        "benchmark": str(relative_benchmark),
                        "command": [
                            script_path,
                            str(relative_benchmark),
                            *extra_args,
                        ],
                    }
                )

    return tasks


def build_environment_task():
    return {
        "name": "environment_check",
        "kind": "environment",
        "category": "",
        "tool": "",
        "benchmark": "",
        "command": ["scripts/check_environment.py"],
    }


def build_report_task():
    return {
        "name": "generate_latest_report",
        "kind": "report",
        "category": "",
        "tool": "",
        "benchmark": "",
        "command": [
            "scripts/generate_report.py",
            "--latest-only",
        ],
    }


def make_summary_path():
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"pipeline_{timestamp}.txt"


def run_task(task):
    command = [sys.executable, *task["command"]]
    started_at = dt.datetime.now()
    start_time = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    duration_seconds = time.perf_counter() - start_time
    finished_at = dt.datetime.now()
    return command, result, started_at, finished_at, duration_seconds


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


def collect_benchmark_metrics(results):
    return [
        {
            "run_date": item["started_at"],
            "category": item["category"],
            "tool": item["tool"],
            "benchmark": item["benchmark"],
            "task_name": item["name"],
            "duration_seconds": f"{item['duration_seconds']:.3f}",
            "returncode": item["returncode"],
        }
        for item in results
        if item["kind"] == "benchmark"
    ]


def build_category_metrics(benchmark_metrics):
    metrics = {}
    for row in benchmark_metrics:
        category = row["category"]
        item = metrics.setdefault(
            category,
            {
                "category": category,
                "execution_count": 0,
                "benchmark_count": set(),
                "total_duration_seconds": 0.0,
                "min_duration_seconds": None,
                "max_duration_seconds": None,
            },
        )
        duration = float(row["duration_seconds"])
        item["execution_count"] += 1
        item["benchmark_count"].add(row["benchmark"])
        item["total_duration_seconds"] += duration
        if item["min_duration_seconds"] is None or duration < item["min_duration_seconds"]:
            item["min_duration_seconds"] = duration
        if item["max_duration_seconds"] is None or duration > item["max_duration_seconds"]:
            item["max_duration_seconds"] = duration

    rows = []
    for item in sorted(metrics.values(), key=lambda value: value["category"]):
        execution_count = item["execution_count"]
        total_duration = item["total_duration_seconds"]
        rows.append(
            {
                "category": item["category"],
                "benchmark_count": len(item["benchmark_count"]),
                "execution_count": execution_count,
                "total_duration_seconds": f"{total_duration:.3f}",
                "avg_duration_seconds": f"{(total_duration / execution_count):.3f}",
                "min_duration_seconds": f"{item['min_duration_seconds']:.3f}",
                "max_duration_seconds": f"{item['max_duration_seconds']:.3f}",
            }
        )

    return rows


def write_dict_csv(rows, output_file, fieldnames):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metrics_reports(
    results,
    benchmark_metrics_file=BENCHMARK_METRICS_FILE,
    category_metrics_file=CATEGORY_METRICS_FILE,
):
    benchmark_metrics = collect_benchmark_metrics(results)
    category_metrics = build_category_metrics(benchmark_metrics)

    write_dict_csv(
        benchmark_metrics,
        benchmark_metrics_file,
        [
            "run_date",
            "category",
            "tool",
            "benchmark",
            "task_name",
            "duration_seconds",
            "returncode",
        ],
    )
    write_dict_csv(
        category_metrics,
        category_metrics_file,
        [
            "category",
            "benchmark_count",
            "execution_count",
            "total_duration_seconds",
            "avg_duration_seconds",
            "min_duration_seconds",
            "max_duration_seconds",
        ],
    )
    return benchmark_metrics, category_metrics


def format_category_metrics(rows):
    if not rows:
        return "Nenhuma metrica de categoria disponivel."

    columns = [
        "category",
        "benchmark_count",
        "execution_count",
        "total_duration_seconds",
        "avg_duration_seconds",
    ]
    labels = {
        "category": "Categoria",
        "benchmark_count": "Benchmarks",
        "execution_count": "Execucoes",
        "total_duration_seconds": "Duracao total",
        "avg_duration_seconds": "Duracao media",
    }
    formatted_rows = [
        {
            "category": row["category"],
            "benchmark_count": str(row["benchmark_count"]),
            "execution_count": str(row["execution_count"]),
            "total_duration_seconds": f"{row['total_duration_seconds']}s",
            "avg_duration_seconds": f"{row['avg_duration_seconds']}s",
        }
        for row in rows
    ]
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


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = make_summary_path()
    results = []

    benchmark_tasks = discover_tasks()
    if not benchmark_tasks:
        print("Nenhum benchmark .c encontrado para executar.", file=sys.stderr)
        return 1

    tasks = [build_environment_task(), *benchmark_tasks, build_report_task()]

    for task in tasks:
        print(f"Executando: {task['name']}")
        command, result, started_at, finished_at, duration_seconds = run_task(task)
        results.append(
            {
                "name": task["name"],
                "kind": task["kind"],
                "category": task["category"],
                "tool": task["tool"],
                "benchmark": task["benchmark"],
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "started_at": started_at.isoformat(timespec="seconds"),
                "finished_at": finished_at.isoformat(timespec="seconds"),
                "duration_seconds": duration_seconds,
            }
        )

    write_summary(summary_path, results)
    _, category_metrics = write_metrics_reports(results)
    print(f"Resumo salvo em: {display_path(summary_path)}")
    print(f"Metricas por benchmark salvas em: {display_path(BENCHMARK_METRICS_FILE)}")
    print(f"Metricas por categoria salvas em: {display_path(CATEGORY_METRICS_FILE)}")
    print_report_summary()
    print("\nMetricas por categoria")
    print(format_category_metrics(category_metrics))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
