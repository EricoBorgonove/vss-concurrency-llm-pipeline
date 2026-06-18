import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline_runner import github_findings
from pipeline_runner.paths import display_path


class GitHubFindingsTest(unittest.TestCase):
    # Verifica se padroes perigosos conhecidos sao identificados.
    def test_analyze_source_text_detects_static_patterns(self):
        findings = github_findings.analyze_source_text(
            """
            #include <string.h>
            void copy(char *dst, char *src) {
                strcpy(dst, src);
                pthread_create(0, 0, 0, 0);
                assert(dst != 0);
            }
            """
        )

        self.assertEqual(
            [(item["category"], item["severity"]) for item in findings],
            [
                ("memory_corruption", "alta"),
                ("data_race", "media"),
                ("assertion_violation", "baixa"),
            ],
        )

    # Verifica se comentarios simples nao geram achados.
    def test_analyze_source_text_ignores_line_comments(self):
        findings = github_findings.analyze_source_text("// strcpy(dst, src);\n")

        self.assertEqual(findings, [])

    # Verifica se comentarios de bloco e strings nao viram falso positivo.
    def test_analyze_source_text_ignores_block_comments_and_strings(self):
        findings = github_findings.analyze_source_text(
            """
            /*
             * memcpy(dst, src, n);
             */
            void log_message(void) {
                puts("pthread_create() failed");
            }
            """
        )

        self.assertEqual(findings, [])

    # Verifica se a triagem grava achados por link em CSV.
    def test_replace_findings_for_link_writes_rows(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_file = root / "github_findings.csv"
            source = root / "sample.c"
            source.write_text(
                "void copy(char *dst, char *src) { strcpy(dst, src); }\n",
                encoding="utf-8",
            )
            file_row = {
                "id": "gh_000001_file_000001",
                "link_id": "gh_000001",
                "file_path": display_path(source),
            }

            rows = github_findings.replace_findings_for_link(
                "gh_000001",
                [file_row],
                csv_file=csv_file,
                created_at="2026-06-16T10:00:00",
            )

            self.assertEqual(rows[0]["id"], "gh_000001_finding_000001")
            self.assertEqual(rows[0]["tool"], "static-patterns")
            self.assertEqual(rows[0]["category"], "memory_corruption")
            self.assertEqual(rows[0]["priority"], "alta")
            self.assertEqual(rows[0]["status"], "suspeito")
            self.assertEqual(rows[0]["context_start_line"], "1")
            self.assertEqual(rows[0]["context_end_line"], "1")
            self.assertIn("> 1:", rows[0]["context"])
            self.assertEqual(github_findings.finding_counts_by_link(rows), {"gh_000001": 1})
            self.assertEqual(github_findings.read_findings(csv_file), rows)

    # Verifica se achados antigos sem prioridade sao enriquecidos na leitura.
    def test_read_findings_enriches_priority_for_legacy_rows(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_findings.csv"
            csv_file.write_text(
                (
                    "id,link_id,file_id,tool,file_path,line,category,severity,status,message,"
                    "evidence,created_at\n"
                    "f1,gh_000001,file1,static-patterns,sample.c,1,memory_corruption,"
                    "alta,suspeito,uso de strcpy pode copiar dados alem do destino,"
                    "strcpy,2026-06-16T10:00:00\n"
                ),
                encoding="utf-8",
            )

            rows = github_findings.read_findings(csv_file)

            self.assertEqual(rows[0]["priority"], "alta")
            self.assertEqual(rows[0]["context"], "")

    # Verifica se o contexto ao redor da linha suspeita pode ser coletado.
    def test_analyze_source_text_can_include_context(self):
        findings = github_findings.analyze_source_text(
            "\n".join(
                [
                    "int before(void) { return 0; }",
                    "void copy(char *dst, char *src) {",
                    "    strcpy(dst, src);",
                    "}",
                    "int after(void) { return 1; }",
                ]
            ),
            include_context=True,
            context_radius=1,
        )

        self.assertEqual(findings[0]["context_start_line"], "2")
        self.assertEqual(findings[0]["context_end_line"], "4")
        self.assertIn("  2: void copy", findings[0]["context"])
        self.assertIn("> 3:     strcpy", findings[0]["context"])
        self.assertIn("  4: }", findings[0]["context"])

    # Verifica se nova triagem substitui achados anteriores do mesmo link.
    def test_replace_findings_for_link_replaces_previous_rows(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_file = root / "github_findings.csv"
            first = root / "first.c"
            second = root / "second.c"
            first.write_text("void a(char *d, char *s) { strcpy(d, s); }\n", encoding="utf-8")
            second.write_text("void b(char *d, char *s) { strcat(d, s); }\n", encoding="utf-8")

            github_findings.replace_findings_for_link(
                "gh_000001",
                [{"id": "f1", "link_id": "gh_000001", "file_path": display_path(first)}],
                csv_file=csv_file,
            )
            rows = github_findings.replace_findings_for_link(
                "gh_000001",
                [{"id": "f2", "link_id": "gh_000001", "file_path": display_path(second)}],
                csv_file=csv_file,
            )

            self.assertEqual(len(rows), 1)
            self.assertEqual(github_findings.read_findings(csv_file), rows)
            self.assertIn("strcat", rows[0]["evidence"])

    # Verifica se achados associados a um link sao removidos.
    def test_remove_findings_for_link_deletes_related_rows(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_file = root / "github_findings.csv"
            first = root / "first.c"
            second = root / "second.c"
            first.write_text("void a(char *d, char *s) { strcpy(d, s); }\n", encoding="utf-8")
            second.write_text("void b(char *d, char *s) { strcat(d, s); }\n", encoding="utf-8")

            github_findings.replace_findings_for_link(
                "gh_000001",
                [{"id": "f1", "link_id": "gh_000001", "file_path": display_path(first)}],
                csv_file=csv_file,
            )
            github_findings.replace_findings_for_link(
                "gh_000002",
                [{"id": "f2", "link_id": "gh_000002", "file_path": display_path(second)}],
                csv_file=csv_file,
            )

            rows = github_findings.remove_findings_for_link("gh_000001", csv_file)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["link_id"], "gh_000002")

    # Verifica se a revisao manual altera o status de um achado no CSV.
    def test_update_finding_status_changes_review_state(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_file = root / "github_findings.csv"
            source = root / "sample.c"
            source.write_text("void a(char *d, char *s) { strcpy(d, s); }\n", encoding="utf-8")
            github_findings.replace_findings_for_link(
                "gh_000001",
                [{"id": "f1", "link_id": "gh_000001", "file_path": display_path(source)}],
                csv_file=csv_file,
            )

            row = github_findings.update_finding_status(
                "gh_000001_finding_000001",
                "confirmado",
                csv_file,
            )

            self.assertEqual(row["status"], "confirmado")
            self.assertEqual(github_findings.read_findings(csv_file)[0]["status"], "confirmado")

    # Verifica se status de revisao invalido e recusado.
    def test_update_finding_status_rejects_invalid_status(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_findings.csv"

            with self.assertRaises(ValueError):
                github_findings.update_finding_status("f1", "resolvido", csv_file)


if __name__ == "__main__":
    unittest.main()
