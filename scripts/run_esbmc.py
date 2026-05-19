#!/usr/bin/env python3
"""Placeholder para executar ESBMC em um benchmark e salvar logs em outputs/esbmc/.
"""
import argparse
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs', 'esbmc')


def main():
    parser = argparse.ArgumentParser(description='Executa ESBMC (placeholder).')
    parser.add_argument('benchmark', nargs='?', help='C file ou diretório de benchmark')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, 'esbmc_placeholder.txt')

    try:
        with open(out_file, 'w') as f:
            f.write('ESBMC placeholder - ainda não implementado\n')
            if args.benchmark:
                f.write(f'Benchmark: {args.benchmark}\n')
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
