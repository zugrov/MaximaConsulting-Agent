# Максима Консалтинг — AI-агент ведения клиента

Автоматизация цикла: **Лид -> Диагностика -> КП -> Проект -> Отчёт**.

**Продакшен:** https://agent.maxima-consulting.ru

## Что внутри

| Компонент | Описание |
|-----------|----------|
| `consulting_agent.py` | CLI для генерации отчётов |
| `web/` | Веб-интерфейс (React + FastAPI) |
| `skills/` | Методологии по услугам |
| `deploy/` | Деплой на VPS |

CLI и веб используют один и тот же **llm-router** — агент не обращается к провайдерам LLM напрямую.

## Установка

Перед запуском должен быть доступен [llm-router](https://github.com/zugrov/llm-router) на `127.0.0.1:8020` (или по адресу из `LLM_ROUTER_URL`).

```bash
pip install -r requirements.txt
cp .env.example .env
# Заполнить LLM_ROUTER_INTERNAL_SECRET (тот же секрет, что INTERNAL_SECRET в llm-router)
```

Проверка роутера:

```bash
curl -f http://127.0.0.1:8020/health
```

### Переменные окружения (LLM)

| Переменная | Описание |
|---|---|
| `LLM_ROUTER_URL` | Адрес llm-router (по умолчанию `http://127.0.0.1:8020`) |
| `LLM_ROUTER_INTERNAL_SECRET` | Секрет, совпадающий с `INTERNAL_SECRET` в llm-router |
| `LLM_ROUTER_PROJECT` | `maxima-consulting` |
| `LLM_ROUTER_TASK_TYPE` | `client_report` |
| `MAX_TOKENS` | Лимит токенов ответа (по умолчанию `8000`) |

Модель (`claude-sonnet-5`, fallback и т.д.) настраивается **в llm-router**, не здесь.

## CLI

### Интерактивный режим

```bash
python consulting_agent.py analyze
```

### С указанием файла

```bash
python consulting_agent.py analyze --file data/clients/client.xlsx --name "ООО Ромашка"
```

### Конкретная услуга

```bash
# 1=Диагностика, 2=НДС, 3=УУ, 4=Финмодель, 5=НалОпт, 6=CFO-light, 7=Лид+КП, 8=Полный цикл
python consulting_agent.py analyze --file data/clients/test_client.md --service 2 --name "ООО ТД Центр" --no-interactive
```

### Список отчётов

```bash
python consulting_agent.py list-reports
```

## Веб-версия

Инструкция: `web/ИНСТРУКЦИЯ.md`

```bash
cd web && bash start.sh
```

## Деплой

```bash
sudo bash /var/www/mc-agent/deploy/deploy.sh
```

Подробнее: `deploy/README.md`

## Форматы данных клиента

- `.xlsx`, `.xls`
- `.csv`
- `.json`
- `.txt`, `.md`

## Мини-чек-лист качества отчёта

- Есть конкретные расчёты и суммы.
- Есть риски (`🔴`, `🟡`, `🟢`).
- Есть приоритизация действий.
- Есть блок **Следующий шаг**.

## Brand Compliance (`maxima consulting`)

- Название бренда в отчётах: только `maxima consulting` (строчными).
- Тон: прямой, senior, без воды и без абстрактных обещаний.
- Целевая аудитория: МСБ РФ с выручкой `5–80 млн руб./год`.
- Структура deliverable: проблема -> данные -> выводы -> рекомендации -> next steps.
