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

    # Verifica se a validacao em lote reporta progresso para a interface.
    def test_validate_findings_reports_progress(self):
        progress = []
        rows = github_tool_validations.validate_findings(
            [
                {
                    "id": "f1",
                    "link_id": "gh_000001",
                    "file_path": "missing-one.c",
                    "category": "memory_corruption",
                    "status": "suspeito",
                },
                {
                    "id": "f2",
                    "link_id": "gh_000001",
                    "file_path": "missing-two.c",
                    "category": "data_race",
                    "status": "suspeito",
                },
            ],
            created_at="2026-06-17T12:00:00",
            progress_callback=lambda processed, total, finding_id, tool: progress.append(
                (processed, total, finding_id, tool)
            ),
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(progress[0], (0, 2, "", ""))
        self.assertEqual(progress[1], (1, 2, "f1", "asan"))
        self.assertEqual(progress[2], (2, 2, "f2", "tsan"))

    # Verifica se validacoes persistidas em CSV podem ser lidas pela pagina.
    def test_read_validations_loads_existing_csv(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_tool_validations.csv"
            csv_file.write_text(
                (
                    "id,finding_id,link_id,tool,status,classification,command,returncode,"
                    "log_file,error,created_at\n"
                    "v1,f1,gh_000001,asan,executado,detectado,python run_asan.py,1,"
                    "outputs/asan/sample.log,,2026-06-18T10:00:00\n"
                ),
                encoding="utf-8",
            )

            rows = github_tool_validations.read_validations(csv_file)

            self.assertEqual(rows[0]["id"], "v1")
            self.assertEqual(rows[0]["classification"], "detectado")

    # Verifica se validar um achado preserva validacoes fora do escopo.
    def test_validate_findings_file_scopes_by_finding_id(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            findings_file = root / "github_findings.csv"
            output_file = root / "github_tool_validations.csv"
            findings_file.write_text(
                (
                    "id,link_id,file_id,tool,file_path,line,category,severity,priority,"
                    "status,message,evidence,context_start_line,context_end_line,context,created_at\n"
                    "f1,gh_000001,file1,static-patterns,missing-one.c,1,memory_corruption,"
                    "alta,alta,suspeito,uso de strcpy,strcpy,1,1,strcpy,2026-06-18T10:00:00\n"
                    "f2,gh_000002,file2,static-patterns,missing-two.c,1,memory_corruption,"
                    "alta,alta,suspeito,uso de strcpy,strcpy,1,1,strcpy,2026-06-18T10:00:00\n"
                ),
                encoding="utf-8",
            )
            output_file.write_text(
                (
                    "id,finding_id,link_id,tool,status,classification,command,returncode,"
                    "log_file,error,created_at\n"
                    "old,f2,gh_000002,asan,executado,detectado,cmd,1,log,,2026-06-18T10:00:00\n"
                ),
                encoding="utf-8",
            )

            rows = github_tool_validations.validate_findings_file(
                findings_file=findings_file,
                output_file=output_file,
                finding_id="f1",
                timeout=1,
            )
            saved_rows = github_tool_validations.read_validations(output_file)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["finding_id"], "f1")
            self.assertEqual(saved_rows[0]["finding_id"], "f2")
            self.assertEqual(saved_rows[1]["finding_id"], "f1")

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

    # Verifica se arquivo de biblioteca sem main nao e tratado como falha operacional.
    def test_classify_tool_result_treats_missing_main_as_not_validatable(self):
        log_text = (
            "[compile]\n"
            "returncode: 1\n"
            "stderr:\n"
            "/usr/bin/ld: /lib/x86_64-linux-gnu/Scrt1.o: in function `_start':\n"
            "(.text+0x1b): undefined reference to `main'\n"
            "clang: error: linker command failed with exit code 1\n"
        )

        self.assertEqual(
            github_tool_validations.classify_tool_result("asan", 1, log_text),
            "nao_validavel",
        )
        self.assertIn("arquivo sem funcao main", github_tool_validations.extract_error_message(log_text))

    # Verifica se falta de header padrao no ESBMC vira erro de ambiente.
    def test_classify_tool_result_treats_missing_standard_header_as_tool_error(self):
        log_text = (
            "tool: esbmc\n"
            "benchmark: inputs/github_repos/gh_000001/deps/hiredis/async.c\n"
            "command: esbmc inputs/github_repos/gh_000001/deps/hiredis/async.c\n"
            "returncode: 6\n"
            "\n[stderr]\n"
            "Target: 64-bit little-endian x86_64-unknown-linux with esbmclibc\n"
            "Parsing inputs/github_repos/gh_000001/deps/hiredis/async.c\n"
            "/tmp/esbmc/headers/stddef.h:13:15: fatal error: 'stddef.h' file not found\n"
            "ERROR: PARSING ERROR\n"
        )

        self.assertEqual(
            github_tool_validations.classify_tool_result("esbmc", 6, log_text),
            "erro_ferramenta",
        )
        self.assertIn("header padrao stddef.h", github_tool_validations.extract_error_message(log_text))
        self.assertIn("Preparar e retestar", github_tool_validations.extract_error_message(log_text))

    # Verifica se header do projeto ausente nao e confundido com problema da AWS.
    def test_classify_tool_result_treats_missing_project_header_as_not_validatable(self):
        log_text = (
            "[stderr]\n"
            "src/file.c:1:10: fatal error: 'project/private.h' file not found\n"
            "ERROR: PARSING ERROR\n"
        )

        self.assertEqual(
            github_tool_validations.classify_tool_result("esbmc", 6, log_text),
            "nao_validavel",
        )
        self.assertIn("includes/build", github_tool_validations.extract_error_message(log_text))

    # Verifica se a validacao registra mensagem util para arquivo sem main.
    def test_validate_finding_with_tool_marks_missing_main_as_not_validatable(self):
        with TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            root = Path(temp_dir)
            source = root / "library_file.c"
            log_file = root / "asan.log"
            source.write_text("int helper(void) { return 1; }\n", encoding="utf-8")
            log_file.write_text(
                (
                    "[compile]\n"
                    "returncode: 1\n"
                    "stderr:\n"
                    "(.text+0x1b): undefined reference to `main'\n"
                ),
                encoding="utf-8",
            )
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

            self.assertEqual(row["status"], "nao_executado")
            self.assertEqual(row["classification"], "nao_validavel")
            self.assertIn("arquivo sem funcao main", row["error"])


if __name__ == "__main__":
    unittest.main()
