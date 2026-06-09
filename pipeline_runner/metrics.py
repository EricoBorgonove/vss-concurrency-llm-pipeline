"""Metricas de execucao por benchmark e categoria."""

import csv

from .paths import BENCHMARK_METRICS_FILE, CATEGORY_METRICS_FILE


def collect_benchmark_metrics(results):
    return [
        {
            "run_date": item["started_at"],
            "category": item["category"],
            "tool": item["tool"],
            "benchmark": item["benchmark"],
            "task_name": item["name"],
            "duration_seconds": f"{item['duration_seconds']:.3f}",
            "returncode": item["returncode"],
        }
        for item in results
        if item["kind"] == "benchmark"
    ]


def build_category_metrics(benchmark_metrics):
    metrics = {}
    for row in benchmark_metrics:
        category = row["category"]
        item = metrics.setdefault(
            category,
            {
                "category": category,
                "execution_count": 0,
                "benchmark_count": set(),
                "total_duration_seconds": 0.0,
                "min_duration_seconds": None,
                "max_duration_seconds": None,
            },
        )
        duration = float(row["duration_seconds"])
        item["execution_count"] += 1
        item["benchmark_count"].add(row["benchmark"])
        item["total_duration_seconds"] += duration
        if item["min_duration_seconds"] is None or duration < item["min_duration_seconds"]:
            item["min_duration_seconds"] = duration
        if item["max_duration_seconds"] is None or duration > item["max_duration_seconds"]:
            item["max_duration_seconds"] = duration

    rows = []
    for item in sorted(metrics.values(), key=lambda value: value["category"]):
        execution_count = item["execution_count"]
        total_duration = item["total_duration_seconds"]
        rows.append(
            {
                "category": item["category"],
                "benchmark_count": len(item["benchmark_count"]),
                "execution_count": execution_count,
                "total_duration_seconds": f"{total_duration:.3f}",
                "avg_duration_seconds": f"{(total_duration / execution_count):.3f}",
                "min_duration_seconds": f"{item['min_duration_seconds']:.3f}",
                "max_duration_seconds": f"{item['max_duration_seconds']:.3f}",
            }
        )

    return rows


def write_dict_csv(rows, output_file, fieldnames):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metrics_reports(
    results,
    benchmark_metrics_file=BENCHMARK_METRICS_FILE,
    category_metrics_file=CATEGORY_METRICS_FILE,
):
    benchmark_metrics = collect_benchmark_metrics(results)
    category_metrics = build_category_metrics(benchmark_metrics)

    write_dict_csv(
        benchmark_metrics,
        benchmark_metrics_file,
        [
            "run_date",
            "category",
            "tool",
            "benchmark",
            "task_name",
            "duration_seconds",
            "returncode",
        ],
    )
    write_dict_csv(
        category_metrics,
        category_metrics_file,
        [
            "category",
            "benchmark_count",
            "execution_count",
            "total_duration_seconds",
            "avg_duration_seconds",
            "min_duration_seconds",
            "max_duration_seconds",
        ],
    )
    return benchmark_metrics, category_metrics


def format_category_metrics(rows):
    if not rows:
        return "Nenhuma metrica de categoria disponivel."

    columns = [
        "category",
        "benchmark_count",
        "execution_count",
        "total_duration_seconds",
        "avg_duration_seconds",
    ]
    labels = {
        "category": "Categoria",
        "benchmark_count": "Benchmarks",
        "execution_count": "Execucoes",
        "total_duration_seconds": "Duracao total",
        "avg_duration_seconds": "Duracao media",
    }
    formatted_rows = [
        {
            "category": row["category"],
            "benchmark_count": str(row["benchmark_count"]),
            "execution_count": str(row["execution_count"]),
            "total_duration_seconds": f"{row['total_duration_seconds']}s",
            "avg_duration_seconds": f"{row['avg_duration_seconds']}s",
        }
        for row in rows
    ]
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
