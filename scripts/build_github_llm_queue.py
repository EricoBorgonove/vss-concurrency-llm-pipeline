#!/usr/bin/env python3
"""Gera fila de candidatos para analise futura por LLM."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_runner.github_llm_queue import (  # noqa: E402
    GITHUB_LLM_QUEUE_FILE,
    build_queue_from_findings,
)
from pipeline_runner.paths import display_path  # noqa: E402


def build_parser():
    parser = argparse.ArgumentParser(
        description="Gera reports/github_llm_queue.csv a partir dos achados GitHub."
    )
    parser.add_argument(
        "--findings",
        help="CSV de achados. Padrao: reports/github_findings.csv.",
    )
    parser.add_argument(
        "--output",
        default=str(GITHUB_LLM_QUEUE_FILE),
        help="CSV da fila LLM. Padrao: reports/github_llm_queue.csv.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Quantidade maxima de candidatos exportados.",
    )
    return parser


def main():
    args = build_parser().parse_args()
    try:
        rows = build_queue_from_findings(
            findings_file=args.findings,
            output_file=args.output,
            limit=args.limit,
        )
        print(f"Fila LLM salva em: {display_path(args.output)}")
        print(f"Candidatos exportados: {len(rows)}")
        return 0
    except Exception as exc:
        print(f"Erro ao gerar fila LLM: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
