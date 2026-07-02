from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

import anthropic

ROOT_DIR = Path(__file__).resolve().parents[3]  # consulting-agent/
SKILLS_DIR = ROOT_DIR / "skills"

MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))
CONSULTANT_NAME = os.getenv("CONSULTANT_NAME", "Максим Зугров")
CONSULTANT_PHONE = os.getenv("CONSULTANT_PHONE", "+79106407686")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Максима Консалтинг")

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
    """Генерирует SSE-токены от Anthropic API."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        yield "data: [ОШИБКА: ANTHROPIC_API_KEY не задан в .env]\n\n"
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

    client = anthropic.AsyncAnthropic(api_key=api_key)
    try:
        async with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for text in stream.text_stream:
                escaped = text.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
        yield "data: [DONE]\n\n"
    except anthropic.AuthenticationError:
        yield "data: [ОШИБКА: Неверный ANTHROPIC_API_KEY]\n\n"
    except Exception as e:
        yield f"data: [ОШИБКА: {str(e)[:200]}]\n\n"
