import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import validate_llm_repair


class ValidateLlmRepairTest(unittest.TestCase):
    def test_parse_repair_extracts_issue_type_and_suggestion_section(self):
        issue_type, has_suggestion = validate_llm_repair.parse_repair(
            "LLM repair simulation\n"
            "issue_type: memory_corruption\n"
            "suggestion:\n"
            "- limitar acesso ao buffer\n"
        )

        self.assertEqual(issue_type, "memory_corruption")
        self.assertTrue(has_suggestion)

    def test_validate_repair_approves_minimal_valid_simulation(self):
        status, issue_type, problems = validate_llm_repair.validate_repair(
            "LLM repair simulation\n"
            "issue_type: data_race\n"
            "suggestion:\n"
            "- proteger acesso compartilhado com mutex\n"
        )

        self.assertEqual(status, "validacao_simulada_aprovada")
        self.assertEqual(issue_type, "data_race")
        self.assertEqual(problems, [])

    def test_validate_repair_rejects_missing_metadata(self):
        status, issue_type, problems = validate_llm_repair.validate_repair(
            "texto sem metadados esperados"
        )

        self.assertEqual(status, "validacao_simulada_reprovada")
        self.assertEqual(issue_type, "")
        self.assertIn("campo issue_type ausente", problems)
        self.assertIn("secao suggestion ausente", problems)

    def test_run_tool_validation_builds_asan_command(self):
        completed = subprocess.CompletedProcess(
            args=["python", "scripts/run_asan.py"],
            returncode=0,
            stdout="ok",
            stderr="",
        )

        with patch("scripts.validate_llm_repair.subprocess.run", return_value=completed) as run:
            command, result = validate_llm_repair.run_tool_validation(
                "asan",
                Path("benchmarks/memory_corruption/simple_buffer_overflow_fixed.c"),
                12,
            )

        self.assertIn("scripts/run_asan.py", command)
        self.assertIn("--timeout", command)
        self.assertIn("12", command)
        self.assertEqual(result.returncode, 0)
        run.assert_called_once()

    def test_run_tool_validation_rejects_unknown_tool(self):
        with self.assertRaises(ValueError):
            validate_llm_repair.run_tool_validation("unknown", Path("sample.c"), 10)

    def test_write_validation_records_tool_result(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "validation.txt"
            repair_path = Path(temp_dir) / "repair.txt"
            tool_result = subprocess.CompletedProcess(
                args=["tool"],
                returncode=1,
                stdout="stdout text",
                stderr="stderr text",
            )

            validate_llm_repair.write_validation(
                output_path,
                repair_path,
                "validacao_controlada_reprovada",
                "deadlock",
                ["validacao falhou"],
                tool_command=["python3", "scripts/run_deadlock.py", "fixed.c"],
                tool_result=tool_result,
            )

            content = output_path.read_text(encoding="utf-8")

        self.assertIn("status: validacao_controlada_reprovada", content)
        self.assertIn("issue_type: deadlock", content)
        self.assertIn("returncode: 1", content)
        self.assertIn("stdout text", content)
        self.assertIn("stderr text", content)


if __name__ == "__main__":
    unittest.main()
