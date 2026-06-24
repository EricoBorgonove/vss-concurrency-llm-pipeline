#!/usr/bin/env bash
set -eu

SERVICE_NAME="${SERVICE_NAME:-vss-pipeline-web}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-8080}"
PUBLIC_PORT="${PUBLIC_PORT:-80}"
SERVER_NAME="${SERVER_NAME:-_}"
DEFAULT_AUTH_USERS="erico:vss123,brenda:vss123,alberjan:vss123,lucas:vss123"
AUTH_USERS="${VSS_AUTH_USERS:-$DEFAULT_AUTH_USERS}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="/etc/${SERVICE_NAME}.env"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
NGINX_SITE="/etc/nginx/sites-available/${SERVICE_NAME}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${SERVICE_NAME}"

if [ "$(id -u)" -eq 0 ]; then
  echo "Execute este script com o usuario padrao da instancia, nao como root."
  exit 1
fi

write_env_var() {
  key="$1"
  value="$2"
  escaped_value="$(printf '%s' "$value" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  printf '%s="%s"\n' "$key" "$escaped_value"
}

echo "Instalando dependencias do painel web..."
sudo apt-get update
sudo apt-get install -y python3 nginx
./scripts/install_aws_toolchain.sh

echo "Gravando variaveis de ambiente em $ENV_FILE..."
sudo install -m 600 -o root -g root /dev/null "$ENV_FILE"
{
  write_env_var "VSS_AUTH_USERS" "$AUTH_USERS"
  write_env_var "GITHUB_VALIDATION_LIMIT" "${GITHUB_VALIDATION_LIMIT:-25}"
  write_env_var "GITHUB_VALIDATION_TIMEOUT" "${GITHUB_VALIDATION_TIMEOUT:-10}"
  printf 'PYTHONUNBUFFERED=1\n'
} | sudo tee "$ENV_FILE" >/dev/null

echo "Criando servico systemd $SERVICE_NAME..."
sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=Pipeline VSS-LLM web panel
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/python3 $APP_DIR/scripts/github_link_server.py --host $WEB_HOST --port $WEB_PORT
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "Configurando Nginx em porta $PUBLIC_PORT..."
sudo tee "$NGINX_SITE" >/dev/null <<EOF
server {
    listen $PUBLIC_PORT;
    server_name $SERVER_NAME;

    client_max_body_size 20m;

    location / {
        proxy_pass http://$WEB_HOST:$WEB_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sfn "$NGINX_SITE" "$NGINX_ENABLED"
if [ -e /etc/nginx/sites-enabled/default ]; then
  sudo rm -f /etc/nginx/sites-enabled/default
fi

echo "Recarregando servicos..."
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"
sudo nginx -t
sudo systemctl reload nginx

echo "Instalacao concluida."
echo "Status do painel:"
sudo systemctl --no-pager --lines=8 status "$SERVICE_NAME" || true
echo "Acesse: http://IP_DA_INSTANCIA/"
echo "Na Lightsail, libere a porta TCP $PUBLIC_PORT no firewall da instancia."
