#!/usr/bin/env bash
set -eu

REPORT_ARCHIVE="${REPORT_ARCHIVE:-reports-lightsail.tar.gz}"
ARCHIVE_OLD_RESULTS="${ARCHIVE_OLD_RESULTS:-1}"
OLD_RESULTS_DIR="${OLD_RESULTS_DIR:-antigos}"

echo "Diagnostico rapido da instancia:"
uname -a
free -h
docker version --format 'Docker {{.Server.Version}}'
docker compose version

if [ "$ARCHIVE_OLD_RESULTS" = "1" ]; then
  archive_dir="$OLD_RESULTS_DIR/rodada-antiga-$(date +%Y%m%d-%H%M%S)"
  has_old_results=0

  for path in outputs reports "$REPORT_ARCHIVE"; do
    if [ -e "$path" ]; then
      has_old_results=1
    fi
  done

  if [ "$has_old_results" = "1" ]; then
    echo "Arquivando logs e relatorios antigos em $archive_dir..."
    mkdir -p "$archive_dir"
    for path in outputs reports "$REPORT_ARCHIVE"; do
      if [ -e "$path" ]; then
        mv "$path" "$archive_dir/"
      fi
    done
  else
    echo "Nenhum resultado antigo encontrado para arquivar."
  fi
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
