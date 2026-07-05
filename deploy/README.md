# Деплой на VPS (agent.maxima-consulting.ru)

Сервер: Beget VPS, Ubuntu 24.04. Порт приложения: **8001**. Nginx проксирует домен.

## Архитектура

```
agent.maxima-consulting.ru
        │
        ▼
     Nginx (80/443)
        ├── /        → web/frontend/dist (React SPA)
        └── /api/    → 127.0.0.1:8001 (FastAPI / uvicorn)
```

## Первый деплой

```bash
# На VPS
cd /var/www
git clone https://github.com/zugrov/MaximaConsulting-Agent.git mc-agent
cd mc-agent
sudo bash deploy/setup-first-time.sh
sudo nano .env   # ANTHROPIC_API_KEY, JWT_SECRET, GOOGLE_DRIVE_API_KEY
sudo systemctl restart mc-agent

# SSL
sudo certbot --nginx -d agent.maxima-consulting.ru
```

## Обновление

```bash
sudo bash /var/www/mc-agent/deploy/deploy.sh
```

## Переменные .env (production)

| Переменная | Описание |
|---|---|
| `ANTHROPIC_API_KEY` | Ключ Anthropic API |
| `JWT_SECRET` | Секрет для JWT (сгенерировать: `python3 -c "import secrets; print(secrets.token_hex(32))"`) |
| `GOOGLE_DRIVE_API_KEY` | Google Drive API (для загрузки папок) |
| `ALLOWED_ORIGINS` | Опционально: `https://agent.maxima-consulting.ru` |

## Полезные команды

```bash
systemctl status mc-agent
journalctl -u mc-agent -f
curl http://127.0.0.1:8001/api/health
nginx -t
```

## API из РФ

При блокировке Anthropic API рассмотрите OpenRouter как шлюз (настройка в `.env`).
