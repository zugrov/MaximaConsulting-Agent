"""Клиенты: валидация ввода и очистка полей через PATCH."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401
from support import auth_headers, build_test_client


class ClientsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client, _ = build_test_client(Path(self.tmp.name))
        self.analyst = auth_headers(self.client, "analyst")

    def post(self, body: dict):
        return self.client.post("/api/clients", headers=self.analyst, json=body)

    def test_invalid_input_is_rejected(self) -> None:
        invalid_bodies = {
            "пустое имя": {"name": ""},
            "имя из пробелов": {"name": "   "},
            "отрицательная сумма": {"name": "X", "amount": -500},
            "сумма не число": {"name": "X", "amount": "abc"},
            "неизвестная услуга": {"name": "X", "services": ["999"]},
            "html вместо кода услуги": {"name": "X", "services": ["<b>x</b>"]},
            "ссылка javascript": {"name": "X", "cloud_url": "javascript:alert(1)"},
            "неизвестный статус": {"name": "X", "status": "deleted"},
        }
        for label, body in invalid_bodies.items():
            with self.subTest(label):
                self.assertEqual(self.post(body).status_code, 422)
        self.assertEqual(self.client.get("/api/clients", headers=self.analyst).json(), [])

    def test_valid_input_is_normalized(self) -> None:
        response = self.post(
            {"name": "  ООО Ромашка  ", "amount": 0, "services": ["1", "2", "1"],
             "cloud_url": "https://disk.yandex.ru/d/abc"}
        )
        self.assertEqual(response.status_code, 201, response.text)
        created = response.json()
        self.assertEqual(created["name"], "ООО Ромашка")
        self.assertEqual(created["amount"], 0)
        self.assertEqual(created["services"], ["1", "2"])

    def test_patch_null_clears_amount_but_keeps_unsent_fields(self) -> None:
        created = self.post({"name": "ООО Ромашка", "amount": 150000, "contact": "Иван"}).json()
        url = f"/api/clients/{created['id']}"

        cleared = self.client.patch(url, headers=self.analyst, json={"amount": None})
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.json()["amount"])
        self.assertEqual(cleared.json()["contact"], "Иван")

        zero = self.client.patch(url, headers=self.analyst, json={"amount": 0})
        self.assertEqual(zero.json()["amount"], 0)

    def test_patch_cannot_null_required_fields(self) -> None:
        created = self.post({"name": "ООО Ромашка", "services": ["3"]}).json()
        url = f"/api/clients/{created['id']}"

        response = self.client.patch(
            url, headers=self.analyst, json={"name": None, "status": None, "services": None}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "ООО Ромашка")
        self.assertEqual(response.json()["status"], "lead")
        self.assertEqual(response.json()["services"], ["3"])

    def test_patch_validates_input(self) -> None:
        created = self.post({"name": "ООО Ромашка"}).json()
        url = f"/api/clients/{created['id']}"
        for body in ({"name": "  "}, {"amount": -1}, {"services": ["0"]}):
            with self.subTest(body=body):
                self.assertEqual(
                    self.client.patch(url, headers=self.analyst, json=body).status_code, 422
                )

    def test_analyst_sees_only_own_clients(self) -> None:
        own = self.post({"name": "Свой клиент"}).json()
        admin = auth_headers(self.client, "admin")
        foreign = self.client.post(
            "/api/clients", headers=admin, json={"name": "Чужой клиент"}
        ).json()

        names = [item["name"] for item in self.client.get("/api/clients", headers=self.analyst).json()]
        self.assertEqual(names, ["Свой клиент"])
        self.assertEqual(
            self.client.get(f"/api/clients/{foreign['id']}", headers=self.analyst).status_code, 404
        )
        self.assertEqual(self.client.get(f"/api/clients/{own['id']}", headers=self.analyst).status_code, 200)

        admin_names = {item["name"] for item in self.client.get("/api/clients", headers=admin).json()}
        self.assertEqual(admin_names, {"Свой клиент", "Чужой клиент"})

    def test_only_admin_can_assign_owner_and_unassigned_stays_with_admin(self) -> None:
        self.assertEqual(self.post({"name": "X", "owner_id": 1}).status_code, 403)
        admin = auth_headers(self.client, "admin")
        created = self.post({"name": "Общий"}).json()
        cleared = self.client.patch(
            f"/api/clients/{created['id']}", headers=admin, json={"owner_id": None}
        )
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertIsNone(cleared.json()["owner_id"])
        self.assertEqual(self.client.get("/api/clients", headers=self.analyst).json(), [])

    def test_other_analyst_cannot_read_report_of_foreign_client(self) -> None:
        self.post({"name": "ООО Ромашка"})
        saved = self.client.post(
            "/api/reports",
            headers=self.analyst,
            json={"content": "# секрет", "client_name": "ООО Ромашка", "service_name": "Диагностика"},
        )
        self.assertEqual(saved.status_code, 201, saved.text)
        filename = saved.json()["filename"]

        admin = auth_headers(self.client, "admin")
        created = self.client.post(
            "/api/auth/users",
            headers=admin,
            json={"email": "other@example.invalid", "name": "Другой", "password": "other-pass-1",
                  "role": "analyst"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        login = self.client.post(
            "/api/auth/login",
            data={"username": "other@example.invalid", "password": "other-pass-1"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        self.assertEqual(self.client.get("/api/reports", headers=headers).json(), [])
        self.assertEqual(self.client.get(f"/api/reports/{filename}", headers=headers).status_code, 404)
        self.assertEqual(self.client.get("/api/reports", headers=admin).status_code, 200)


if __name__ == "__main__":
    unittest.main()
