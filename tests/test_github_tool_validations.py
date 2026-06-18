import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pipeline_runner import github_tool_validations
from pipeline_runner.paths import PROJECT_ROOT, display_path


class GitHubToolValidationsTest(unittest.TestCase):
    # Verifica o mapeamento inicial entre categoria do achado e ferramenta.
    def test_tools_for_finding_uses_category(self):
        self.assertEqual(
            github_tool_validations.tools_for_finding({"category": "memory_corruption"}),
            ("asan",),
        )
        self.assertEqual(
            github_tool_validations.tools_for_finding({"category": "data_race"}),
            ("tsan",),
        )
        self.assertEqual(
            github_tool_validations.tools_for_finding({"category": "deadlock"}),
            ("deadlock",),
        )
        self.assertEqual(
            github_tool_validations.tools_for_finding({"category": "assertion_violation"}),
            ("esbmc",),
        )

    # Verifica se arquivos que nao sao .c viram resultado nao validavel.
    def test_validate_finding_with_tool_skips_non_c_files(self):
        with TemporaryDirectory() as temp_dir:
            header = Path(temp_dir) / "sample.h"
            header.write_text("void f(void);\n", encoding="utf-8")

            row = github_tool_validations.validate_finding_with_tool(
                {"id": "f1", "link_id": "gh_000001", "file_path": str(header)},
                "asan",
                1,
                created_at="2026-06-17T12:00:00",
            )

            self.assertEqual(row["status"], "nao_executado")
            self.assertEqual(row["classification"], "nao_validavel")
            self.assertIn("apenas arquivos .c", row["error"])

    # Verifica se uma execucao com log de ASAN e classificada como detectada.
    def test_validate_finding_with_tool_classifies_detected_log(self):
        with TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            root = Path(temp_dir)
            source = root / "sample.c"
            log_file = root / "asan.log"
            source.write_text("int main(void) { return 0; }\n", encoding="utf-8")
            log_file.write_text("AddressSanitizer: heap-buffer-overflow\n", encoding="utf-8")
            stdout = f"Log salvo em: {display_path(log_file)}\n"
            completed = subprocess.CompletedProcess(
                args=["python", "scripts/run_asan.py"],
                returncode=1,
                stdout=stdout,
                stderr="",
            )

            with patch("pipeline_runner.github_tool_validations.subprocess.run", return_value=completed):
                row = github_tool_validations.validate_finding_with_tool(
                    {
                        "id": "f1",
                        "link_id": "gh_000001",
                        "file_path": str(source),
                        "category": "memory_corruption",
                    },
                    "asan",
                    1,
                    created_at="2026-06-17T12:00:00",
                )

            self.assertEqual(row["status"], "executado")
            self.assertEqual(row["classification"], "detectado")
            self.assertEqual(row["log_file"], display_path(log_file))

    # Verifica se a validacao em lote ignora falso positivo revisado.
    def test_validate_findings_ignores_false_positive(self):
        rows = github_tool_validations.validate_findings(
            [
                {
                    "id": "f1",
                    "link_id": "gh_000001",
                    "file_path": "missing.c",
                    "category": "memory_corruption",
                    "status": "falso_positivo",
                }
            ],
            created_at="2026-06-17T12:00:00",
        )

        self.assertEqual(rows, [])

    # Verifica se falha de execucao sem marcador nao vira erro de compilacao.
    def test_classify_tool_result_distinguishes_run_failure_from_compile_failure(self):
        self.assertEqual(
            github_tool_validations.classify_tool_result(
                "asan",
                1,
                "[compile]\nreturncode: 0\n[run]\nreturncode: 1\n",
            ),
            "inconclusivo",
        )
        self.assertEqual(
            github_tool_validations.classify_tool_result(
                "asan",
                1,
                "[compile]\nreturncode: 1\n",
            ),
            "erro_compilacao",
        )


if __name__ == "__main__":
    unittest.main()
