"""Общие настройки тестов: пути импорта и изолированное приложение во временной папке."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for path in (ROOT, ROOT / "web" / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

TEST_PASSWORD = "test-pass-123"


def build_test_client(tmp_dir: Path):
    """TestClient с отдельными users.json, clients.db и каталогом отчётов в tmp_dir.

    Рабочие данные не затрагиваются: пути подменяются до первого запроса,
    события startup не запускаются (TestClient используется без контекстного менеджера).
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from routers import auth as auth_router
    from routers import clients as clients_router
    from routers import reports as reports_router
    from services import auth as auth_service
    from services import clients_db

    reports_dir = tmp_dir / "reports"
    reports_dir.mkdir()
    auth_service.USERS_FILE = tmp_dir / "users.json"
    clients_db.DB_PATH = tmp_dir / "clients.db"
    reports_router.REPORTS_DIR = reports_dir
    clients_router.REPORTS_DIR = reports_dir
    clients_db.init_db()

    for role in ("admin", "analyst", "viewer"):
        auth_service.create_user(f"{role}@example.invalid", role, TEST_PASSWORD, role)

    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api/auth")
    app.include_router(clients_router.router, prefix="/api/clients")
    app.include_router(reports_router.router, prefix="/api/reports")
    return TestClient(app), reports_dir


def auth_headers(client, role: str) -> dict:
    response = client.post(
        "/api/auth/login",
        data={"username": f"{role}@example.invalid", "password": TEST_PASSWORD},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
