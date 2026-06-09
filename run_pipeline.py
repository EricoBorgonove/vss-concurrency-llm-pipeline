#!/usr/bin/env python3
"""Executa uma rodada completa das ferramentas implementadas no pipeline."""

import csv
import datetime as dt
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "pipeline"
REPORT_SUMMARY_FILE = PROJECT_ROOT / "reports" / "summary.csv"
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
        "command": ["scripts/check_environment.py"],
    }


def build_report_task():
    return {
        "name": "generate_latest_report",
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
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return command, result


def write_summary(summary_path, results):
    with summary_path.open("w", encoding="utf-8") as summary_file:
        summary_file.write("Pipeline VSS-LLM - resumo da rodada\n")
        summary_file.write(f"gerado_em: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        summary_file.write(f"total_tarefas: {len(results)}\n\n")

        for item in results:
            summary_file.write(f"[{item['name']}]\n")
            summary_file.write(f"command: {' '.join(item['command'])}\n")
            summary_file.write(f"returncode: {item['returncode']}\n")
            if item["stdout"]:
                summary_file.write("stdout:\n")
                summary_file.write(item["stdout"])
                if not item["stdout"].endswith("\n"):
                    summary_file.write("\n")
            if item["stderr"]:
                summary_file.write("stderr:\n")
                summary_file.write(item["stderr"])
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
        command, result = run_task(task)
        results.append(
            {
                "name": task["name"],
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )

    write_summary(summary_path, results)
    print(f"Resumo salvo em: {summary_path}")
    print_report_summary()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
