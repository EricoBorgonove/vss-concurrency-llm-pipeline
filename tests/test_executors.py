import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import run_asan, run_deadlock, run_esbmc, run_tsan


class ExecutorHelpersTest(unittest.TestCase):
    def test_find_compiler_uses_requested_compiler_when_available(self):
        with patch("scripts.run_asan.shutil.which", return_value="/usr/bin/clang"):
            compiler_path, compiler_name = run_asan.find_compiler("clang")

        self.assertEqual(compiler_path, "/usr/bin/clang")
        self.assertEqual(compiler_name, "clang")

    def test_find_compiler_falls_back_to_gcc_when_clang_is_missing(self):
        def fake_which(candidate):
            return "/usr/bin/gcc" if candidate == "gcc" else None

        with patch("scripts.run_tsan.shutil.which", side_effect=fake_which):
            compiler_path, compiler_name = run_tsan.find_compiler(None)

        self.assertEqual(compiler_path, "/usr/bin/gcc")
        self.assertEqual(compiler_name, "gcc")

    def test_find_compiler_returns_none_when_no_compiler_exists(self):
        with patch("scripts.run_deadlock.shutil.which", return_value=None):
            compiler_path, compiler_name = run_deadlock.find_compiler(None)

        self.assertIsNone(compiler_path)
        self.assertEqual(compiler_name, "clang")

    def test_asan_write_log_records_compile_and_run_sections(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "asan.log"
            compile_result = subprocess.CompletedProcess(
                args=["clang"],
                returncode=0,
                stdout="",
                stderr="compile stderr",
            )
            run_result = subprocess.CompletedProcess(
                args=["binary"],
                returncode=1,
                stdout="run stdout",
                stderr="run stderr",
            )

            run_asan.write_log(
                log_path,
                Path("sample.c"),
                ["clang", "sample.c"],
                ["./sample"],
                compile_result=compile_result,
                run_result=run_result,
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn("tool: asan", content)
        self.assertIn("[compile]", content)
        self.assertIn("[run]", content)
        self.assertIn("compile stderr", content)
        self.assertIn("run stdout", content)

    def test_deadlock_write_log_records_timeout_error(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "deadlock.log"

            run_deadlock.write_log(
                log_path,
                Path("deadlock.c"),
                ["clang", "deadlock.c"],
                ["./deadlock"],
                error="Tempo limite excedido apos 3 segundos.",
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn("tool: deadlock-timeout", content)
        self.assertIn("[error]", content)
        self.assertIn("Tempo limite excedido", content)

    def test_esbmc_write_log_records_command_and_error(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "esbmc.log"

            run_esbmc.write_log(
                log_path,
                ["esbmc", "sample.c"],
                Path("sample.c"),
                127,
                error="Executavel ESBMC nao encontrado no PATH.",
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn("tool: esbmc", content)
        self.assertIn("command: esbmc sample.c", content)
        self.assertIn("returncode: 127", content)
        self.assertIn("Executavel ESBMC nao encontrado", content)


if __name__ == "__main__":
    unittest.main()
