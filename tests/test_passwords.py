"""Смена пароля: своего (с проверкой текущего) и сброс администратором."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401
from support import TEST_PASSWORD, auth_headers, build_test_client

NEW_PASSWORD = "new-pass-456"


class PasswordsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client, _ = build_test_client(Path(self.tmp.name))

    def login(self, role: str, password: str):
        return self.client.post(
            "/api/auth/login", data={"username": f"{role}@example.invalid", "password": password}
        )

    def change_own(self, role: str, current: str, new: str):
        return self.client.post(
            "/api/auth/me/password",
            headers=auth_headers(self.client, role),
            json={"current_password": current, "new_password": new},
        )

    def test_old_token_is_rejected_after_password_change(self) -> None:
        headers = auth_headers(self.client, "analyst")
        changed = self.client.post(
            "/api/auth/me/password",
            headers=headers,
            json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
        )
        self.assertEqual(changed.status_code, 204, changed.text)
        again = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(again.status_code, 401)
        self.assertEqual(self.login("analyst", NEW_PASSWORD).status_code, 200)

    def test_user_changes_own_password(self) -> None:
        response = self.change_own("analyst", TEST_PASSWORD, NEW_PASSWORD)
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(self.login("analyst", TEST_PASSWORD).status_code, 401)
        self.assertEqual(self.login("analyst", NEW_PASSWORD).status_code, 200)

    def test_wrong_current_short_and_same_password_are_rejected(self) -> None:
        self.assertEqual(self.change_own("analyst", "wrong-pass-1", NEW_PASSWORD).status_code, 400)
        self.assertEqual(self.change_own("analyst", TEST_PASSWORD, "short").status_code, 422)
        self.assertEqual(self.change_own("analyst", TEST_PASSWORD, TEST_PASSWORD).status_code, 422)
        self.assertEqual(self.login("analyst", TEST_PASSWORD).status_code, 200)

    def test_change_requires_authentication(self) -> None:
        response = self.client.post(
            "/api/auth/me/password",
            json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
        )
        self.assertEqual(response.status_code, 401)

    def test_admin_resets_password_of_another_user(self) -> None:
        users = self.client.get("/api/auth/users", headers=auth_headers(self.client, "admin"))
        viewer_id = next(u["id"] for u in users.json() if u["role"] == "viewer")

        response = self.client.put(
            f"/api/auth/users/{viewer_id}/password",
            headers=auth_headers(self.client, "admin"),
            json={"new_password": NEW_PASSWORD},
        )
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(self.login("viewer", TEST_PASSWORD).status_code, 401)
        self.assertEqual(self.login("viewer", NEW_PASSWORD).status_code, 200)

    def test_only_admin_can_reset_and_unknown_user_gives_404(self) -> None:
        for role in ("analyst", "viewer"):
            response = self.client.put(
                "/api/auth/users/1/password",
                headers=auth_headers(self.client, role),
                json={"new_password": NEW_PASSWORD},
            )
            self.assertEqual(response.status_code, 403)
        response = self.client.put(
            "/api/auth/users/999/password",
            headers=auth_headers(self.client, "admin"),
            json={"new_password": NEW_PASSWORD},
        )
        self.assertEqual(response.status_code, 404)

    def test_new_user_needs_password_of_min_length(self) -> None:
        response = self.client.post(
            "/api/auth/users",
            headers=auth_headers(self.client, "admin"),
            json={"email": "a@example.com", "name": "A", "password": "1234567"},
        )
        self.assertEqual(response.status_code, 422)

    def test_password_over_bcrypt_limit_is_rejected_not_server_error(self) -> None:
        # 72 байта — предел bcrypt; кириллица занимает по 2 байта на символ
        for password in ("я" * 37, "x" * 73):
            self.assertEqual(self.change_own("analyst", TEST_PASSWORD, password).status_code, 422)
            created = self.client.post(
                "/api/auth/users",
                headers=auth_headers(self.client, "admin"),
                json={"email": "b@example.com", "name": "B", "password": password},
            )
            self.assertEqual(created.status_code, 422)
        self.assertEqual(self.change_own("analyst", TEST_PASSWORD, "x" * 72).status_code, 204)

    def test_login_with_overlong_password_is_plain_401(self) -> None:
        self.assertEqual(self.login("analyst", "x" * 200).status_code, 401)


if __name__ == "__main__":
    unittest.main()
