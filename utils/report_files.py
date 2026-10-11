"""Имена файлов отчётов — единые для CLI и веб-бэкенда."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

CLIENT_MAX_LEN = 30
SERVICE_MAX_LEN = 24
MAX_ATTEMPTS = 1000


def resolve_reports_dir(root_dir: Path) -> Path:
    """Каталог отчётов: REPORTS_DIR из окружения (относительный — от корня проекта)."""
    raw = os.getenv("REPORTS_DIR")
    if not raw:
        return root_dir / "reports"
    path = Path(raw)
    return path if path.is_absolute() else root_dir / path


def safe_slug(value: str, max_len: int = 40) -> str:
    value = value.strip().replace(" ", "_")
    value = re.sub(r"[^\w\-_.]", "", value, flags=re.UNICODE)
    return value[:max_len] or "client"


def client_key(name: str) -> str:
    """Ключ сравнения имени клиента с именем из файла отчёта: без регистра и знаков."""
    return re.sub(r"[\W_]+", "", safe_slug(name, CLIENT_MAX_LEN).lower())


def save_report_file(
    reports_dir: Path, content: str, client_name: str, service_name: str
) -> Path:
    """Сохраняет отчёт, не перезаписывая существующие файлы.

    Имя: <дата>_<время>[-N]_<клиент>--<услуга>.md. Разделитель "--" нужен парсеру
    web/backend/routers/reports.py (_parse_meta); счётчик -N стоит в части времени.
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tail = f"{safe_slug(client_name, CLIENT_MAX_LEN)}--{safe_slug(service_name, SERVICE_MAX_LEN)}.md"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        suffix = "" if attempt == 1 else f"-{attempt}"
        path = reports_dir / f"{stamp}{suffix}_{tail}"
        try:
            with path.open("x", encoding="utf-8") as file:
                file.write(content)
        except FileExistsError:
            continue
        return path
    raise RuntimeError("Не удалось подобрать свободное имя файла отчёта")
