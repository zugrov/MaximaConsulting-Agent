#!/bin/bash
# Быстрый деплой mc-agent на VPS
# Запуск: sudo bash /var/www/mc-agent/deploy/deploy.sh

set -e

APP_DIR="/var/www/mc-agent"
cd "$APP_DIR"

echo "=== git pull ==="
git pull origin main

echo "=== Python-зависимости ==="
source venv/bin/activate
pip install -r requirements.txt -q
pip install -r web/backend/requirements-web.txt -q
deactivate

echo "=== Сборка frontend ==="
cd web/frontend
npm ci --silent
npm run build
cd "$APP_DIR"

echo "=== Права на данные ==="
mkdir -p reports web/backend/data
chown -R www-data:www-data reports web/backend/data
chmod -R 755 reports web/backend/data

echo "=== Перезапуск сервиса ==="
systemctl restart mc-agent
systemctl status mc-agent --no-pager

echo "=== Nginx ==="
nginx -t && systemctl reload nginx

echo "✅ mc-agent обновлён: https://agent.maxima-consulting.ru"
