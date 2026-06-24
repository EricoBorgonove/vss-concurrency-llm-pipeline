#!/usr/bin/env bash
set -eu

REPORT_ARCHIVE="${REPORT_ARCHIVE:-reports-lightsail.tar.gz}"
OLD_RESULTS_DIR="${OLD_RESULTS_DIR:-antigos}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_DIR"

echo "Limpando historico local de benchmarks e relatorios..."
echo "Preservando repositorios GitHub em inputs/github_repos/."

rm -rf outputs reports "$REPORT_ARCHIVE"

if [ "${CLEAN_OLD_ARCHIVES:-1}" = "1" ]; then
  rm -rf "$OLD_RESULTS_DIR"
else
  echo "Mantendo $OLD_RESULTS_DIR porque CLEAN_OLD_ARCHIVES=$CLEAN_OLD_ARCHIVES."
fi

mkdir -p reports outputs

echo "Limpeza concluida."
echo "Repositorios GitHub preservados em: inputs/github_repos/"
