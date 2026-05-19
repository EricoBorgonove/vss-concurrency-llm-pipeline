#!/usr/bin/env python3
"""Placeholder para executar ThreadSanitizer (gera saída em outputs/tsan/)."""
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs', 'tsan')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, 'tsan_placeholder.txt')
    try:
        with open(out_file, 'w') as f:
            f.write('TSAN placeholder - ainda não implementado\n')
        print(f'Log salvo em: {out_file}')
        return 0
    except Exception as e:
        print(f'Erro ao escrever log: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f'Erro: {e}', file=sys.stderr)
        sys.exit(1)
