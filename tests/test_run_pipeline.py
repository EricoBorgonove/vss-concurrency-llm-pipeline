import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
