#!/usr/bin/env python3
"""Executa uma rodada completa das ferramentas implementadas no pipeline."""

import sys

from pipeline_runner.metrics import (
    build_category_metrics,
    collect_benchmark_metrics,
    format_category_metrics,
    write_metrics_reports,
)
from pipeline_runner.paths import (
    BENCHMARK_METRICS_FILE,
    CATEGORY_METRICS_FILE,
    OUTPUT_DIR,
    PROJECT_ROOT,
    REPORT_SUMMARY_FILE,
    REPORTS_DIR,
    display_path,
    sanitize_text,
)
from pipeline_runner.runner import build_result_record, main
from pipeline_runner.summary import (
    format_summary_date,
    format_summary_rows,
    make_summary_path,
    print_report_summary,
    write_summary,
)
from pipeline_runner.tasks import (
    BENCHMARK_RULES,
    build_environment_task,
    build_report_task,
    discover_tasks,
    is_experiment_benchmark,
    run_task,
)

__all__ = [
    "BENCHMARK_METRICS_FILE",
    "BENCHMARK_RULES",
    "CATEGORY_METRICS_FILE",
    "OUTPUT_DIR",
    "PROJECT_ROOT",
    "REPORTS_DIR",
    "REPORT_SUMMARY_FILE",
    "build_category_metrics",
    "build_environment_task",
    "build_report_task",
    "build_result_record",
    "collect_benchmark_metrics",
    "discover_tasks",
    "display_path",
    "format_category_metrics",
    "format_summary_date",
    "format_summary_rows",
    "is_experiment_benchmark",
    "main",
    "make_summary_path",
    "print_report_summary",
    "run_task",
    "sanitize_text",
    "write_metrics_reports",
    "write_summary",
]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
