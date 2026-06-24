#!/usr/bin/env bash
set -eu

if [ "$(id -u)" -eq 0 ]; then
  echo "Execute este script com o usuario padrao da instancia, nao como root."
  exit 1
fi

echo "Instalando ferramentas locais para validacoes pelo painel web..."
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  ca-certificates \
  clang \
  curl \
  g++ \
  gcc \
  git \
  python3 \
  software-properties-common

if ! command -v esbmc >/dev/null 2>&1; then
  echo "Instalando ESBMC via PPA oficial..."
  sudo add-apt-repository -y ppa:esbmc/esbmc
  sudo apt-get update
  sudo apt-get install -y esbmc
else
  echo "ESBMC ja esta instalado."
fi

echo "Ferramentas disponiveis:"
for tool in clang gcc g++ esbmc python3; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '  - %s: %s\n' "$tool" "$(command -v "$tool")"
  else
    printf '  - %s: nao encontrado\n' "$tool"
  fi
done
