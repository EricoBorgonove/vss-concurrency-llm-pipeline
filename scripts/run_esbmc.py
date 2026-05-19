#!/usr/bin/env python3
"""Executa ESBMC em um benchmark C e salva o log em outputs/esbmc/."""

import argparse
import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "esbmc"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Executa ESBMC em um benchmark C e salva o log em outputs/esbmc/."
    )
    parser.add_argument("benchmark", help="Arquivo .c que sera verificado pelo ESBMC.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Tempo limite da execucao em segundos. Padrao: 60.",
    )
    parser.add_argument(
        "--esbmc-bin",
        default="esbmc",
        help="Nome ou caminho do executavel ESBMC. Padrao: esbmc.",
    )
    return parser


def make_log_path(benchmark):
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"{benchmark.stem}_{timestamp}.log"


def write_log(log_path, command, benchmark, returncode, stdout="", stderr="", error=""):
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("tool: esbmc\n")
        log_file.write(f"benchmark: {benchmark}\n")
        log_file.write(f"command: {' '.join(command) if command else 'N/A'}\n")
        log_file.write(f"returncode: {returncode}\n")
        if error:
            log_file.write("\n[error]\n")
            log_file.write(error)
            log_file.write("\n")
        if stdout:
            log_file.write("\n[stdout]\n")
            log_file.write(stdout)
        if stderr:
            log_file.write("\n[stderr]\n")
            log_file.write(stderr)


def main():
    parser = build_parser()
    args = parser.parse_args()

    benchmark = Path(args.benchmark).resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = make_log_path(benchmark)

    if not benchmark.exists():
        write_log(log_path, [], benchmark, 2, error="Arquivo de benchmark nao encontrado.")
        print(f"Erro: arquivo nao encontrado: {benchmark}", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 2

    if benchmark.suffix != ".c":
        write_log(log_path, [], benchmark, 2, error="O benchmark deve ser um arquivo .c.")
        print(f"Erro: o benchmark deve ser um arquivo .c: {benchmark}", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 2

    esbmc_path = shutil.which(args.esbmc_bin)
    command = [args.esbmc_bin, str(benchmark)]

    if esbmc_path is None:
        write_log(
            log_path,
            command,
            benchmark,
            127,
            error="Executavel ESBMC nao encontrado no PATH.",
        )
        print("Erro: executavel ESBMC nao encontrado no PATH.", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 127

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            check=False,
        )
        write_log(log_path, command, benchmark, result.returncode, result.stdout, result.stderr)
        print(f"Log salvo em: {log_path}")
        return result.returncode
    except subprocess.TimeoutExpired as exc:
        write_log(
            log_path,
            command,
            benchmark,
            124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            error=f"Tempo limite excedido apos {args.timeout} segundos.",
        )
        print(f"Erro: tempo limite excedido apos {args.timeout} segundos.", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 124
    except OSError as exc:
        write_log(log_path, command, benchmark, 1, error=str(exc))
        print(f"Erro ao executar ESBMC: {exc}", file=sys.stderr)
        print(f"Log salvo em: {log_path}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
