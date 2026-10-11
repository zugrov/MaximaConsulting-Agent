"""Отчёты: уникальность файлов, привязка к клиенту, доступ к файлам."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import support
from support import auth_headers, build_test_client


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 11, 9, 24, 16)


class ReportsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client, self.reports_dir = build_test_client(Path(self.tmp.name))
        self.analyst = auth_headers(self.client, "analyst")
        self.viewer = auth_headers(self.client, "viewer")

    def save_report(self, client_name: str, content: str, service: str = "Диагностика") -> str:
        response = self.client.post(
            "/api/reports",
            headers=self.analyst,
            json={"content": content, "client_name": client_name, "service_name": service},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["filename"]

    def create_client(self, name: str) -> int:
        response = self.client.post("/api/clients", headers=self.analyst, json={"name": name})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def report_filenames(self, client_id: int) -> list:
        response = self.client.get(f"/api/clients/{client_id}/reports", headers=self.viewer)
        self.assertEqual(response.status_code, 200)
        return [item["filename"] for item in response.json()]

    def test_same_second_reports_do_not_overwrite_each_other(self) -> None:
        with mock.patch("utils.report_files.datetime", FixedDatetime):
            first = self.save_report("ООО Ромашка", "# R1")
            second = self.save_report("ООО Ромашка", "# R2")

        self.assertNotEqual(first, second)
        self.assertEqual((self.reports_dir / first).read_text(encoding="utf-8"), "# R1")
        self.assertEqual((self.reports_dir / second).read_text(encoding="utf-8"), "# R2")

    def test_report_with_counter_keeps_client_and_service_in_listing(self) -> None:
        with mock.patch("utils.report_files.datetime", FixedDatetime):
            self.save_report("ООО Ромашка", "# R1", "НДС-аудит")
            self.save_report("ООО Ромашка", "# R2", "НДС-аудит")

        listing = self.client.get("/api/reports", headers=self.viewer).json()
        self.assertEqual({(r["client"], r["service"]) for r in listing}, {("ООО Ромашка", "НДС-аудит")})

    def test_client_sees_only_own_reports(self) -> None:
        romashka = self.create_client("ООО «Ромашка»")
        short = self.create_client("ООО Ром")
        other = self.create_client("ООО Лютик")

        own_with_quotes = self.save_report("ООО «Ромашка»", "# 1")
        own_without_quotes = self.save_report("ООО Ромашка", "# 2")

        self.assertCountEqual(
            self.report_filenames(romashka), [own_with_quotes, own_without_quotes]
        )
        self.assertEqual(self.report_filenames(short), [])
        self.assertEqual(self.report_filenames(other), [])

    def test_old_web_style_filename_is_still_matched(self) -> None:
        romashka = self.create_client("ООО «Ромашка»")
        legacy = "20260911_162841_ООО__Ромашка_--Финансовая_диагностика.md"
        (self.reports_dir / legacy).write_text("# old", encoding="utf-8")

        self.assertEqual(self.report_filenames(romashka), [legacy])

    def test_directory_and_non_markdown_are_not_downloadable(self) -> None:
        (self.reports_dir / "audit").mkdir()
        (self.reports_dir / "notes.txt").write_text("x", encoding="utf-8")

        for name in ("audit", "notes.txt", "missing.md"):
            for suffix in ("", "/download"):
                with self.subTest(name=name, suffix=suffix):
                    response = self.client.get(f"/api/reports/{name}{suffix}", headers=self.viewer)
                    self.assertEqual(response.status_code, 404)

    def test_saved_report_is_downloadable(self) -> None:
        filename = self.save_report("ООО Ромашка", "# Отчёт")
        response = self.client.get(f"/api/reports/{filename}/download", headers=self.viewer)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "# Отчёт")


if __name__ == "__main__":
    unittest.main()
