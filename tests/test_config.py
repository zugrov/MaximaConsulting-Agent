"""Конфигурация из окружения и запуск приложения (main.py) на временных данных."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support  # noqa: F401
from utils.report_files import resolve_reports_dir


class ResolveReportsDirTest(unittest.TestCase):
    def resolve(self, value):
        env = {} if value is None else {"REPORTS_DIR": value}
        with mock.patch.dict(os.environ, env, clear=True):
            return resolve_reports_dir(Path("/project"))

    def test_default_is_reports_in_project_root(self) -> None:
        self.assertEqual(self.resolve(None), Path("/project/reports"))

    def test_relative_path_is_resolved_from_project_root(self) -> None:
        self.assertEqual(self.resolve("reports/audit"), Path("/project/reports/audit"))

    def test_absolute_path_is_used_as_is(self) -> None:
        self.assertEqual(self.resolve("/tmp/x"), Path("/tmp/x"))


class AppStartupTest(unittest.TestCase):
    def test_startup_creates_clients_db(self) -> None:
        from fastapi.testclient import TestClient

        from services import clients_db

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(clients_db, "DB_PATH", Path(tmp) / "clients.db"):
                import main

                with TestClient(main.app) as client:
                    self.assertEqual(client.get("/api/health").json(), {"status": "ok"})
                self.assertTrue((Path(tmp) / "clients.db").exists())


if __name__ == "__main__":
    unittest.main()
