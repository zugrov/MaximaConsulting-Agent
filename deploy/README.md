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
sudo nano .env   # LLM_ROUTER_INTERNAL_SECRET, JWT_SECRET, GOOGLE_DRIVE_API_KEY
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
| `LLM_ROUTER_URL` | Адрес llm-router (на VPS: `http://127.0.0.1:8020`) |
| `LLM_ROUTER_INTERNAL_SECRET` | Секрет, совпадающий с `INTERNAL_SECRET` в llm-router |
| `LLM_ROUTER_PROJECT` | `maxima-consulting` |
| `LLM_ROUTER_TASK_TYPE` | `client_report` |
| `JWT_SECRET` | Секрет для JWT (сгенерировать: `python3 -c "import secrets; print(secrets.token_hex(32))"`) |
| `GOOGLE_DRIVE_API_KEY` | Google Drive API (для загрузки папок) |
| `ALLOWED_ORIGINS` | `https://agent.maxima-consulting.ru` |

На VPS должен быть запущен **llm-router** на `127.0.0.1:8020`. CLI и веб обращаются к нему, а не к провайдерам LLM напрямую.

## Полезные команды

```bash
systemctl status mc-agent
journalctl -u mc-agent -f
curl http://127.0.0.1:8001/api/health
nginx -t
```

## LLM

Модель и fallback настраиваются в **llm-router**, не в mc-agent.
