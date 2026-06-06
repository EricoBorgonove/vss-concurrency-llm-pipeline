#!/usr/bin/env python3
"""Executa uma rodada basica das ferramentas implementadas no pipeline."""

import datetime as dt
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "pipeline"

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


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = make_summary_path()
    results = []

    tasks = discover_tasks()
    if not tasks:
        print("Nenhum benchmark .c encontrado para executar.", file=sys.stderr)
        return 1

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
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
