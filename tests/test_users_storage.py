"""Хранилище users.json: параллельные изменения не теряются, запись атомарна."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import support  # noqa: F401
from services import auth


class UsersStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(auth, "USERS_FILE", Path(self.tmp.name) / "users.json")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_parallel_user_creation_loses_nothing(self) -> None:
        threads = [
            threading.Thread(
                target=auth.create_user,
                args=(f"u{n}@example.invalid", f"u{n}", "password-123", "viewer"),
            )
            for n in range(12)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        users = json.loads(auth.USERS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(users), 12)
        self.assertEqual(len({u["id"] for u in users}), 12)

    def test_parallel_password_change_and_role_change_both_apply(self) -> None:
        user = auth.create_user("a@example.invalid", "A", "password-123", "viewer")
        threads = [
            threading.Thread(target=auth.set_user_password, args=(user["id"], "new-password-456")),
            threading.Thread(target=auth.update_user_role, args=(user["id"], "analyst")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        saved = auth.get_user_by_email("a@example.invalid")
        self.assertEqual(saved["role"], "analyst")
        self.assertTrue(auth.verify_password("new-password-456", saved["password_hash"]))

    def test_no_temp_files_left_after_save(self) -> None:
        auth.create_user("a@example.invalid", "A", "password-123", "viewer")
        self.assertEqual([p.name for p in Path(self.tmp.name).iterdir()], ["users.json"])


if __name__ == "__main__":
    unittest.main()
