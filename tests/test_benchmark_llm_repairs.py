import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pipeline_runner import benchmark_llm_repairs
from pipeline_runner.paths import PROJECT_ROOT


class BenchmarkLlmRepairsTest(unittest.TestCase):
    # Verifica se a resposta em markdown e convertida em codigo C puro.
    def test_extract_c_code_from_fenced_response(self):
        code = benchmark_llm_repairs.extract_c_code(
            "```c\nint main(void) { return 0; }\n```",
            "original",
        )

        self.assertEqual(code, "int main(void) { return 0; }\n")

    # Verifica se categoria e ferramenta sao inferidas pelos metadados.
    def test_tool_for_benchmark_uses_category(self):
        benchmark = "benchmarks/assertion_violation/simple_assert_fail.c"

        self.assertEqual(benchmark_llm_repairs.category_for_benchmark(benchmark), "assertion_violation")
        self.assertEqual(benchmark_llm_repairs.tool_for_benchmark(benchmark), "esbmc")
        self.assertEqual(benchmark_llm_repairs.tool_for_benchmark(benchmark, "afl++"), "asan")

    # Verifica se o fallback simulado retorna um programa C compilavel, nao apenas texto.
    def test_simulated_response_contains_safe_c_code(self):
        code = benchmark_llm_repairs.extract_c_code(
            benchmark_llm_repairs.simulated_response("memory_corruption"),
            "original",
        )

        self.assertIn("int main", code)
        self.assertIn("free(buffer)", code)

    # Verifica se ausencia de chave gera fallback auditavel sem chamar API externa.
    def test_generate_repair_from_log_uses_simulated_fallback_without_api_key(self):
        log_file = PROJECT_ROOT / "outputs" / "asan" / "unit_llm_repair.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(
            (
                "tool: asan\n"
                "benchmark: benchmarks/memory_corruption/simple_buffer_overflow.c\n"
                "returncode: 1\n"
                "\n[run]\n"
                "AddressSanitizer: heap-buffer-overflow\n"
            ),
            encoding="utf-8",
        )

        try:
            with TemporaryDirectory() as temp_dir, patch.object(
                benchmark_llm_repairs,
                "LLM_BENCHMARK_REPAIRS_FILE",
                Path(temp_dir) / "llm_benchmark_repairs.csv",
            ), patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
                row = benchmark_llm_repairs.generate_repair_from_log(log_file)

                self.assertEqual(row["mode"], "simulado")
                self.assertEqual(row["category"], "memory_corruption")
                self.assertTrue((PROJECT_ROOT / row["repair_file"]).is_file())
                self.assertTrue((PROJECT_ROOT / row["repaired_benchmark"]).is_file())
                repaired_code = (PROJECT_ROOT / row["repaired_benchmark"]).read_text(encoding="utf-8")
                self.assertIn("int main", repaired_code)
                self.assertNotIn("original", repaired_code)
        finally:
            for key in ("repair_file", "repaired_benchmark", "response_file"):
                if "row" in locals() and row.get(key):
                    try:
                        (PROJECT_ROOT / row[key]).unlink()
                    except OSError:
                        pass
            try:
                log_file.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
