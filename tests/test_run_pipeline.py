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
        task_names = {task["name"] for task in run_pipeline.discover_tasks()}

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

    def test_build_environment_task_runs_environment_check(self):
        task = run_pipeline.build_environment_task()

        self.assertEqual(task["name"], "environment_check")
        self.assertEqual(task["command"], ["scripts/check_environment.py"])

    def test_build_report_task_generates_latest_report(self):
        task = run_pipeline.build_report_task()

        self.assertEqual(task["name"], "generate_latest_report")
        self.assertEqual(
            task["command"],
            ["scripts/generate_report.py", "--latest-only"],
        )

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
