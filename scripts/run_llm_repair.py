#!/usr/bin/env python3
"""Gera uma sugestao simulada de reparo a partir de um log de ferramenta."""

import argparse
import datetime as dt
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "llm"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Gera uma sugestao simulada de reparo sem chamar API externa."
    )
    parser.add_argument("evidence", help="Arquivo de log usado como evidencia.")
    return parser


def make_output_path(evidence_path):
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"{evidence_path.stem}_{timestamp}_repair.txt"


def classify_evidence(log_text):
    text = log_text.lower()
    if "heap-buffer-overflow" in text or "addresssanitizer" in text:
        return (
            "memory_corruption",
            "Revisar os limites do buffer, validar indices antes de escrita e "
            "garantir que a alocacao tenha tamanho suficiente.",
        )
    if "data race" in text or "threadsanitizer" in text:
        return (
            "data_race",
            "Proteger o estado compartilhado com mutex ou usar operacoes atomicas "
            "para sincronizar acessos concorrentes.",
        )
    if "deadlock" in text:
        return (
            "deadlock",
            "Definir uma ordem global de aquisicao de locks e liberar mutexes em "
            "todos os caminhos de erro.",
        )
    if "assert" in text or "violated property" in text or "verification failed" in text:
        return (
            "assertion_violation",
            "Revisar a pre-condicao que leva a assertiva, corrigindo o valor de "
            "entrada ou fortalecendo a validacao antes da propriedade.",
        )
    if "ferramenta afl++ nao encontrada" in text:
        return (
            "tool_unavailable",
            "Instalar AFL++ ou configurar os caminhos de afl-clang-fast e afl-fuzz "
            "antes de solicitar uma sugestao de reparo baseada em fuzzing.",
        )
    return (
        "unknown",
        "Inspecionar manualmente o log e identificar a propriedade violada antes "
        "de propor uma alteracao no codigo.",
    )


def write_repair(output_path, evidence_path, issue_type, suggestion):
    with output_path.open("w", encoding="utf-8") as output_file:
        output_file.write("LLM repair simulation\n")
        output_file.write(f"generated_at: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        output_file.write(f"evidence: {evidence_path}\n")
        output_file.write(f"issue_type: {issue_type}\n\n")
        output_file.write("suggestion:\n")
        output_file.write(suggestion)
        output_file.write("\n\n")
        output_file.write("note:\n")
        output_file.write(
            "Esta etapa e uma simulacao deterministica. Nenhuma API externa foi chamada.\n"
        )


def main():
    parser = build_parser()
    args = parser.parse_args()

    evidence_path = Path(args.evidence).resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = make_output_path(evidence_path)

    if not evidence_path.exists():
        print(f"Erro: evidencia nao encontrada: {evidence_path}", file=sys.stderr)
        return 2

    if not evidence_path.is_file():
        print(f"Erro: evidencia deve ser um arquivo: {evidence_path}", file=sys.stderr)
        return 2

    try:
        log_text = evidence_path.read_text(encoding="utf-8", errors="replace")
        issue_type, suggestion = classify_evidence(log_text)
        write_repair(output_path, evidence_path, issue_type, suggestion)
        print(f"Sugestao simulada salva em: {output_path}")
        return 0
    except OSError as exc:
        print(f"Erro ao processar evidencia: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
