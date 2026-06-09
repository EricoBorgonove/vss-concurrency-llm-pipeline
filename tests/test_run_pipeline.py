import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import run_pipeline


class RunPipelineTest(unittest.TestCase):
    def test_is_experiment_benchmark_ignores_fixed_variants(self):
        self.assertTrue(run_pipeline.is_experiment_benchmark(Path("sample.c")))
        self.assertFalse(run_pipeline.is_experiment_benchmark(Path("sample_fixed.c")))
        self.assertFalse(run_pipeline.is_experiment_benchmark(Path("sample_pass.c")))
        self.assertFalse(run_pipeline.is_experiment_benchmark(Path("sample.txt")))

    def test_discover_tasks_includes_current_benchmarks(self):
        tasks = run_pipeline.discover_tasks()
        task_names = {task["name"] for task in tasks}

        self.assertIn(
            "esbmc_assertion_violation_simple_assert_fail",
            task_names,
        )
        self.assertIn(
            "asan_memory_corruption_simple_buffer_overflow",
            task_names,
        )
        self.assertIn(
            "afl_memory_corruption_simple_buffer_overflow",
            task_names,
        )
        self.assertIn(
            "tsan_data_race_simple_data_race",
            task_names,
        )
        self.assertIn(
            "deadlock_deadlock_simple_deadlock",
            task_names,
        )
        self.assertNotIn(
            "asan_memory_corruption_simple_buffer_overflow_fixed",
            task_names,
        )
        self.assertNotIn(
            "esbmc_assertion_violation_simple_assert_pass",
            task_names,
        )
        simple_asan = next(
            task
            for task in tasks
            if task["name"] == "asan_memory_corruption_simple_buffer_overflow"
        )
        self.assertEqual(simple_asan["kind"], "benchmark")
        self.assertEqual(simple_asan["category"], "memory_corruption")
        self.assertEqual(simple_asan["tool"], "asan")
        self.assertEqual(
            simple_asan["benchmark"],
            "benchmarks/memory_corruption/simple_buffer_overflow.c",
        )

    def test_build_environment_task_runs_environment_check(self):
        task = run_pipeline.build_environment_task()

        self.assertEqual(task["name"], "environment_check")
        self.assertEqual(task["kind"], "environment")
        self.assertEqual(task["command"], ["scripts/check_environment.py"])

    def test_build_report_task_generates_latest_report(self):
        task = run_pipeline.build_report_task()

        self.assertEqual(task["name"], "generate_latest_report")
        self.assertEqual(task["kind"], "report")
        self.assertEqual(
            task["command"],
            ["scripts/generate_report.py", "--latest-only"],
        )

    def test_collect_benchmark_metrics_ignores_non_benchmark_tasks(self):
        metrics = run_pipeline.collect_benchmark_metrics(
            [
                {
                    "name": "environment_check",
                    "kind": "environment",
                    "category": "",
                    "tool": "",
                    "benchmark": "",
                    "started_at": "2026-06-09T09:00:00",
                    "duration_seconds": 0.1,
                    "returncode": 0,
                },
                {
                    "name": "asan_memory_corruption_sample",
                    "kind": "benchmark",
                    "category": "memory_corruption",
                    "tool": "asan",
                    "benchmark": "benchmarks/memory_corruption/sample.c",
                    "started_at": "2026-06-09T09:00:01",
                    "duration_seconds": 1.2345,
                    "returncode": 1,
                },
            ]
        )

        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["category"], "memory_corruption")
        self.assertEqual(metrics[0]["duration_seconds"], "1.234")

    def test_build_category_metrics_groups_by_category(self):
        rows = run_pipeline.build_category_metrics(
            [
                {
                    "category": "memory_corruption",
                    "benchmark": "benchmarks/memory_corruption/a.c",
                    "duration_seconds": "1.000",
                },
                {
                    "category": "memory_corruption",
                    "benchmark": "benchmarks/memory_corruption/b.c",
                    "duration_seconds": "3.000",
                },
                {
                    "category": "data_race",
                    "benchmark": "benchmarks/data_race/race.c",
                    "duration_seconds": "2.000",
                },
            ]
        )

        by_category = {row["category"]: row for row in rows}
        self.assertEqual(by_category["memory_corruption"]["benchmark_count"], 2)
        self.assertEqual(by_category["memory_corruption"]["execution_count"], 2)
        self.assertEqual(by_category["memory_corruption"]["total_duration_seconds"], "4.000")
        self.assertEqual(by_category["memory_corruption"]["avg_duration_seconds"], "2.000")
        self.assertEqual(by_category["data_race"]["benchmark_count"], 1)

    def test_write_metrics_reports_creates_csv_files(self):
        with TemporaryDirectory() as temp_dir:
            benchmark_file = Path(temp_dir) / "benchmark_metrics.csv"
            category_file = Path(temp_dir) / "category_metrics.csv"

            run_pipeline.write_metrics_reports(
                [
                    {
                        "name": "tsan_data_race_sample",
                        "kind": "benchmark",
                        "category": "data_race",
                        "tool": "tsan",
                        "benchmark": "benchmarks/data_race/sample.c",
                        "started_at": "2026-06-09T09:00:00",
                        "duration_seconds": 2.0,
                        "returncode": 0,
                    }
                ],
                benchmark_file,
                category_file,
            )

            self.assertIn("duration_seconds", benchmark_file.read_text())
            self.assertIn("data_race", category_file.read_text())

    def test_format_category_metrics_returns_readable_table(self):
        table = run_pipeline.format_category_metrics(
            [
                {
                    "category": "deadlock",
                    "benchmark_count": 3,
                    "execution_count": 3,
                    "total_duration_seconds": "9.000",
                    "avg_duration_seconds": "3.000",
                }
            ]
        )

        self.assertIn("Categoria", table)
        self.assertIn("deadlock", table)
        self.assertIn("9.000s", table)

    def test_print_report_summary_prints_csv_content(self):
        with TemporaryDirectory() as temp_dir:
            summary_file = Path(temp_dir) / "summary.csv"
            summary_file.write_text(
                "tool,expected_behavior,expectation_match,classification,count,"
                "first_execution_date,latest_execution_date\n"
                "afl++,correto,conforme esperado,nao detectado,1,"
                "2026-06-05T21:00:00,2026-06-05T21:10:00\n"
            )
            output = StringIO()

            with redirect_stdout(output):
                run_pipeline.print_report_summary(summary_file)

        self.assertIn("Resumo consolidado da rodada", output.getvalue())
        self.assertIn("Ferramenta", output.getvalue())
        self.assertIn("Correto", output.getvalue())
        self.assertIn("Conforme", output.getvalue())
        self.assertIn("Nao detectado", output.getvalue())
        self.assertIn("2026-06-05 21:10:00", output.getvalue())

    def test_print_report_summary_handles_missing_file(self):
        output = StringIO()

        with redirect_stderr(output):
            run_pipeline.print_report_summary(Path("missing-summary.csv"))

        self.assertIn("Nao foi possivel ler o resumo CSV", output.getvalue())

    def test_format_summary_date_converts_iso_timestamp(self):
        self.assertEqual(
            run_pipeline.format_summary_date("2026-06-05T21:10:00"),
            "2026-06-05 21:10:00",
        )

    def test_format_summary_rows_returns_readable_table(self):
        table = run_pipeline.format_summary_rows(
            [
                {
                    "tool": "asan",
                    "expected_behavior": "vulneravel",
                    "expectation_match": "conforme esperado",
                    "classification": "detectado",
                    "count": "7",
                    "first_execution_date": "2026-06-05T21:00:00",
                    "latest_execution_date": "2026-06-05T21:20:00",
                }
            ]
        )

        self.assertIn("Ferramenta", table)
        self.assertIn("Vulneravel", table)
        self.assertIn("Conforme", table)
        self.assertIn("Detectado", table)
        self.assertIn("2026-06-05 21:20:00", table)


if __name__ == "__main__":
    unittest.main()
