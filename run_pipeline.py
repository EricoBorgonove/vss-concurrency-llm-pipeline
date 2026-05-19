#!/usr/bin/env python3
"""Orquestrador mínimo do pipeline (placeholder).

Ainda não implementado: usará em etapas futuras para chamar scripts em `scripts/`.
"""
import sys


def main():
    print("Pipeline VSS-LLM: orquestrador placeholder")
    print("Execute scripts individuais em scripts/ por enquanto.")
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
