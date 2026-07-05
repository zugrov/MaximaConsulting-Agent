#!/bin/bash
# Первичная установка mc-agent на VPS (Ubuntu 24.04)
# Запуск от root после: git clone ... /var/www/mc-agent

set -e

APP_DIR="/var/www/mc-agent"
cd "$APP_DIR"

echo "=== 1. Python venv ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
pip install -r web/backend/requirements-web.txt
deactivate

echo "=== 2. Node.js frontend ==="
cd web/frontend
npm ci
npm run build
cd "$APP_DIR"

echo "=== 3. .env ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Создан .env из .env.example — заполните секреты:"
  echo "    nano $APP_DIR/.env"
  echo "    Обязательно: ANTHROPIC_API_KEY, JWT_SECRET"
fi

echo "=== 4. Данные и права ==="
mkdir -p reports web/backend/data
if [ ! -f web/backend/data/users.json ]; then
  cp web/backend/data/users.json.example web/backend/data/users.json
fi
chown -R www-data:www-data reports web/backend/data .env
chmod 600 .env

echo "=== 5. systemd ==="
cp deploy/mc-agent.service /etc/systemd/system/mc-agent.service
systemctl daemon-reload
systemctl enable mc-agent
systemctl start mc-agent

echo "=== 6. Nginx ==="
cp deploy/nginx-agent.maxima-consulting.ru.conf /etc/nginx/sites-available/agent.maxima-consulting.ru
ln -sf /etc/nginx/sites-available/agent.maxima-consulting.ru /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo ""
echo "✅ Установка завершена."
echo "   Проверка: curl http://127.0.0.1:8001/api/health"
echo "   SSL: certbot --nginx -d agent.maxima-consulting.ru"
