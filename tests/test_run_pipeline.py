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


if __name__ == "__main__":
    unittest.main()
