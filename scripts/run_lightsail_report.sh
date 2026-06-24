#!/usr/bin/env bash
set -eu

REPORT_ARCHIVE="${REPORT_ARCHIVE:-reports-lightsail.tar.gz}"
ARCHIVE_OLD_RESULTS="${ARCHIVE_OLD_RESULTS:-1}"
CLEAN_BENCHMARK_HISTORY="${CLEAN_BENCHMARK_HISTORY:-0}"
OLD_RESULTS_DIR="${OLD_RESULTS_DIR:-antigos}"
GITHUB_LLM_QUEUE_LIMIT="${GITHUB_LLM_QUEUE_LIMIT:-}"
GITHUB_VALIDATE_FINDINGS="${GITHUB_VALIDATE_FINDINGS:-1}"
GITHUB_VALIDATION_LIMIT="${GITHUB_VALIDATION_LIMIT:-25}"
GITHUB_VALIDATION_TIMEOUT="${GITHUB_VALIDATION_TIMEOUT:-10}"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

take_ownership() {
  for path in "$@"; do
    if [ -e "$path" ]; then
      sudo chown -R "$HOST_UID:$HOST_GID" "$path"
    fi
  done
}

echo "Diagnostico rapido da instancia:"
uname -a
free -h
docker version --format 'Docker {{.Server.Version}}'
docker compose version

if [ "$CLEAN_BENCHMARK_HISTORY" = "1" ]; then
  CLEAN_OLD_ARCHIVES="${CLEAN_OLD_ARCHIVES:-1}" ./scripts/clean_benchmark_history.sh
elif [ "$ARCHIVE_OLD_RESULTS" = "1" ]; then
  archive_dir="$OLD_RESULTS_DIR/rodada-antiga-$(date +%Y%m%d-%H%M%S)"
  has_old_results=0

  for path in outputs reports "$REPORT_ARCHIVE"; do
    if [ -e "$path" ]; then
      has_old_results=1
    fi
  done

  if [ "$has_old_results" = "1" ]; then
    echo "Arquivando logs e relatorios antigos em $archive_dir..."
    take_ownership outputs reports "$REPORT_ARCHIVE" "$OLD_RESULTS_DIR"
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
docker compose run --rm --user "$HOST_UID:$HOST_GID" pipeline

echo "Gerando fila de candidatos para LLM a partir dos achados GitHub..."
llm_queue_args=()
if [ -n "$GITHUB_LLM_QUEUE_LIMIT" ]; then
  llm_queue_args+=(--limit "$GITHUB_LLM_QUEUE_LIMIT")
fi
docker compose run --rm --user "$HOST_UID:$HOST_GID" pipeline \
  python3 scripts/build_github_llm_queue.py "${llm_queue_args[@]}"

if [ "$GITHUB_VALIDATE_FINDINGS" = "1" ]; then
  echo "Validando achados GitHub por ferramentas locais..."
  docker compose run --rm --user "$HOST_UID:$HOST_GID" pipeline \
    python3 scripts/validate_github_findings.py \
      --limit "$GITHUB_VALIDATION_LIMIT" \
      --timeout "$GITHUB_VALIDATION_TIMEOUT"
else
  echo "Validacao de achados GitHub desativada por GITHUB_VALIDATE_FINDINGS=$GITHUB_VALIDATE_FINDINGS."
fi

echo "Atualizando dashboard HTML com fila LLM e validacoes GitHub..."
docker compose run --rm --user "$HOST_UID:$HOST_GID" pipeline \
  python3 scripts/generate_report.py --latest-only

echo "Conferindo resumo TSAN:"
grep '^tsan' reports/summary.csv || true

echo "Empacotando reports/ e outputs/ principais em $REPORT_ARCHIVE..."
take_ownership outputs reports
tar -czf "$REPORT_ARCHIVE" reports outputs/environment outputs/pipeline

echo "Finalizado."
echo "Relatorio HTML: reports/report.html"
echo "Pacote para baixar: $REPORT_ARCHIVE"
