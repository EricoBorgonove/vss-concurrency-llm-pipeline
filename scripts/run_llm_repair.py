#!/usr/bin/env python3
"""Gera reparo LLM para um benchmark a partir de um log de ferramenta."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_runner.benchmark_llm_repairs import generate_repair_from_log  # noqa: E402


def display_path(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Gera reparo LLM para um benchmark a partir de um log."
    )
    parser.add_argument("evidence", help="Arquivo de log usado como evidencia.")
    parser.add_argument(
        "--benchmark",
        help="Arquivo .c a ser reparado. Se omitido, sera lido do campo benchmark do log.",
    )
    parser.add_argument("--tool", help="Ferramenta usada para validar este benchmark.")
    parser.add_argument("--model", help="Modelo LLM. Padrao: VSS_LLM_MODEL ou gpt-4.1-mini.")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    evidence_path = Path(args.evidence).resolve()
    if not evidence_path.exists():
        print(f"Erro: evidencia nao encontrada: {display_path(evidence_path)}", file=sys.stderr)
        return 2

    if not evidence_path.is_file():
        print(f"Erro: evidencia deve ser um arquivo: {display_path(evidence_path)}", file=sys.stderr)
        return 2

    try:
        row = generate_repair_from_log(
            evidence_path,
            benchmark=args.benchmark or "",
            tool=args.tool or "",
            model=args.model,
        )
        print(f"Reparo LLM registrado: {row['id']}")
        print(f"Arquivo de reparo: {row['repair_file']}")
        print(f"Benchmark reparado: {row['repaired_benchmark']}")
        print(f"Resposta LLM: {row['response_file']}")
        if row.get("error"):
            print(f"Aviso: {row['error']}", file=sys.stderr)
        return 0
    except (OSError, ValueError) as exc:
        print(f"Erro ao gerar reparo LLM: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
