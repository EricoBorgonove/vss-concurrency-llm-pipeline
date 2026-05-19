#!/usr/bin/env python3
"""Placeholder para geração de relatórios agregados em `reports/`.
"""
import os
import sys

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    out_file = os.path.join(REPORTS_DIR, 'report_placeholder.txt')
    try:
        with open(out_file, 'w') as f:
            f.write('Report placeholder - ainda não implementado\n')
        print(f'Relatório salvo em: {out_file}')
        return 0
    except Exception as e:
        print(f'Erro ao escrever relatório: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f'Erro: {e}', file=sys.stderr)
        sys.exit(1)
