#!/usr/bin/env python3
"""Executa uma rodada basica das ferramentas implementadas no pipeline."""

import datetime as dt
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "pipeline"

TASKS = [
    {
        "name": "esbmc_assertion_violation",
        "command": [
            "scripts/run_esbmc.py",
            "benchmarks/assertion_violation/simple_assert_fail.c",
        ],
    },
    {
        "name": "asan_buffer_overflow",
        "command": [
            "scripts/run_asan.py",
            "benchmarks/memory_corruption/simple_buffer_overflow.c",
        ],
    },
    {
        "name": "tsan_data_race",
        "command": [
            "scripts/run_tsan.py",
            "benchmarks/data_race/simple_data_race.c",
        ],
    },
    {
        "name": "afl_buffer_overflow",
        "command": [
            "scripts/run_afl.py",
            "benchmarks/memory_corruption/simple_buffer_overflow.c",
        ],
    },
]


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

    for task in TASKS:
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
