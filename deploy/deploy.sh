#!/bin/bash
# Быстрый деплой mc-agent на VPS
# Запуск: sudo bash /var/www/mc-agent/deploy/deploy.sh

set -e

APP_DIR="/var/www/mc-agent"
DEPLOY_USER="${DEPLOY_USER:-www-data}"

cd "$APP_DIR"

echo "=== git pull ==="
# Git 2.35+ блокирует pull в «чужом» каталоге (dubious ownership), если скрипт
# запущен от root, а репозиторий принадлежит www-data.
# -c не пишет в ~/.gitconfig: у www-data нет права на /var/www/.gitconfig,
# а каталог репозитория принадлежит другому пользователю
sudo -u "$DEPLOY_USER" git -c safe.directory="$APP_DIR" -C "$APP_DIR" pull origin main

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
