#!/usr/bin/env python3
"""Прогон всех услуг: клиенты в БД + отчёты в reports/."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "web" / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from consulting_agent import (  # noqa: E402
    SERVICES,
    load_client_data,
    run_analysis,
    save_report,
)
from services.clients_db import create_client, init_db  # noqa: E402

TEST_CASES = [
    {
        "service_code": "1",
        "client_name": "ООО СеверСтрой",
        "file": "data/clients/01_diagnostic_severstroy.md",
        "contact": "директор Игорь, +7 900 111-22-33",
        "status": "project",
        "amount": 180000,
        "notes": "Тест: финансовая диагностика",
    },
    {
        "service_code": "2",
        "client_name": "ООО Топком",
        "file": "data/clients/02_nds_topkom.md",
        "contact": "финдиректор Елена",
        "status": "project",
        "amount": 220000,
        "notes": "Тест: НДС-аудит 2026",
    },
    {
        "service_code": "3",
        "client_name": "ООО МедиаПлюс",
        "file": "data/clients/03_uu_mediaplus.md",
        "contact": "CEO Анна",
        "status": "lead",
        "amount": 150000,
        "notes": "Тест: управленческий учёт",
    },
    {
        "service_code": "4",
        "client_name": "ООО ФудЛайн",
        "file": "data/clients/04_finmodel_fudline.md",
        "contact": "собственник Рустам",
        "status": "project",
        "amount": 200000,
        "notes": "Тест: финансовая модель под кредит",
    },
    {
        "service_code": "5",
        "client_name": "ИП Зайцев М.А.",
        "file": "data/clients/05_tax_zaytsev.md",
        "contact": "zaytsev@mail.ru",
        "status": "lead",
        "amount": 90000,
        "notes": "Тест: налоговая оптимизация",
    },
    {
        "service_code": "6",
        "client_name": "ООО ЛогистикПро",
        "file": "data/clients/06_cfo_logisticpro.md",
        "contact": "собственник Виктор",
        "status": "project",
        "amount": 350000,
        "notes": "Тест: CFO-light",
    },
    {
        "service_code": "7",
        "client_name": "ООО СтартАйТи",
        "file": "data/clients/07_lead_startit.md",
        "contact": "@startit_ceo",
        "status": "lead",
        "amount": 150000,
        "notes": "Тест: квалификация лида + КП",
    },
    {
        "service_code": "8",
        "client_name": "ООО ТекстильНова",
        "file": "data/clients/08_fullcycle_tekstilnova.md",
        "contact": "коммерческий директор Ольга",
        "status": "project",
        "amount": 400000,
        "notes": "Тест: полный цикл",
    },
]


def main() -> int:
    init_db()
    ok, failed = 0, 0

    for case in TEST_CASES:
        code = case["service_code"]
        skill_name, service_name = SERVICES[code]
        file_path = ROOT / case["file"]

        print(f"\n=== Услуга {code}: {service_name} | {case['client_name']} ===")

        create_client(
            name=case["client_name"],
            contact=case.get("contact"),
            status=case.get("status", "lead"),
            amount=case.get("amount"),
            services=[service_name],
            notes=case.get("notes"),
        )

        try:
            client_data = load_client_data(str(file_path))
            report = run_analysis(client_data, skill_name, service_name, "")
            path = save_report(report, case["client_name"], service_name)
            print(f"OK → {path.name} ({len(report)} символов)")
            ok += 1
        except Exception as err:
            print(f"FAIL → {err}")
            failed += 1

    print(f"\nИтого: успешно {ok}, ошибок {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
