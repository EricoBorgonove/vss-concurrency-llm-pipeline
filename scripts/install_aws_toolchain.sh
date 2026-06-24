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

optional_packages=(
  afl++
  libc6-dev
  linux-libc-dev
  llvm
  libclang-common-18-dev
  libclang-rt-18-dev
  libclang-common-17-dev
  libclang-rt-17-dev
)
available_optional_packages=()

for package in "${optional_packages[@]}"; do
  if apt-cache show "$package" >/dev/null 2>&1; then
    available_optional_packages+=("$package")
  else
    echo "Pacote opcional nao disponivel neste Ubuntu: $package"
  fi
done

if [ "${#available_optional_packages[@]}" -gt 0 ]; then
  echo "Instalando headers e runtimes do Clang usados pelo ESBMC..."
  sudo apt-get install -y "${available_optional_packages[@]}"
fi

if ! command -v esbmc >/dev/null 2>&1; then
  echo "Instalando ESBMC via PPA oficial..."
  sudo add-apt-repository -y ppa:esbmc/esbmc
  sudo apt-get update
  sudo apt-get install -y esbmc
else
  echo "ESBMC ja esta instalado."
fi

echo "Ferramentas disponiveis:"
for tool in clang gcc g++ esbmc afl-clang-fast afl-fuzz python3; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '  - %s: %s\n' "$tool" "$(command -v "$tool")"
  else
    printf '  - %s: nao encontrado\n' "$tool"
  fi
done
