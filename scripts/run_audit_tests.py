#!/usr/bin/env python3
"""
Прогон услуг на синтетических кейсах (data/audit/clients/).
Не читает data/clients/* и не пишет в production clients.db / reports/.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "web" / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.audit", override=True)

from consulting_agent import (  # noqa: E402
    SERVICES,
    load_client_data,
    run_analysis,
    save_report,
)
from services.clients_db import DB_PATH, create_client, init_db  # noqa: E402

AUDIT_CLIENTS = ROOT / "data" / "audit" / "clients"

TEST_CASES = [
    {
        "service_code": "1",
        "client_name": 'ООО «Синт-Кейс-01»',
        "file": AUDIT_CLIENTS / "01_diagnostic.md",
        "contact": "demo-01@example.invalid",
        "status": "project",
        "amount": 180000,
        "notes": "Аудит: финансовая диагностика (синтетика)",
    },
    {
        "service_code": "2",
        "client_name": 'ООО «Синт-Кейс-02»',
        "file": AUDIT_CLIENTS / "02_nds.md",
        "contact": "demo-02@example.invalid",
        "status": "project",
        "amount": 220000,
        "notes": "Аудит: НДС-аудит 2026 (синтетика)",
    },
    {
        "service_code": "3",
        "client_name": 'ООО «Синт-Кейс-03»',
        "file": AUDIT_CLIENTS / "03_management_accounting.md",
        "contact": "demo-03@example.invalid",
        "status": "lead",
        "amount": 150000,
        "notes": "Аудит: управленческий учёт (синтетика)",
    },
    {
        "service_code": "4",
        "client_name": 'ООО «Синт-Кейс-04»',
        "file": AUDIT_CLIENTS / "04_financial_model.md",
        "contact": "demo-04@example.invalid",
        "status": "project",
        "amount": 200000,
        "notes": "Аудит: финансовая модель (синтетика)",
    },
    {
        "service_code": "5",
        "client_name": "ИП Демо-Вендор А.Б.",
        "file": AUDIT_CLIENTS / "05_tax.md",
        "contact": "demo-05@example.invalid",
        "status": "lead",
        "amount": 90000,
        "notes": "Аудит: налоговая оптимизация (синтетика)",
    },
    {
        "service_code": "6",
        "client_name": 'ООО «Синт-Кейс-06»',
        "file": AUDIT_CLIENTS / "06_cfo_light.md",
        "contact": "demo-06@example.invalid",
        "status": "project",
        "amount": 350000,
        "notes": "Аудит: CFO-light (синтетика)",
    },
    {
        "service_code": "7",
        "client_name": 'ООО «Синт-Кейс-07»',
        "file": AUDIT_CLIENTS / "07_lead.md",
        "contact": "demo-07@example.invalid",
        "status": "lead",
        "amount": 150000,
        "notes": "Аудит: квалификация лида (синтетика)",
    },
    {
        "service_code": "8",
        "client_name": 'ООО «Синт-Кейс-08»',
        "file": AUDIT_CLIENTS / "08_full_cycle.md",
        "contact": "demo-08@example.invalid",
        "status": "project",
        "amount": 400000,
        "notes": "Аудит: полный цикл (синтетика)",
    },
]


def main() -> int:
    print(f"БД аудита: {DB_PATH}")
    init_db()
    ok, failed = 0, 0

    for case in TEST_CASES:
        code = case["service_code"]
        skill_name, service_name = SERVICES[code]
        file_path = case["file"]

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
