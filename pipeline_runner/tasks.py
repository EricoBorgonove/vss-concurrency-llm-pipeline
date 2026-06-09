"""Descoberta e execucao de tarefas do pipeline."""

import datetime as dt
import subprocess
import sys
import time

from .paths import PROJECT_ROOT

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
