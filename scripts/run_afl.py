#!/usr/bin/env python3
"""Prepara e executa uma campanha basica com AFL++."""

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "afl"
DEFAULT_SEEDS_DIR = PROJECT_ROOT / "seeds"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Compila um benchmark C com AFL++ e executa uma campanha curta."
    )
    parser.add_argument("benchmark", help="Arquivo .c que sera compilado com AFL++.")
    parser.add_argument(
        "--seeds-dir",
        default=str(DEFAULT_SEEDS_DIR),
        help="Diretorio com seeds iniciais. Padrao: seeds/.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Duracao da campanha AFL++ em segundos. Padrao: 5.",
    )
    parser.add_argument(
        "--afl-cc",
        default="afl-clang-fast",
        help="Compilador AFL++ a usar. Padrao: afl-clang-fast.",
    )
    parser.add_argument(
        "--afl-fuzz",
        default="afl-fuzz",
        help="Executor AFL++ a usar. Padrao: afl-fuzz.",
    )
    return parser


def make_log_path(benchmark):
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"{benchmark.stem}_{timestamp}.log"


def write_log(
    log_path,
    benchmark,
    seeds_dir,
    compile_command,
    fuzz_command,
    compile_result=None,
    fuzz_result=None,
    campaign_dir=None,
    error="",
):
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("tool: afl++\n")
        log_file.write(f"benchmark: {benchmark}\n")
        log_file.write(f"seeds_dir: {seeds_dir}\n")
        log_file.write(f"campaign_dir: {campaign_dir or 'N/A'}\n")
        log_file.write(f"compile_command: {' '.join(compile_command) if compile_command else 'N/A'}\n")
        log_file.write(f"fuzz_command: {' '.join(fuzz_command) if fuzz_command else 'N/A'}\n")

        if error:
            log_file.write("\n[error]\n")
            log_file.write(error)
            log_file.write("\n")

        if compile_result is not None:
            log_file.write("\n[compile]\n")
            log_file.write(f"returncode: {compile_result.returncode}\n")
            if compile_result.stdout:
                log_file.write("\nstdout:\n")
                log_file.write(compile_result.stdout)
            if compile_result.stderr:
                log_file.write("\nstderr:\n")
                log_file.write(compile_result.stderr)

        if fuzz_result is not None:
            log_file.write("\n[fuzz]\n")
            log_file.write(f"returncode: {fuzz_result.returncode}\n")
            if fuzz_result.stdout:
                log_file.write("\nstdout:\n")
                log_file.write(fuzz_result.stdout)
            if fuzz_result.stderr:
                log_file.write("\nstderr:\n")
                log_file.write(fuzz_result.stderr)


def main():
    parser = build_parser()
    args = parser.parse_args()

    benchmark = Path(args.benchmark).resolve()
    seeds_dir = Path(args.seeds_dir).resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = make_log_path(benchmark)

    if not benchmark.exists():
        write_log(log_path, benchmark, seeds_dir, [], [], error="Arquivo de benchmark nao encontrado.")
        print(f"Erro: arquivo nao encontrado: {benchmark}", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 2

    if benchmark.suffix != ".c":
        write_log(log_path, benchmark, seeds_dir, [], [], error="O benchmark deve ser um arquivo .c.")
        print(f"Erro: o benchmark deve ser um arquivo .c: {benchmark}", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 2

    if not seeds_dir.is_dir():
        write_log(log_path, benchmark, seeds_dir, [], [], error="Diretorio de seeds nao encontrado.")
        print(f"Erro: diretorio de seeds nao encontrado: {seeds_dir}", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 2

    seed_files = [path for path in seeds_dir.iterdir() if path.is_file() and path.name != ".gitkeep"]
    if not seed_files:
        write_log(log_path, benchmark, seeds_dir, [], [], error="Nenhum arquivo de seed encontrado.")
        print(f"Erro: nenhum arquivo de seed encontrado em: {seeds_dir}", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 2

    afl_cc_path = shutil.which(args.afl_cc)
    afl_fuzz_path = shutil.which(args.afl_fuzz)
    if afl_cc_path is None or afl_fuzz_path is None:
        missing = []
        if afl_cc_path is None:
            missing.append(args.afl_cc)
        if afl_fuzz_path is None:
            missing.append(args.afl_fuzz)
        write_log(
            log_path,
            benchmark,
            seeds_dir,
            [],
            [],
            error=f"Ferramenta AFL++ nao encontrada: {', '.join(missing)}.",
        )
        print(f"Erro: ferramenta AFL++ nao encontrada: {', '.join(missing)}.", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 127

    try:
        with tempfile.TemporaryDirectory(prefix="vss-afl-build-") as tmp_dir:
            binary_path = Path(tmp_dir) / benchmark.stem
            campaign_dir = OUTPUT_DIR / f"{benchmark.stem}_{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            compile_command = [
                args.afl_cc,
                "-g",
                "-O0",
                str(benchmark),
                "-o",
                str(binary_path),
            ]
            compile_result = subprocess.run(
                compile_command,
                capture_output=True,
                text=True,
                check=False,
            )

            if compile_result.returncode != 0:
                write_log(
                    log_path,
                    benchmark,
                    seeds_dir,
                    compile_command,
                    [],
                    compile_result=compile_result,
                    campaign_dir=campaign_dir,
                )
                print(f"Erro: falha na compilacao AFL++. Log salvo em: {log_path}", file=sys.stderr)
                return compile_result.returncode

            fuzz_command = [
                args.afl_fuzz,
                "-i",
                str(seeds_dir),
                "-o",
                str(campaign_dir),
                "-V",
                str(args.timeout),
                "--",
                str(binary_path),
            ]
            env = os.environ.copy()
            env.setdefault("AFL_SKIP_CPUFREQ", "1")
            env.setdefault("AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES", "1")

            fuzz_result = subprocess.run(
                fuzz_command,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            write_log(
                log_path,
                benchmark,
                seeds_dir,
                compile_command,
                fuzz_command,
                compile_result=compile_result,
                fuzz_result=fuzz_result,
                campaign_dir=campaign_dir,
            )
            print(f"Log salvo em: {log_path}")
            return fuzz_result.returncode
    except OSError as exc:
        write_log(log_path, benchmark, seeds_dir, [], [], error=str(exc))
        print(f"Erro ao executar AFL++: {exc}", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
