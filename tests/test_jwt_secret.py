"""Выбор JWT-секрета: небезопасные значения не должны попадать в работу."""

from __future__ import annotations

import os
import unittest
from unittest import mock

import support  # noqa: F401
from services import auth

INSECURE_VALUES = [None, "", "change-me-in-production", "maxima-consulting-secret-change-in-prod"]


def load_secret(value):
    env = {} if value is None else {"JWT_SECRET": value}
    with mock.patch.dict(os.environ, env, clear=True):
        return auth.load_jwt_secret()


class JwtSecretTest(unittest.TestCase):
    def test_configured_secret_is_used_as_is(self) -> None:
        self.assertEqual(load_secret("x" * 40), "x" * 40)

    def test_insecure_secrets_are_replaced_with_random_and_logged(self) -> None:
        for value in INSECURE_VALUES:
            with self.assertLogs("services.auth", level="WARNING"):
                secret = load_secret(value)
            self.assertNotIn(secret, auth.INSECURE_JWT_SECRETS)
            self.assertEqual(len(secret), 64)

    def test_random_secrets_differ_between_calls(self) -> None:
        with self.assertLogs("services.auth", level="WARNING"):
            self.assertNotEqual(load_secret(None), load_secret(None))


if __name__ == "__main__":
    unittest.main()
