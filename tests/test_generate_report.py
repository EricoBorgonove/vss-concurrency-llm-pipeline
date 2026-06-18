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

    # Verifica se crash de runtime sem marcador nao vira falso negativo.
    def test_classify_result_treats_negative_run_returncode_as_execution_error(self):
        data = {
            "tool": "tsan",
            "error": "",
            "compile_returncode": "0",
            "run_returncode": "-11",
        }

        classification = generate_report.classify_result("returncode: -11", data)

        self.assertEqual(classification, "erro de execucao")

    # Verifica se falha fatal do runtime TSAN nao vira deteccao.
    def test_classify_result_treats_tsan_fatal_runtime_as_execution_error(self):
        data = {
            "tool": "tsan",
            "error": "",
            "compile_returncode": "0",
            "run_returncode": "66",
        }

        classification = generate_report.classify_result(
            "FATAL: ThreadSanitizer: unexpected memory mapping",
            data,
        )

        self.assertEqual(classification, "erro de execucao")

    # Verifica se TSAN sem diagnostico explicito nao vira divergencia falsa.
    def test_classify_result_treats_empty_tsan_exit_66_as_inconclusive(self):
        data = {
            "tool": "tsan",
            "error": "",
            "compile_returncode": "0",
            "run_returncode": "66",
        }

        classification = generate_report.classify_result("returncode: 66", data)

        self.assertEqual(classification, "inconclusivo")

    # Verifica se AFL++ sem crash em campanha curta fica inconclusivo.
    def test_classify_result_treats_afl_timeout_without_crashes_as_inconclusive(self):
        data = {
            "tool": "afl++",
            "error": "",
            "compile_returncode": "0",
            "run_returncode": "0",
        }

        classification = generate_report.classify_result(
            "Time limit was reached\nStatistics: 0 crashes saved",
            data,
        )

        self.assertEqual(classification, "inconclusivo")

    # Verifica se AFL++ com crash salvo fica detectado.
    def test_classify_result_treats_afl_saved_crashes_as_detected(self):
        data = {
            "tool": "afl++",
            "error": "",
            "compile_returncode": "0",
            "run_returncode": "0",
        }

        classification = generate_report.classify_result(
            "Statistics: 1 crashes saved",
            data,
        )

        self.assertEqual(classification, "detectado")

    # Verifica se AFL++ considera crash no dry run como deteccao.
    def test_classify_result_treats_afl_seed_crash_as_detected(self):
        data = {
            "tool": "afl++",
            "error": "",
            "compile_returncode": "0",
            "run_returncode": "1",
        }

        classification = generate_report.classify_result(
            "Oops, the program crashed with one of the test cases provided.",
            data,
        )

        self.assertEqual(classification, "detectado")

    # Verifica se o resumo agrupa resultados e datas por ferramenta/classificacao.
    def test_build_summary_counts_by_tool_and_classification(self):
        rows = [
            {
                "tool": "asan",
                "expected_behavior": "vulneravel",
                "expectation_match": "conforme esperado",
                "expected_tool_behavior": "detectar",
                "tool_expectation_match": "conforme esperado",
                "classification": "detectado",
                "execution_date": "2026-06-05T20:00:00",
            },
            {
                "tool": "asan",
                "expected_behavior": "vulneravel",
                "expectation_match": "conforme esperado",
                "expected_tool_behavior": "detectar",
                "tool_expectation_match": "conforme esperado",
                "classification": "detectado",
                "execution_date": "2026-06-05T21:00:00",
            },
            {
                "tool": "tsan",
                "expected_behavior": "correto",
                "expectation_match": "conforme esperado",
                "expected_tool_behavior": "nao_detectar",
                "tool_expectation_match": "conforme esperado",
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
                    "expected_tool_behavior": "detectar",
                    "tool_expectation_match": "conforme esperado",
                    "classification": "detectado",
                    "count": 2,
                    "first_execution_date": "2026-06-05T20:00:00",
                    "latest_execution_date": "2026-06-05T21:00:00",
                },
                {
                    "tool": "tsan",
                    "expected_behavior": "correto",
                    "expectation_match": "conforme esperado",
                    "expected_tool_behavior": "nao_detectar",
                    "tool_expectation_match": "conforme esperado",
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

    # Verifica se metadados explicitos substituem a inferencia por sufixo.
    def test_get_expected_behavior_from_metadata(self):
        metadata = {
            "benchmarks/data_race/simple_data_race.c": {
                "expected_behavior": "vulneravel",
                "expected_tsan": "detectar",
            }
        }

        self.assertEqual(
            generate_report.get_expected_behavior(
                "benchmarks/data_race/simple_data_race.c",
                metadata,
            ),
            "vulneravel",
        )
        self.assertEqual(
            generate_report.get_expected_tool_behavior(
                "tsan",
                "benchmarks/data_race/simple_data_race.c",
                metadata,
            ),
            "detectar",
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
        self.assertEqual(
            generate_report.evaluate_expectation("vulneravel", "inconclusivo"),
            "inconclusivo",
        )

    # Verifica a comparacao especifica da expectativa da ferramenta.
    def test_evaluate_tool_expectation_compares_tool_behavior_and_classification(self):
        self.assertEqual(
            generate_report.evaluate_tool_expectation("detectar", "detectado"),
            "conforme esperado",
        )
        self.assertEqual(
            generate_report.evaluate_tool_expectation("nao_detectar", "detectado"),
            "divergente",
        )
        self.assertEqual(
            generate_report.evaluate_tool_expectation("inconclusivo", "nao detectado"),
            "inconclusivo",
        )
        self.assertEqual(
            generate_report.evaluate_tool_expectation("detectar", "inconclusivo"),
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

    # Verifica se metricas por categoria sao derivadas dos resultados quando o CSV auxiliar falta.
    def test_build_category_metrics_from_rows_counts_benchmarks_and_executions(self):
        rows = generate_report.dashboard_rows(
            [
                {
                    "tool": "asan",
                    "benchmark": "benchmarks/memory_corruption/sample_error.c",
                },
                {
                    "tool": "tsan",
                    "benchmark": "benchmarks/memory_corruption/sample_error.c",
                },
                {
                    "tool": "tsan",
                    "benchmark": "benchmarks/data_race/race_error.c",
                },
            ]
        )

        metrics = generate_report.build_category_metrics_from_rows(rows)

        self.assertEqual(
            metrics,
            [
                {
                    "category": "data_race",
                    "benchmark_count": 1,
                    "execution_count": 1,
                    "total_duration_seconds": "nao informado",
                    "avg_duration_seconds": "nao informado",
                    "min_duration_seconds": "nao informado",
                    "max_duration_seconds": "nao informado",
                },
                {
                    "category": "memory_corruption",
                    "benchmark_count": 1,
                    "execution_count": 2,
                    "total_duration_seconds": "nao informado",
                    "avg_duration_seconds": "nao informado",
                    "min_duration_seconds": "nao informado",
                    "max_duration_seconds": "nao informado",
                },
            ],
        )

    # Verifica se metricas por benchmark sao derivadas dos resultados quando o CSV auxiliar falta.
    def test_build_benchmark_metrics_from_rows_uses_result_rows(self):
        rows = generate_report.dashboard_rows(
            [
                {
                    "tool": "asan",
                    "benchmark": "benchmarks/memory_corruption/sample_error.c",
                    "execution_date": "2026-06-09T12:00:00",
                    "run_returncode": "1",
                    "returncode": "",
                }
            ]
        )

        metrics = generate_report.build_benchmark_metrics_from_rows(rows)

        self.assertEqual(
            metrics,
            [
                {
                    "run_date": "2026-06-09T12:00:00",
                    "category": "memory_corruption",
                    "tool": "asan",
                    "benchmark": "benchmarks/memory_corruption/sample_error.c",
                    "duration_seconds": "nao informado",
                    "returncode": "1",
                }
            ],
        )

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
                "expected_tool_behavior": "detectar",
                "tool_expectation_match": "conforme esperado",
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

        self.assertIn("Dashboard Pipeline VSS-LLM", content)
        self.assertIn("filter-tool", content)
        self.assertIn("filter-category", content)
        self.assertIn("filter-classification", content)
        self.assertIn("detail-table", content)
        self.assertIn("Resumo", content)
        self.assertIn("Metricas por Categoria", content)
        self.assertIn("Metricas por Benchmark", content)
        self.assertIn("Resultados Detalhados", content)
        self.assertIn("memory_corruption", content)
        self.assertIn("duration_seconds", content)
        self.assertIn("sample_error.c", content)
        self.assertIn("conforme esperado", content)

    # Verifica se o HTML preenche metricas derivadas quando os CSVs auxiliares nao sao informados.
    def test_write_html_report_derives_metrics_when_auxiliary_rows_are_missing(self):
        rows = [
            {
                "tool": "asan",
                "benchmark": "benchmarks/memory_corruption/sample_error.c",
                "log_file": "outputs/asan/sample_error_20260609-120000.log",
                "execution_date": "2026-06-09T12:00:00",
                "expected_behavior": "vulneravel",
                "expectation_match": "conforme esperado",
                "expected_tool_behavior": "detectar",
                "tool_expectation_match": "conforme esperado",
                "returncode": "",
                "compile_returncode": "0",
                "run_returncode": "1",
                "classification": "detectado",
                "error": "",
            }
        ]

        with TemporaryDirectory() as temp_dir:
            html_path = Path(temp_dir) / "report.html"
            generate_report.write_html_report(rows, html_path)
            content = html_path.read_text(encoding="utf-8")

        self.assertIn("memory_corruption", content)
        self.assertIn("nao informado", content)
        self.assertIn("Metricas por Categoria", content)
        self.assertIn("Metricas por Benchmark", content)

    # Verifica se o HTML inclui links e achados vindos da analise de GitHub.
    def test_write_html_report_includes_github_links_and_findings(self):
        rows = [
            {
                "tool": "asan",
                "benchmark": "benchmarks/memory_corruption/sample_error.c",
                "log_file": "outputs/asan/sample_error_20260609-120000.log",
                "execution_date": "2026-06-09T12:00:00",
                "expected_behavior": "vulneravel",
                "expectation_match": "conforme esperado",
                "expected_tool_behavior": "detectar",
                "tool_expectation_match": "conforme esperado",
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
                github_link_rows=[
                    {
                        "id": "gh_000001",
                        "submitted_at": "2026-06-16T10:00:00",
                        "url": "https://github.com/nginx/nginx",
                        "url_type": "repo",
                        "status": "triagem_concluida",
                        "local_path": "inputs/github_repos/gh_000001",
                        "error": "",
                    }
                ],
                github_file_rows=[
                    {
                        "id": "gh_000001_file_000001",
                        "link_id": "gh_000001",
                        "file_path": "inputs/github_repos/gh_000001/src/core/sample.c",
                    }
                ],
                github_finding_rows=[
                    {
                        "id": "gh_000001_finding_000001",
                        "link_id": "gh_000001",
                        "tool": "static-patterns",
                        "file_path": "inputs/github_repos/gh_000001/src/core/sample.c",
                        "line": "10",
                        "category": "memory_corruption",
                        "severity": "media",
                        "priority": "media",
                        "status": "suspeito",
                        "message": "uso de memcpy exige validacao explicita de tamanho",
                        "evidence": "memcpy(dst, src, n);",
                        "context_start_line": "8",
                        "context_end_line": "12",
                        "context": "> 10: memcpy(dst, src, n);",
                    }
                ],
            )
            content = html_path.read_text(encoding="utf-8")

        self.assertIn("Analises de Links do GitHub", content)
        self.assertIn("Achados dos Links do GitHub", content)
        self.assertIn("https://github.com/nginx/nginx", content)
        self.assertIn("gh_000001", content)
        self.assertIn("file_count", content)
        self.assertIn("finding_count", content)
        self.assertIn("github-filter-link", content)
        self.assertIn("github-filter-category", content)
        self.assertIn("github-filter-severity", content)
        self.assertIn("github-filter-priority", content)
        self.assertIn("github-filter-status", content)
        self.assertIn("github-finding-table", content)
        self.assertIn("memcpy(dst, src, n);", content)
        self.assertIn("context_start_line", content)
        self.assertIn("&gt; 10: memcpy(dst, src, n);", content)

    # Verifica se tabelas muito grandes sao limitadas no HTML.
    def test_render_limited_html_table_shows_limit_note(self):
        rows = [{"id": str(index)} for index in range(3)]

        table = generate_report.render_limited_html_table(rows, ["id"], limit=2)

        self.assertIn("Exibindo 2 de 3 registros", table)
        self.assertIn("<td>0</td>", table)
        self.assertIn("<td>1</td>", table)
        self.assertNotIn("<td>2</td>", table)

    # Verifica se a tabela de achados contem atributos usados pelos filtros.
    def test_render_github_finding_table_adds_filter_attributes(self):
        table = generate_report.render_github_finding_table(
            [
                {
                    "id": "finding-1",
                    "link_id": "gh_000001",
                    "category": "memory_corruption",
                    "severity": "alta",
                    "priority": "alta",
                    "status": "suspeito",
                    "message": "uso de strcpy",
                }
            ],
            ["id", "link_id", "category", "severity", "priority", "status", "message"],
        )

        self.assertIn('id="github-finding-table"', table)
        self.assertIn('data-link="gh_000001"', table)
        self.assertIn('data-category="memory_corruption"', table)
        self.assertIn('data-severity="alta"', table)
        self.assertIn('data-priority="alta"', table)
        self.assertIn('data-status="suspeito"', table)

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
