#!/usr/bin/env python3
"""Compila e executa um benchmark C com ThreadSanitizer."""

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "tsan"


def display_path(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        if path.is_absolute() and str(path).startswith(tempfile.gettempdir()):
            return f"<tmp>/{path.name}"
        return str(path)


def display_command(command):
    return [display_path(part) if "/" in str(part) else str(part) for part in command]


def sanitize_text(text):
    text = str(text)
    text = text.replace(str(PROJECT_ROOT) + "/", "")
    temp_pattern = r"/var" + r"/folders/\S+/T/vss-"
    text = re.sub(temp_pattern + r"[^/\s,;\"<>]+/(\S+)", r"<tmp>/\1", text)
    return re.sub(temp_pattern + r"[^\s,;\"<>]+", "<tmp>", text)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Compila e executa um benchmark C com ThreadSanitizer."
    )
    parser.add_argument("benchmark", help="Arquivo .c que sera compilado com TSAN.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Tempo limite da execucao do binario em segundos. Padrao: 10.",
    )
    parser.add_argument(
        "--compiler",
        default=None,
        help="Compilador C a usar. Padrao: clang, ou gcc se clang nao existir.",
    )
    return parser


def make_log_path(benchmark):
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"{benchmark.stem}_{timestamp}.log"


def find_compiler(compiler):
    if compiler:
        return shutil.which(compiler), compiler

    candidates = (
        "/opt/homebrew/opt/llvm/bin/clang",
        "/usr/local/opt/llvm/bin/clang",
        "clang",
        "gcc",
    )
    for candidate in candidates:
        compiler_path = shutil.which(candidate)
        if compiler_path:
            return compiler_path, compiler_path if candidate.startswith("/") else candidate

    return None, "clang"


def write_log(
    log_path,
    benchmark,
    compile_command,
    run_command,
    compile_result=None,
    run_result=None,
    error="",
):
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("tool: tsan\n")
        log_file.write(f"benchmark: {display_path(benchmark)}\n")
        log_file.write(
            f"compile_command: {' '.join(display_command(compile_command)) if compile_command else 'N/A'}\n"
        )
        log_file.write(
            f"run_command: {' '.join(display_command(run_command)) if run_command else 'N/A'}\n"
        )

        if error:
            log_file.write("\n[error]\n")
            log_file.write(sanitize_text(error))
            log_file.write("\n")

        if compile_result is not None:
            log_file.write("\n[compile]\n")
            log_file.write(f"returncode: {compile_result.returncode}\n")
            if compile_result.stdout:
                log_file.write("\nstdout:\n")
                log_file.write(sanitize_text(compile_result.stdout))
            if compile_result.stderr:
                log_file.write("\nstderr:\n")
                log_file.write(sanitize_text(compile_result.stderr))

        if run_result is not None:
            log_file.write("\n[run]\n")
            log_file.write(f"returncode: {run_result.returncode}\n")
            if run_result.stdout:
                log_file.write("\nstdout:\n")
                log_file.write(sanitize_text(run_result.stdout))
            if run_result.stderr:
                log_file.write("\nstderr:\n")
                log_file.write(sanitize_text(run_result.stderr))


def main():
    parser = build_parser()
    args = parser.parse_args()

    benchmark = Path(args.benchmark).resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = make_log_path(benchmark)

    if not benchmark.exists():
        write_log(log_path, benchmark, [], [], error="Arquivo de benchmark nao encontrado.")
        print(f"Erro: arquivo nao encontrado: {display_path(benchmark)}", file=sys.stderr)
        print(f"Log salvo em: {display_path(log_path)}")
        return 2

    if benchmark.suffix != ".c":
        write_log(log_path, benchmark, [], [], error="O benchmark deve ser um arquivo .c.")
        print(f"Erro: o benchmark deve ser um arquivo .c: {display_path(benchmark)}", file=sys.stderr)
        print(f"Log salvo em: {display_path(log_path)}")
        return 2

    compiler_path, compiler_name = find_compiler(args.compiler)
    if compiler_path is None:
        write_log(log_path, benchmark, [], [], error="Compilador C nao encontrado.")
        print("Erro: compilador C nao encontrado.", file=sys.stderr)
        print(f"Log salvo em: {display_path(log_path)}")
        return 127

    try:
        with tempfile.TemporaryDirectory(prefix="vss-tsan-") as tmp_dir:
            binary_path = Path(tmp_dir) / benchmark.stem
            compile_command = [
                compiler_name,
                "-fsanitize=thread",
                "-g",
                "-O0",
                str(benchmark),
                "-o",
                str(binary_path),
                "-pthread",
            ]
            compile_result = subprocess.run(
                compile_command,
                capture_output=True,
                text=True,
                check=False,
            )

            if compile_result.returncode != 0:
                write_log(log_path, benchmark, compile_command, [], compile_result=compile_result)
                print(f"Erro: falha na compilacao. Log salvo em: {display_path(log_path)}", file=sys.stderr)
                return compile_result.returncode

            run_command = [str(binary_path)]
            run_result = subprocess.run(
                run_command,
                capture_output=True,
                text=True,
                timeout=args.timeout,
                check=False,
            )
            runtime_error = ""
            if run_result.returncode == 66 and not run_result.stdout and not run_result.stderr:
                runtime_error = (
                    "TSAN terminou com codigo 66 sem diagnostico. "
                    "Esse padrao indica ambiente de execucao incompativel, "
                    "por exemplo Docker linux/amd64 emulado em Apple Silicon."
                )
            write_log(
                log_path,
                benchmark,
                compile_command,
                run_command,
                compile_result=compile_result,
                run_result=run_result,
                error=runtime_error,
            )
            print(f"Log salvo em: {display_path(log_path)}")
            return run_result.returncode
    except subprocess.TimeoutExpired as exc:
        run_result = subprocess.CompletedProcess(
            args=exc.cmd,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
        )
        write_log(
            log_path,
            benchmark,
            locals().get("compile_command", []),
            locals().get("run_command", []),
            compile_result=locals().get("compile_result"),
            run_result=run_result,
            error=f"Tempo limite excedido apos {args.timeout} segundos.",
        )
        print(f"Erro: tempo limite excedido apos {args.timeout} segundos.", file=sys.stderr)
        print(f"Log salvo em: {display_path(log_path)}")
        return 124
    except OSError as exc:
        write_log(log_path, benchmark, [], [], error=str(exc))
        print(f"Erro ao executar TSAN: {exc}", file=sys.stderr)
        print(f"Log salvo em: {display_path(log_path)}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
