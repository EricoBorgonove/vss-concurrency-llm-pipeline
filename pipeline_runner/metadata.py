"""Leitura dos metadados auditaveis dos benchmarks."""

import csv
from pathlib import Path

from .paths import PROJECT_ROOT

BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
METADATA_FILE = BENCHMARKS_DIR / "metadata.csv"
EXPECTED_TOOL_COLUMNS = {
    "afl": "expected_afl",
    "asan": "expected_asan",
    "deadlock": "expected_deadlock",
    "esbmc": "expected_esbmc",
    "tsan": "expected_tsan",
}
NON_APPLICABLE_TOOL_VALUES = ("", "nao_aplicavel")


def normalize_benchmark_path(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except (OSError, ValueError):
        return str(path)


def read_benchmark_metadata(metadata_file=METADATA_FILE):
    if not Path(metadata_file).is_file():
        return {}

    with Path(metadata_file).open(encoding="utf-8", newline="") as csv_file:
        rows = {}
        for row in csv.DictReader(csv_file):
            benchmark = row.get("path", "").strip()
            if benchmark:
                rows[benchmark] = {key: value.strip() for key, value in row.items()}
        return rows


def get_benchmark_metadata(benchmark, metadata=None):
    metadata = metadata if metadata is not None else read_benchmark_metadata()
    return metadata.get(normalize_benchmark_path(benchmark), {})


def expected_behavior_for(benchmark, metadata=None):
    row = get_benchmark_metadata(benchmark, metadata)
    return row.get("expected_behavior", "")


def expected_tool_behavior_for(tool, benchmark, metadata=None):
    row = get_benchmark_metadata(benchmark, metadata)
    column = EXPECTED_TOOL_COLUMNS.get(tool)
    if not column:
        return ""
    return row.get(column, "")


def is_tool_applicable(expected_tool_behavior):
    return expected_tool_behavior not in NON_APPLICABLE_TOOL_VALUES


def applicable_tools_for(benchmark, metadata=None):
    row = get_benchmark_metadata(benchmark, metadata)
    return tuple(
        tool
        for tool, column in sorted(EXPECTED_TOOL_COLUMNS.items())
        if is_tool_applicable(row.get(column, ""))
    )


def include_in_pipeline(benchmark, metadata=None):
    row = get_benchmark_metadata(benchmark, metadata)
    if not row:
        return None
    return row.get("include_in_pipeline", "").lower() == "true"
