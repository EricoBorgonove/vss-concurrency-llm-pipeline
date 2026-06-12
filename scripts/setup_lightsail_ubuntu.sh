#!/usr/bin/env bash
set -eu

SWAP_SIZE="${SWAP_SIZE:-4G}"
SWAP_FILE="${SWAP_FILE:-/swapfile}"

if [ "$(id -u)" -eq 0 ]; then
  echo "Execute este script com o usuario padrao da instancia, nao como root."
  exit 1
fi

echo "Atualizando pacotes basicos..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl git

if ! command -v docker >/dev/null 2>&1; then
  echo "Instalando Docker..."
  curl -fsSL https://get.docker.com | sudo sh
else
  echo "Docker ja esta instalado."
fi

if ! groups "$USER" | grep -q '\bdocker\b'; then
  echo "Adicionando $USER ao grupo docker..."
  sudo usermod -aG docker "$USER"
fi

if [ ! -f "$SWAP_FILE" ]; then
  echo "Criando swap em $SWAP_FILE com tamanho $SWAP_SIZE..."
  sudo fallocate -l "$SWAP_SIZE" "$SWAP_FILE"
  sudo chmod 600 "$SWAP_FILE"
  sudo mkswap "$SWAP_FILE"
else
  echo "Arquivo de swap ja existe em $SWAP_FILE."
fi

if ! swapon --show=NAME | grep -qx "$SWAP_FILE"; then
  sudo swapon "$SWAP_FILE"
fi

if ! grep -q "^$SWAP_FILE " /etc/fstab; then
  echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
fi

echo "Ambiente preparado."
echo "Se o grupo docker acabou de ser adicionado, saia e entre novamente no SSH ou rode: newgrp docker"
