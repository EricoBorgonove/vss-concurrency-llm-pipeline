#!/usr/bin/env python3
"""Valida achados GitHub com ferramentas locais quando possivel."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_runner.github_tool_validations import (  # noqa: E402
    GITHUB_TOOL_VALIDATIONS_FILE,
    validate_findings_file,
)
from pipeline_runner.paths import display_path  # noqa: E402


def build_parser():
    parser = argparse.ArgumentParser(
        description="Executa validacao inicial dos achados GitHub por ferramentas locais."
    )
    parser.add_argument(
        "--findings",
        help="CSV de achados. Padrao: reports/github_findings.csv.",
    )
    parser.add_argument(
        "--output",
        default=str(GITHUB_TOOL_VALIDATIONS_FILE),
        help="CSV de validacoes. Padrao: reports/github_tool_validations.csv.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout por ferramenta em segundos. Padrao: 10.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Quantidade maxima de validacoes executadas.",
    )
    return parser


def main():
    args = build_parser().parse_args()
    try:
        rows = validate_findings_file(
            findings_file=args.findings,
            output_file=args.output,
            timeout=args.timeout,
            limit=args.limit,
        )
        print(f"Validacoes salvas em: {display_path(args.output)}")
        print(f"Validacoes registradas: {len(rows)}")
        return 0
    except Exception as exc:
        print(f"Erro ao validar achados GitHub: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
