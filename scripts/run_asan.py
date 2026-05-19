#!/usr/bin/env python3
"""Placeholder para executar AddressSanitizer (gera saída em outputs/asan/)."""
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs', 'asan')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, 'asan_placeholder.txt')
    try:
        with open(out_file, 'w') as f:
            f.write('ASAN placeholder - ainda não implementado\n')
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
