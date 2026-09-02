from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parents[3]  # consulting-agent/
SKILLS_DIR = ROOT_DIR / "skills"

MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))
CONSULTANT_NAME = os.getenv("CONSULTANT_NAME", "Максим Зугров")
CONSULTANT_PHONE = os.getenv("CONSULTANT_PHONE", "+79106407686")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Максима Консалтинг")

# llm-router — общий сервис маршрутизации LLM для нескольких MVP
# (см. https://github.com/zugrov/llm-router). Модель для task_type=client_report
# выбирает сам llm-router, здесь она не задаётся.
# consulting-agent — systemd-процесс на хосте VPS (не в Docker), поэтому обращается
# к llm-router через опубликованный на localhost порт, а не по имени контейнера.
LLM_ROUTER_URL = os.getenv("LLM_ROUTER_URL", "http://127.0.0.1:8020")
LLM_ROUTER_INTERNAL_SECRET = os.getenv("LLM_ROUTER_INTERNAL_SECRET", "")

SERVICES: dict[str, tuple[str, str]] = {
    "1": ("diagnostic", "Финансовая диагностика"),
    "2": ("nds", "НДС-аудит и сопровождение"),
    "3": ("management_accounting", "Управленческий учёт"),
    "4": ("financial_model", "Финансовая модель"),
    "5": ("tax_optimization", "Налоговая оптимизация"),
    "6": ("cfo_light", "CFO-light (подписное сопровождение)"),
    "7": ("lead_qualification", "Квалификация лида + КП"),
    "8": ("full_cycle", "Полный цикл: диагностика → КП → план проекта"),
}


def get_services() -> list[dict]:
    return [{"code": code, "skill": skill, "name": name} for code, (skill, name) in SERVICES.items()]


def load_skill(skill_name: str) -> str:
    if skill_name == "full_cycle":
        parts: list[str] = []
        for code, (skill, _) in SERVICES.items():
            if code == "8":
                continue
            p = SKILLS_DIR / f"{skill}.md"
            if p.exists():
                parts.append(p.read_text(encoding="utf-8"))
        return "\n\n---\n\n".join(parts) or "Методологии не найдены."
    path = SKILLS_DIR / f"{skill_name}.md"
    return path.read_text(encoding="utf-8") if path.exists() else f"[Навык {skill_name} не найден]"


def build_system_prompt(skill_name: str, service_name: str) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    skill_content = load_skill(skill_name)
    return f"""Ты — {CONSULTANT_NAME}, ведущий финансовый консультант и основатель maxima consulting.
Контакты: {CONSULTANT_PHONE}
Сегодня: {today}
Целевая аудитория: собственники и директора МСБ в РФ (выручка 5–80 млн руб./год).

## Методология
{skill_content}

## Правила ответа
1. Используй конкретные цифры из входных данных.
2. Указывай риски с пометками: 🔴 / 🟡 / 🟢.
3. Формат денег: 1 234 567 руб.
4. В конце каждого раздела давай вывод и действие.
5. Последний блок: "Следующий шаг" с предложением услуги.
6. Анализируй динамику за 2024, 2025 и 2026 годы (факт/прогноз), если данные есть.
7. Пиши кратко, по делу, без воды и канцелярита.
8. Каждый вывод привязывай к управленческому решению.
9. Используй название бренда только как "maxima consulting" (строчными).

## Формат отчёта
- Markdown: H1 название + "maxima consulting", H2 разделы, H3 подразделы
- Таблицы для сравнений и расчётов (Markdown-таблицы)
- Обязательная логика: проблема → данные → выводы → рекомендации → next steps

Текущая услуга: {service_name}
"""


async def stream_analysis(
    raw_content: str,
    source_file: str,
    truncated: bool,
    skill_name: str,
    service_name: str,
    context: str = "",
) -> AsyncGenerator[str, None]:
    """Генерирует SSE-токены через llm-router (task_type=client_report)."""
    if not LLM_ROUTER_INTERNAL_SECRET:
        yield "data: [ОШИБКА: LLM_ROUTER_INTERNAL_SECRET не задан в .env]\n\n"
        return

    system_prompt = build_system_prompt(skill_name, service_name)
    truncation_note = "\n\n⚠️ *Документ обрезан до 100 000 символов*" if truncated else ""
    user_message = f"""## ДАННЫЕ КЛИЕНТА
Источник: {source_file}{truncation_note}

{raw_content}

## ЗАПРОС
Сделай профессиональный анализ по услуге "{service_name}".
{f"Дополнительный контекст: {context}" if context else ""}
В начале укажи дату, услугу и имя консультанта."""

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{LLM_ROUTER_URL}/v1/complete/stream",
                headers={"X-Internal-Secret": LLM_ROUTER_INTERNAL_SECRET},
                json={
                    "project": "maxima-consulting",
                    "task_type": "client_report",
                    "system": system_prompt,
                    "prompt": user_message,
                    "max_tokens": MAX_TOKENS,
                },
            ) as response:
                if response.status_code != 200:
                    yield f"data: [ОШИБКА: llm-router вернул HTTP {response.status_code}]\n\n"
                    return
                async for line in response.aiter_lines():
                    trimmed = line.strip()
                    if not trimmed.startswith("data: "):
                        continue
                    try:
                        event = json.loads(trimmed[len("data: "):])
                    except ValueError:
                        continue  # skip malformed SSE chunk
                    if event.get("error"):
                        yield f"data: [ОШИБКА: {event.get('error_code', 'STREAM_INTERRUPTED')}]\n\n"
                        return
                    if event.get("done"):
                        break
                    delta = event.get("delta")
                    if delta:
                        escaped = delta.replace("\n", "\\n")
                        yield f"data: {escaped}\n\n"
        yield "data: [DONE]\n\n"
    except httpx.HTTPError as e:
        yield f"data: [ОШИБКА: llm-router недоступен ({str(e)[:150]})]\n\n"
