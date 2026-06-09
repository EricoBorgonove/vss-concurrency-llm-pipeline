"""Caminhos compartilhados e sanitizacao de texto."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "pipeline"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORT_SUMMARY_FILE = REPORTS_DIR / "summary.csv"
BENCHMARK_METRICS_FILE = REPORTS_DIR / "benchmark_metrics.csv"
CATEGORY_METRICS_FILE = REPORTS_DIR / "category_metrics.csv"


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
