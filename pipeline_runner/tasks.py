"""Descoberta e execucao de tarefas do pipeline."""

import datetime as dt
import subprocess
import sys
import time

from .analyzer import infer_tools_from_file
from .metadata import (
    applicable_tools_for,
    get_benchmark_metadata,
    include_in_pipeline,
    read_benchmark_metadata,
)
from .paths import PROJECT_ROOT

TOOL_COMMANDS = {
    "afl": ("scripts/run_afl.py", ()),
    "asan": ("scripts/run_asan.py", ()),
    "deadlock": ("scripts/run_deadlock.py", ("--timeout", "3")),
    "esbmc": ("scripts/run_esbmc.py", ()),
    "tsan": ("scripts/run_tsan.py", ()),
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


def tools_for_benchmark(benchmark_path, category, metadata):
    row = get_benchmark_metadata(benchmark_path, metadata)
    if row:
        return tuple(
            (tool, *TOOL_COMMANDS[tool])
            for tool in applicable_tools_for(benchmark_path, metadata)
            if tool in TOOL_COMMANDS
        )

    inferred_tools = infer_tools_from_file(benchmark_path)
    if inferred_tools:
        return tuple(
            (tool, *TOOL_COMMANDS[tool])
            for tool in inferred_tools
            if tool in TOOL_COMMANDS
        )

    return BENCHMARK_RULES.get(category, ())


def build_benchmark_task(tool_name, script_path, extra_args, category, benchmark_path):
    relative_benchmark = benchmark_path.relative_to(PROJECT_ROOT)
    return {
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


def discover_tasks(benchmarks_dir=PROJECT_ROOT / "benchmarks"):
    tasks = []
    metadata = read_benchmark_metadata()
    for benchmark_path in sorted(benchmarks_dir.glob("*/*.c")):
        category = benchmark_path.parent.name
        row = get_benchmark_metadata(benchmark_path, metadata)
        metadata_include = include_in_pipeline(benchmark_path, metadata)

        if row:
            category = row.get("category", category) or category
        if metadata_include is False:
            continue
        if metadata_include is None and not is_experiment_benchmark(benchmark_path):
            continue

        for tool_name, script_path, extra_args in tools_for_benchmark(
            benchmark_path,
            category,
            metadata,
        ):
            tasks.append(
                build_benchmark_task(
                    tool_name,
                    script_path,
                    extra_args,
                    category,
                    benchmark_path,
                )
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
