"""Fluxo principal da rodada completa do pipeline."""

import sys

from .metrics import format_category_metrics, write_metrics_reports
from .paths import (
    BENCHMARK_METRICS_FILE,
    CATEGORY_METRICS_FILE,
    OUTPUT_DIR,
    display_path,
)
from .summary import make_summary_path, print_report_summary, write_summary
from .tasks import build_environment_task, build_report_task, discover_tasks, run_task


def build_result_record(task, command, result, started_at, finished_at, duration_seconds):
    return {
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
            build_result_record(
                task,
                command,
                result,
                started_at,
                finished_at,
                duration_seconds,
            )
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
