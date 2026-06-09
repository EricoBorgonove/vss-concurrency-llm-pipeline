import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import generate_report


class GenerateReportTest(unittest.TestCase):
    # Verifica se a lista de ferramentas separada por virgulas e aceita.
    def test_parse_tools_accepts_comma_separated_tools(self):
        tools = generate_report.parse_tools("asan,tsan")

        self.assertEqual(tools, ("asan", "tsan"))

    # Verifica se ferramentas desconhecidas sao rejeitadas.
    def test_parse_tools_rejects_unknown_tool(self):
        with self.assertRaises(ValueError):
            generate_report.parse_tools("asan,unknown")

    # Verifica se marcadores do AddressSanitizer classificam deteccao.
    def test_classify_result_detects_asan_marker(self):
        data = {
            "error": "",
            "compile_returncode": "0",
        }

        classification = generate_report.classify_result(
            "SUMMARY: AddressSanitizer: heap-buffer-overflow",
            data,
        )

        self.assertEqual(classification, "detectado")

    # Verifica se falta de ferramenta e classificada como indisponibilidade.
    def test_classify_result_detects_unavailable_tool(self):
        data = {
            "error": "Ferramenta AFL++ nao encontrada: afl-clang-fast, afl-fuzz.",
            "compile_returncode": "",
        }

        classification = generate_report.classify_result("", data)

        self.assertEqual(classification, "ferramenta indisponivel")

    # Verifica se o resumo agrupa resultados e datas por ferramenta/classificacao.
    def test_build_summary_counts_by_tool_and_classification(self):
        rows = [
            {
                "tool": "asan",
                "expected_behavior": "vulneravel",
                "expectation_match": "conforme esperado",
                "classification": "detectado",
                "execution_date": "2026-06-05T20:00:00",
            },
            {
                "tool": "asan",
                "expected_behavior": "vulneravel",
                "expectation_match": "conforme esperado",
                "classification": "detectado",
                "execution_date": "2026-06-05T21:00:00",
            },
            {
                "tool": "tsan",
                "expected_behavior": "correto",
                "expectation_match": "conforme esperado",
                "classification": "nao detectado",
                "execution_date": "2026-06-05T20:30:00",
            },
        ]

        summary = generate_report.build_summary(rows)

        self.assertEqual(
            summary,
            [
                {
                    "tool": "asan",
                    "expected_behavior": "vulneravel",
                    "expectation_match": "conforme esperado",
                    "classification": "detectado",
                    "count": 2,
                    "first_execution_date": "2026-06-05T20:00:00",
                    "latest_execution_date": "2026-06-05T21:00:00",
                },
                {
                    "tool": "tsan",
                    "expected_behavior": "correto",
                    "expectation_match": "conforme esperado",
                    "classification": "nao detectado",
                    "count": 1,
                    "first_execution_date": "2026-06-05T20:30:00",
                    "latest_execution_date": "2026-06-05T20:30:00",
                },
            ],
        )

    # Verifica se a data de execucao e extraida do nome do arquivo de log.
    def test_extract_execution_date_from_log_filename(self):
        execution_date = generate_report.extract_execution_date(
            Path("outputs/asan/simple_buffer_overflow_20260605-210638.log")
        )

        self.assertEqual(execution_date, "2026-06-05T21:06:38")

    # Verifica se sufixos de benchmark definem o comportamento esperado.
    def test_infer_expected_behavior_from_benchmark_suffix(self):
        self.assertEqual(
            generate_report.infer_expected_behavior("benchmarks/data_race/race_error.c"),
            "vulneravel",
        )
        self.assertEqual(
            generate_report.infer_expected_behavior("benchmarks/data_race/race_safe.c"),
            "correto",
        )
        self.assertEqual(
            generate_report.infer_expected_behavior("benchmarks/data_race/simple_data_race.c"),
            "nao informado",
        )

    # Verifica a comparacao entre comportamento esperado e classificacao.
    def test_evaluate_expectation_compares_expected_behavior_and_classification(self):
        self.assertEqual(
            generate_report.evaluate_expectation("vulneravel", "detectado"),
            "conforme esperado",
        )
        self.assertEqual(
            generate_report.evaluate_expectation("correto", "detectado"),
            "divergente",
        )
        self.assertEqual(
            generate_report.evaluate_expectation("correto", "erro de execucao"),
            "inconclusivo",
        )

    # Verifica se apenas o log mais recente por ferramenta/benchmark e mantido.
    def test_filter_latest_rows_keeps_latest_log_per_tool_and_benchmark(self):
        rows = [
            {
                "tool": "afl++",
                "benchmark": "benchmarks/memory_corruption/simple_buffer_overflow.c",
                "log_file": "outputs/afl/simple_buffer_overflow_20260519-170253.log",
            },
            {
                "tool": "afl++",
                "benchmark": "benchmarks/memory_corruption/simple_buffer_overflow.c",
                "log_file": "outputs/afl/simple_buffer_overflow_20260605-204924.log",
            },
            {
                "tool": "asan",
                "benchmark": "benchmarks/memory_corruption/simple_buffer_overflow.c",
                "log_file": "outputs/asan/simple_buffer_overflow_20260605-204920.log",
            },
        ]

        latest_rows = generate_report.filter_latest_rows(rows)

        self.assertEqual(
            latest_rows,
            [
                {
                    "tool": "afl++",
                    "benchmark": "benchmarks/memory_corruption/simple_buffer_overflow.c",
                    "log_file": "outputs/afl/simple_buffer_overflow_20260605-204924.log",
                },
                {
                    "tool": "asan",
                    "benchmark": "benchmarks/memory_corruption/simple_buffer_overflow.c",
                    "log_file": "outputs/asan/simple_buffer_overflow_20260605-204920.log",
                },
            ],
        )

    # Verifica se a tabela HTML escapa valores potencialmente perigosos.
    def test_render_html_table_escapes_cell_values(self):
        table = generate_report.render_html_table(
            [{"tool": "<script>alert(1)</script>"}],
            ["tool"],
        )

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", table)
        self.assertNotIn("<script>alert(1)</script>", table)

    # Verifica se o relatorio HTML contem resumo, metricas e detalhes.
    def test_write_html_report_creates_summary_and_detail_sections(self):
        rows = [
            {
                "tool": "asan",
                "benchmark": "benchmarks/memory_corruption/sample_error.c",
                "log_file": "outputs/asan/sample_error_20260609-120000.log",
                "execution_date": "2026-06-09T12:00:00",
                "expected_behavior": "vulneravel",
                "expectation_match": "conforme esperado",
                "returncode": "",
                "compile_returncode": "0",
                "run_returncode": "1",
                "classification": "detectado",
                "error": "",
            }
        ]

        with TemporaryDirectory() as temp_dir:
            html_path = Path(temp_dir) / "report.html"
            generate_report.write_html_report(
                rows,
                html_path,
                category_metrics_rows=[
                    {
                        "category": "memory_corruption",
                        "benchmark_count": "1",
                        "execution_count": "2",
                        "total_duration_seconds": "3.000",
                        "avg_duration_seconds": "1.500",
                        "min_duration_seconds": "1.000",
                        "max_duration_seconds": "2.000",
                    }
                ],
                benchmark_metrics_rows=[
                    {
                        "run_date": "2026-06-09T12:00:00",
                        "category": "memory_corruption",
                        "tool": "asan",
                        "benchmark": "benchmarks/memory_corruption/sample_error.c",
                        "duration_seconds": "1.000",
                        "returncode": "1",
                    }
                ],
            )
            content = html_path.read_text(encoding="utf-8")

        self.assertIn("Relatorio Pipeline VSS-LLM", content)
        self.assertIn("Resumo", content)
        self.assertIn("Métricas por Categoria", content)
        self.assertIn("Métricas por Benchmark", content)
        self.assertIn("Resultados Detalhados", content)
        self.assertIn("memory_corruption", content)
        self.assertIn("duration_seconds", content)
        self.assertIn("sample_error.c", content)
        self.assertIn("conforme esperado", content)

    # Verifica se a leitura opcional de CSV retorna vazio quando o arquivo nao existe.
    def test_read_csv_if_exists_returns_empty_list_for_missing_file(self):
        with TemporaryDirectory() as temp_dir:
            rows = generate_report.read_csv_if_exists(Path(temp_dir) / "missing.csv")

        self.assertEqual(rows, [])

    # Verifica se a leitura opcional de CSV carrega linhas existentes.
    def test_read_csv_if_exists_reads_existing_csv(self):
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "metrics.csv"
            csv_path.write_text("category,count\nmemory_corruption,2\n", encoding="utf-8")

            rows = generate_report.read_csv_if_exists(csv_path)

        self.assertEqual(rows, [{"category": "memory_corruption", "count": "2"}])


if __name__ == "__main__":
    unittest.main()
