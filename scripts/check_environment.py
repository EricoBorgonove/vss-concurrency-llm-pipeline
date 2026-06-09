#!/usr/bin/env python3
"""Registra diagnostico basico do ambiente de execucao do pipeline."""

import datetime as dt
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "environment"
TOOLS = {
    "clang": ["clang", "--version"],
    "gcc": ["gcc", "--version"],
    "esbmc": ["esbmc", "--version"],
    "afl-clang-fast": ["afl-clang-fast", "--version"],
    "afl-fuzz": ["afl-fuzz", "-h"],
}


def display_path(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def make_output_path():
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"environment_{timestamp}.txt"


def run_probe(command):
    executable = command[0]
    executable_path = shutil.which(executable)
    if executable_path is None:
        return {
            "available": False,
            "path": "",
            "returncode": "",
            "output": "not found",
        }

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = (result.stdout or result.stderr).strip().splitlines()
        return {
            "available": True,
            "path": executable_path,
            "returncode": str(result.returncode),
            "output": output[0] if output else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "path": executable_path,
            "returncode": "124",
            "output": "timeout while probing",
        }
    except OSError as exc:
        return {
            "available": True,
            "path": executable_path,
            "returncode": "1",
            "output": str(exc),
        }


def write_report(output_path, probes):
    with output_path.open("w", encoding="utf-8") as report:
        report.write("Pipeline VSS-LLM - environment diagnostics\n")
        report.write(f"generated_at: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        report.write(f"python: {sys.version.split()[0]}\n")
        report.write(f"platform: {platform.platform()}\n")
        report.write(f"machine: {platform.machine()}\n\n")

        for tool_name, probe in probes.items():
            report.write(f"[{tool_name}]\n")
            report.write(f"available: {probe['available']}\n")
            report.write(f"path: {probe['path'] or 'N/A'}\n")
            report.write(f"returncode: {probe['returncode'] or 'N/A'}\n")
            report.write(f"output: {probe['output'] or 'N/A'}\n\n")

        report.write("notes:\n")
        report.write("- Sanitizers and ESBMC may depend on platform-specific runtime support.\n")
        report.write("- On macOS, ASAN/TSAN and ESBMC solver availability should be checked before experiments.\n")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = make_output_path()
    probes = {tool_name: run_probe(command) for tool_name, command in TOOLS.items()}
    write_report(output_path, probes)
    print(f"Diagnostico salvo em: {display_path(output_path)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
