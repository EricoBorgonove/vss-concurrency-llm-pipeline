#!/usr/bin/env python3
"""Valida de forma simulada uma sugestao gerada pela etapa de LLM."""

import argparse
import datetime as dt
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "llm"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Valida uma sugestao simulada de reparo sem alterar codigo-fonte."
    )
    parser.add_argument("repair_file", help="Arquivo de sugestao gerado por run_llm_repair.py.")
    return parser


def make_output_path(repair_path):
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"{repair_path.stem}_{timestamp}_validation.txt"


def parse_repair(content):
    issue_type = ""
    has_suggestion = False

    for line in content.splitlines():
        if line.startswith("issue_type: "):
            issue_type = line.removeprefix("issue_type: ").strip()
        if line.strip() == "suggestion:":
            has_suggestion = True

    return issue_type, has_suggestion


def validate_repair(content):
    issue_type, has_suggestion = parse_repair(content)
    problems = []

    if "LLM repair simulation" not in content:
        problems.append("arquivo nao parece ser uma sugestao simulada de LLM")
    if not issue_type:
        problems.append("campo issue_type ausente")
    if not has_suggestion:
        problems.append("secao suggestion ausente")

    status = "validacao_simulada_aprovada" if not problems else "validacao_simulada_reprovada"
    return status, issue_type, problems


def write_validation(output_path, repair_path, status, issue_type, problems):
    with output_path.open("w", encoding="utf-8") as output_file:
        output_file.write("LLM repair validation simulation\n")
        output_file.write(f"generated_at: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        output_file.write(f"repair_file: {repair_path}\n")
        output_file.write(f"status: {status}\n")
        output_file.write(f"issue_type: {issue_type or 'N/A'}\n\n")
        output_file.write("checks:\n")
        if problems:
            for problem in problems:
                output_file.write(f"- {problem}\n")
        else:
            output_file.write("- sugestao contem metadados minimos esperados\n")
            output_file.write("- nenhuma alteracao de codigo foi aplicada nesta etapa\n")
            output_file.write("- validacao real com ESBMC/sanitizers fica para etapa futura\n")


def main():
    parser = build_parser()
    args = parser.parse_args()

    repair_path = Path(args.repair_file).resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = make_output_path(repair_path)

    if not repair_path.exists():
        print(f"Erro: arquivo de reparo nao encontrado: {repair_path}", file=sys.stderr)
        return 2

    if not repair_path.is_file():
        print(f"Erro: reparo deve ser um arquivo: {repair_path}", file=sys.stderr)
        return 2

    try:
        content = repair_path.read_text(encoding="utf-8", errors="replace")
        status, issue_type, problems = validate_repair(content)
        write_validation(output_path, repair_path, status, issue_type, problems)
        print(f"Validacao simulada salva em: {output_path}")
        return 0 if not problems else 1
    except OSError as exc:
        print(f"Erro ao validar reparo: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
