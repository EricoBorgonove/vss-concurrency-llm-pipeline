import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import run_afl, run_asan, run_deadlock, run_esbmc, run_tsan


class ExecutorHelpersTest(unittest.TestCase):
    # Verifica se o compilador solicitado e usado quando esta disponivel.
    def test_find_compiler_uses_requested_compiler_when_available(self):
        with patch("scripts.run_asan.shutil.which", return_value="/usr/bin/clang"):
            compiler_path, compiler_name = run_asan.find_compiler("clang")

        self.assertEqual(compiler_path, "/usr/bin/clang")
        self.assertEqual(compiler_name, "clang")

    # Verifica se o helper tenta usar gcc quando clang nao esta disponivel.
    def test_find_compiler_falls_back_to_gcc_when_clang_is_missing(self):
        def fake_which(candidate):
            return "/usr/bin/gcc" if candidate == "gcc" else None

        with patch("scripts.run_tsan.shutil.which", side_effect=fake_which):
            compiler_path, compiler_name = run_tsan.find_compiler(None)

        self.assertEqual(compiler_path, "/usr/bin/gcc")
        self.assertEqual(compiler_name, "gcc")

    # Verifica se TSAN prefere clang LLVM quando disponivel.
    def test_tsan_find_compiler_prefers_homebrew_llvm_clang(self):
        def fake_which(candidate):
            if candidate == "/opt/homebrew/opt/llvm/bin/clang":
                return candidate
            if candidate == "clang":
                return "/usr/bin/clang"
            return None

        with patch("scripts.run_tsan.shutil.which", side_effect=fake_which):
            compiler_path, compiler_name = run_tsan.find_compiler(None)

        self.assertEqual(compiler_path, "/opt/homebrew/opt/llvm/bin/clang")
        self.assertEqual(compiler_name, "/opt/homebrew/opt/llvm/bin/clang")

    # Verifica se ASAN tambem prefere clang LLVM quando disponivel.
    def test_asan_find_compiler_prefers_homebrew_llvm_clang(self):
        def fake_which(candidate):
            if candidate == "/opt/homebrew/opt/llvm/bin/clang":
                return candidate
            if candidate == "clang":
                return "/usr/bin/clang"
            return None

        with patch("scripts.run_asan.shutil.which", side_effect=fake_which):
            compiler_path, compiler_name = run_asan.find_compiler(None)

        self.assertEqual(compiler_path, "/opt/homebrew/opt/llvm/bin/clang")
        self.assertEqual(compiler_name, "/opt/homebrew/opt/llvm/bin/clang")

    # Verifica o comportamento quando nenhum compilador C e encontrado.
    def test_find_compiler_returns_none_when_no_compiler_exists(self):
        with patch("scripts.run_deadlock.shutil.which", return_value=None):
            compiler_path, compiler_name = run_deadlock.find_compiler(None)

        self.assertIsNone(compiler_path)
        self.assertEqual(compiler_name, "clang")

    # Verifica se o log do ASAN registra secoes de compilacao e execucao.
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

    # Verifica se o log do AFL++ registra uso de ASAN.
    def test_afl_write_log_records_asan_mode(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "afl.log"

            run_afl.write_log(
                log_path,
                Path("sample.c"),
                Path("seeds"),
                ["afl-clang-fast", "sample.c"],
                ["afl-fuzz"],
                use_asan=True,
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn("tool: afl++", content)
        self.assertIn("use_asan: true", content)

    # Verifica se o log do AFL++ preserva a tentativa ASAN descartada.
    def test_afl_write_log_records_asan_fallback(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "afl.log"
            asan_result = subprocess.CompletedProcess(
                args=["afl-clang-fast"],
                returncode=1,
                stdout="",
                stderr="missing asan runtime",
            )
            compile_result = subprocess.CompletedProcess(
                args=["afl-clang-fast"],
                returncode=0,
                stdout="",
                stderr="",
            )

            run_afl.write_log(
                log_path,
                Path("sample.c"),
                Path("seeds"),
                ["afl-clang-fast", "sample.c"],
                ["afl-fuzz"],
                compile_result=compile_result,
                use_asan=False,
                asan_compile_result=asan_result,
                asan_fallback=True,
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn("use_asan: false", content)
        self.assertIn("asan_compile_fallback: true", content)
        self.assertIn("[asan_compile_attempt]", content)
        self.assertIn("missing asan runtime", content)
        self.assertIn("[compile]", content)
        self.assertIn("returncode: 0", content)

    # Verifica se o log de deadlock registra corretamente erro de timeout.
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

    # Verifica se o log do ESBMC registra comando, retorno e erro.
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
