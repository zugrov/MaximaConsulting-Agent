#!/usr/bin/env python3
"""Сброс и подготовка изолированной БД и каталога отчётов для аудита."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.audit", override=True)

    db_raw = os.environ.get(
        "CLIENTS_DB_PATH", "web/backend/data/clients_audit.db"
    )
    db_path = Path(db_raw)
    if not db_path.is_absolute():
        db_path = ROOT / db_path

    reports_raw = os.environ.get("REPORTS_DIR", "reports/audit")
    reports_path = Path(reports_raw)
    if not reports_path.is_absolute():
        reports_path = ROOT / reports_path

    if db_path.exists():
        db_path.unlink()
        print(f"Удалена БД: {db_path.relative_to(ROOT)}")

    reports_path.mkdir(parents=True, exist_ok=True)
    for report in reports_path.glob("*.md"):
        report.unlink()
    print(f"Каталог отчётов: {reports_path.relative_to(ROOT)} (очищен *.md)")

    sys.path.insert(0, str(ROOT / "web" / "backend"))
    from services.clients_db import init_db  # noqa: E402

    init_db()
    print(f"Создана пустая БД: {db_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
