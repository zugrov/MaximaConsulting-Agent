# Максима Консалтинг — AI-агент ведения клиента

Автоматизация цикла: **Лид -> Диагностика -> КП -> Проект -> Отчёт**.

## Установка

```bash
pip install -r requirements.txt
cp .env.example .env
# Вставь ANTHROPIC_API_KEY в .env
# По умолчанию:
# DEFAULT_MODEL=claude-sonnet-4-6
# FALLBACK_MODEL=claude-haiku-4-5-20251001
```

## Использование

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
