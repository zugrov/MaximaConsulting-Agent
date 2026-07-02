#!/usr/bin/env python3
"""
Максима Консалтинг — AI-агент ведения клиента.
Автоматизация: Лид -> Диагностика -> КП -> Проект -> Отчёт.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
import pandas as pd
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()

app = typer.Typer(help="CLI агент финансового консалтинга")
console = Console()

ROOT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = ROOT_DIR / "skills"
REPORTS_DIR = ROOT_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))
CONSULTANT_NAME = os.getenv("CONSULTANT_NAME", "Максим Евгеньевич Зугров")
CONSULTANT_PHONE = os.getenv("CONSULTANT_PHONE", "+79106407686")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Максима Консалтинг")
BRAND_NAME = "maxima consulting"

SERVICES = {
    "1": ("diagnostic", "Финансовая диагностика"),
    "2": ("nds", "НДС-аудит и сопровождение"),
    "3": ("management_accounting", "Управленческий учёт"),
    "4": ("financial_model", "Финансовая модель"),
    "5": ("tax_optimization", "Налоговая оптимизация"),
    "6": ("cfo_light", "CFO-light (подписное сопровождение)"),
    "7": ("lead_qualification", "Квалификация лида + КП"),
    "8": ("full_cycle", "Полный цикл: диагностика -> КП -> план проекта"),
}


def safe_slug(value: str, max_len: int = 40) -> str:
    value = value.strip().replace(" ", "_")
    value = re.sub(r"[^\w\-_.]", "", value, flags=re.UNICODE)
    return value[:max_len] or "client"


def load_skill(skill_name: str) -> str:
    if skill_name == "full_cycle":
        parts = []
        for key, (skill, _) in SERVICES.items():
            if key == "8":
                continue
            skill_path = SKILLS_DIR / f"{skill}.md"
            if skill_path.exists():
                parts.append(skill_path.read_text(encoding="utf-8"))
        return "\n\n---\n\n".join(parts) if parts else "Методологии не найдены."

    skill_path = SKILLS_DIR / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return f"[Навык {skill_name} не найден; используй общую методологию финансового анализа]"


def load_client_data(file_path: str) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    ext = path.suffix.lower()
    payload: dict[str, Any] = {"source_file": str(path), "raw": "", "structured": {}}

    if ext in {".xlsx", ".xls"}:
        xl = pd.ExcelFile(path)
        sheets_data: dict[str, str] = {}
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet, header=0)
            df = df.dropna(how="all").fillna("")
            sheets_data[sheet] = df.to_string(index=False)
        payload["structured"] = sheets_data
        payload["raw"] = "\n\n".join(f"=== Лист: {name} ===\n{content}" for name, content in sheets_data.items())
        return payload

    if ext == ".csv":
        last_error: Exception | None = None
        for enc in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                df = pd.read_csv(path, encoding=enc)
                payload["structured"] = df.to_dict(orient="records")
                payload["raw"] = df.to_string(index=False)
                return payload
            except Exception as err:  # pragma: no cover
                last_error = err
        raise ValueError(f"Не удалось прочитать CSV: {last_error}") from last_error

    if ext == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        payload["structured"] = data
        payload["raw"] = json.dumps(data, ensure_ascii=False, indent=2)
        return payload

    payload["raw"] = path.read_text(encoding="utf-8", errors="ignore")
    return payload


def build_system_prompt(skill_name: str, service_name: str) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    skill_content = load_skill(skill_name)
    return f"""Ты — {CONSULTANT_NAME}, ведущий финансовый консультант компании {BRAND_NAME}.
Контакты консультанта: {CONSULTANT_PHONE}
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
6. Анализируй динамику за 2024, 2025 и 2026 годы (факт/прогноз), если эти данные есть у клиента.
7. Пиши в стиле опытного финансового партнёра: кратко, по делу, без воды и без канцелярита.
8. Избегай абстрактных формулировок вроде "комплексный подход", "индивидуальные решения" без цифр и действий.
9. Каждый вывод привязывай к управленческому решению: прибыль, cash flow, управляемость, риски, срок действия.
10. Используй название бренда только как "maxima consulting" (строчными, без иных вариантов).

## Формат отчёта
- Markdown
- H1: название отчёта и бренд "maxima consulting"
- H2 разделы
- Таблицы для сравнений и расчётов
- Ясный, деловой стиль для собственника бизнеса
- Обязательная логика документа: проблема -> данные -> выводы -> рекомендации -> next steps

Текущая услуга: {service_name}
"""


def call_model(client: anthropic.Anthropic, system_prompt: str, user_message: str) -> str:
    models = [MODEL]
    if FALLBACK_MODEL and FALLBACK_MODEL != MODEL:
        models.append(FALLBACK_MODEL)

    last_error: Exception | None = None
    for model_name in models:
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except Exception as err:  # pragma: no cover
            last_error = err
            console.print(f"[yellow]Не удалось вызвать модель {model_name}: {err}[/yellow]")

    raise RuntimeError(f"Все модели недоступны: {last_error}") from last_error


def run_analysis(client_data: dict[str, Any], skill_name: str, service_name: str, context: str) -> str:
    if not client_data.get("raw", "").strip():
        raise ValueError("В файле нет данных для анализа.")

    system_prompt = build_system_prompt(skill_name, service_name)
    user_message = f"""## ДАННЫЕ КЛИЕНТА
Источник: {client_data['source_file']}

{client_data['raw']}

## ЗАПРОС
Сделай профессиональный анализ по услуге "{service_name}".
{f"Дополнительный контекст: {context}" if context else ""}
В начале укажи дату, услугу и имя консультанта.
"""
    model_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    with console.status("[bold green]Анализирую данные клиента...[/bold green]"):
        return call_model(model_client, system_prompt, user_message)


def save_report(report_text: str, client_name: str, service_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_slug(client_name, 30)}_{safe_slug(service_name, 24)}.md"
    report_path = REPORTS_DIR / filename
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def show_menu() -> tuple[str, str]:
    console.print(
        Panel(
            f"[bold cyan]{COMPANY_NAME}[/bold cyan]\n[dim]AI-агент ведения клиента[/dim]",
            border_style="cyan",
        )
    )
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("№", width=4)
    table.add_column("Услуга")
    for key, (_, name) in SERVICES.items():
        table.add_row(key, name)
    console.print(table)

    service_code = Prompt.ask(
        "\n[bold]Выберите тип анализа[/bold]",
        choices=list(SERVICES.keys()),
        default="1",
    )
    return SERVICES[service_code]


@app.command()
def analyze(
    client_file: str = typer.Option("", "--file", "-f", help="Путь к файлу с данными клиента"),
    service: str = typer.Option("", "--service", "-s", help="Код услуги (1-8)"),
    client_name: str = typer.Option("Клиент", "--name", "-n", help="Название клиента"),
    context: str = typer.Option("", "--context", "-c", help="Дополнительный контекст"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Интерактивный режим"),
) -> None:
    """Запуск анализа клиента по выбранной методологии."""
    if not ANTHROPIC_API_KEY:
        console.print("[red]ANTHROPIC_API_KEY не задан в .env[/red]")
        raise typer.Exit(code=1)

    if not client_file:
        if interactive:
            client_file = Prompt.ask("[bold]Путь к файлу с данными клиента[/bold]")
        else:
            console.print("[red]Для неинтерактивного режима укажите --file[/red]")
            raise typer.Exit(code=1)

    try:
        client_data = load_client_data(client_file)
    except Exception as err:
        console.print(f"[red]Ошибка чтения файла: {err}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Файл загружен ({len(client_data['raw'])} символов)[/green]")

    if service and service in SERVICES:
        skill_name, service_name = SERVICES[service]
    else:
        skill_name, service_name = show_menu() if interactive else SERVICES["1"]

    try:
        report = run_analysis(client_data, skill_name, service_name, context)
    except Exception as err:
        console.print(f"[red]Ошибка анализа: {err}[/red]")
        raise typer.Exit(code=1)

    report_path = save_report(report, client_name, service_name)
    console.print(f"\n[bold green]Отчёт сохранён:[/bold green] {report_path}")
    console.print(Markdown(report))


@app.command("list-reports")
def list_reports() -> None:
    """Показать список ранее созданных отчётов."""
    reports = sorted(REPORTS_DIR.glob("*.md"), reverse=True)
    if not reports:
        console.print("[yellow]Отчётов пока нет.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Файл")
    table.add_column("Размер, KB", justify="right")
    table.add_column("Изменён")
    for path in reports:
        stat = path.stat()
        table.add_row(
            path.name,
            f"{stat.st_size / 1024:.1f}",
            datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
        )
    console.print(table)


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Операция прервана пользователем.[/yellow]")
        sys.exit(130)
