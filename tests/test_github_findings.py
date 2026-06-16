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
            self.assertEqual(rows[0]["status"], "suspeito")
            self.assertEqual(github_findings.finding_counts_by_link(rows), {"gh_000001": 1})
            self.assertEqual(github_findings.read_findings(csv_file), rows)

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


if __name__ == "__main__":
    unittest.main()
