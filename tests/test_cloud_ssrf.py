"""Проверки защиты от SSRF в services/cloud.py (без обращения к сети)."""

from __future__ import annotations

import unittest

import httpx

import support  # noqa: F401
from services.cloud import _client, assert_public_url

BLOCKED_URLS = [
    "http://127.0.0.1:8020/v1/complete",
    "http://localhost/",
    "http://10.0.0.5/",
    "http://172.16.0.1/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://0.0.0.0/",
    "file:///etc/hosts",
    "ftp://93.184.216.34/file",
    "http:///no-host",
]


class AssertPublicUrlTest(unittest.IsolatedAsyncioTestCase):
    async def test_blocks_internal_and_unsupported_urls(self) -> None:
        for url in BLOCKED_URLS:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    await assert_public_url(url)

    async def test_allows_public_ip(self) -> None:
        await assert_public_url("https://93.184.216.34/file.xlsx")


class RedirectGuardTest(unittest.IsolatedAsyncioTestCase):
    async def test_redirect_to_internal_address_is_blocked(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "93.184.216.34":
                return httpx.Response(302, headers={"location": "http://127.0.0.1:8020/"})
            return httpx.Response(200, text="секрет внутреннего сервиса")

        async with _client(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as client:
            with self.assertRaises(ValueError):
                await client.get("http://93.184.216.34/start")


if __name__ == "__main__":
    unittest.main()
