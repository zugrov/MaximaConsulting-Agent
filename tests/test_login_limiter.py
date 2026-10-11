"""Ограничение неудачных попыток входа."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401
from services.login_limiter import LoginLimiter
from support import TEST_PASSWORD, build_test_client


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class LoginLimiterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.limiter = LoginLimiter(max_per_account=3, max_per_ip=5, window_sec=600, clock=self.clock)

    def fail(self, ip: str, email: str, times: int) -> None:
        for _ in range(times):
            self.limiter.register_failure(ip, email)

    def test_account_is_blocked_after_limit_and_unblocked_after_window(self) -> None:
        self.fail("1.1.1.1", "a@x.ru", 2)
        self.assertEqual(self.limiter.retry_after("1.1.1.1", "a@x.ru"), 0)

        self.fail("1.1.1.1", "A@x.ru", 1)  # регистр email не важен
        self.assertGreater(self.limiter.retry_after("1.1.1.1", "a@x.ru"), 0)

        self.clock.now += 601
        self.assertEqual(self.limiter.retry_after("1.1.1.1", "a@x.ru"), 0)

    def test_other_account_and_other_ip_are_not_blocked(self) -> None:
        self.fail("1.1.1.1", "a@x.ru", 3)
        self.assertEqual(self.limiter.retry_after("1.1.1.1", "b@x.ru"), 0)
        self.assertEqual(self.limiter.retry_after("2.2.2.2", "a@x.ru"), 0)

    def test_ip_is_blocked_when_spraying_across_accounts(self) -> None:
        for index in range(5):
            self.limiter.register_failure("1.1.1.1", f"user{index}@x.ru")
        self.assertGreater(self.limiter.retry_after("1.1.1.1", "new@x.ru"), 0)
        self.assertEqual(self.limiter.retry_after("2.2.2.2", "new@x.ru"), 0)

    def test_success_resets_account_counter(self) -> None:
        self.fail("1.1.1.1", "a@x.ru", 2)
        self.limiter.reset_account("1.1.1.1", "a@x.ru")
        self.fail("1.1.1.1", "a@x.ru", 2)
        self.assertEqual(self.limiter.retry_after("1.1.1.1", "a@x.ru"), 0)


class LoginApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client, _ = build_test_client(Path(self.tmp.name))

    def login(self, password: str, email: str = "admin@example.invalid"):
        return self.client.post("/api/auth/login", data={"username": email, "password": password})

    def test_correct_password_is_rejected_after_five_failures(self) -> None:
        for _ in range(5):
            self.assertEqual(self.login("wrong").status_code, 401)

        blocked = self.login(TEST_PASSWORD)
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)
        self.assertEqual(self.login(TEST_PASSWORD, "analyst@example.invalid").status_code, 200)

    def test_successful_logins_do_not_count_as_failures(self) -> None:
        for _ in range(10):
            self.assertEqual(self.login(TEST_PASSWORD).status_code, 200)


if __name__ == "__main__":
    unittest.main()
