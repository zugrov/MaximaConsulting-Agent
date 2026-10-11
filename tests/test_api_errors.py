"""Ошибки API: некорректные файлы, права на облачные эндпоинты, SSRF через HTTP."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401
from support import auth_headers, build_test_client


class ApiErrorsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client, _ = build_test_client(Path(self.tmp.name))
        self.analyst = auth_headers(self.client, "analyst")
        self.viewer = auth_headers(self.client, "viewer")

    def analyze(self, filename: str, content: bytes):
        return self.client.post(
            "/api/analyze",
            headers=self.analyst,
            data={"service_code": "1"},
            files={"files": (filename, content)},
        )

    def test_corrupted_files_return_422_with_file_name(self) -> None:
        for filename, content in (("bad.xlsx", b"not excel"), ("bad.json", b"{oops")):
            with self.subTest(filename=filename):
                response = self.analyze(filename, content)
                self.assertEqual(response.status_code, 422)
                self.assertIn(filename, response.json()["detail"])

    def test_empty_file_and_unknown_service_are_rejected(self) -> None:
        self.assertEqual(self.analyze("empty.md", b"").status_code, 422)
        response = self.client.post(
            "/api/analyze",
            headers=self.analyst,
            data={"service_code": "99"},
            files={"files": ("a.md", b"x")},
        )
        self.assertEqual(response.status_code, 422)

    def test_viewer_cannot_use_cloud_endpoints(self) -> None:
        resolve = self.client.post(
            "/api/cloud/resolve", headers=self.viewer, json={"url": "https://93.184.216.34/a.csv"}
        )
        download = self.client.post(
            "/api/cloud/download",
            headers=self.viewer,
            json={"files": [{"name": "a", "url": "https://93.184.216.34/a.csv", "provider": "direct"}]},
        )
        self.assertEqual(resolve.status_code, 403)
        self.assertEqual(download.status_code, 403)

    def test_analyst_cannot_download_internal_or_non_http_urls(self) -> None:
        urls = (
            "http://127.0.0.1:8020/v1/complete",
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:1/?x=dropbox.com",
            "file:///etc/hosts",
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.post(
                    "/api/cloud/download",
                    headers=self.analyst,
                    json={"files": [{"name": "x", "url": url, "provider": "direct"}]},
                )
                self.assertEqual(response.status_code, 400, response.text)


if __name__ == "__main__":
    unittest.main()
