#!/usr/bin/env bash
set -eu

REPORT_ARCHIVE="${REPORT_ARCHIVE:-reports-lightsail.tar.gz}"
CLEAN_RESULTS="${CLEAN_RESULTS:-1}"

echo "Diagnostico rapido da instancia:"
uname -a
free -h
docker version --format 'Docker {{.Server.Version}}'
docker compose version

if [ "$CLEAN_RESULTS" = "1" ]; then
  echo "Limpando logs e relatorios antigos antes da rodada..."
  rm -rf outputs reports "$REPORT_ARCHIVE"
fi

echo "Construindo imagem do pipeline..."
docker compose build

echo "Executando pipeline completo..."
docker compose run --rm pipeline

echo "Conferindo resumo TSAN:"
grep '^tsan' reports/summary.csv || true

echo "Empacotando reports/ e outputs/ principais em $REPORT_ARCHIVE..."
tar -czf "$REPORT_ARCHIVE" reports outputs/environment outputs/pipeline

echo "Finalizado."
echo "Relatorio HTML: reports/report.html"
echo "Pacote para baixar: $REPORT_ARCHIVE"
