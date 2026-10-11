"""Лимиты размера файлов: загрузка в анализ и скачивание по ссылкам (без сети)."""

from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import httpx

import support  # noqa: F401
from services import cloud
from support import auth_headers, build_test_client

PUBLIC_URL = "https://93.184.216.34/data.csv"
REAL_CLIENT = cloud._client


def patched_client(handler):
    """Подменяет транспорт, сохраняя проверку адреса и редиректов."""
    return lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs)


class CloudDownloadLimitTest(unittest.IsolatedAsyncioTestCase):
    async def download(self, handler, limit: int = 1000, **kwargs):
        with mock.patch.object(cloud, "_client", patched_client(handler)), \
                mock.patch.object(cloud, "MAX_FILE_BYTES", limit):
            return await cloud.download_file(PUBLIC_URL, "direct", **kwargs)

    async def test_small_file_is_downloaded(self) -> None:
        content, name = await self.download(lambda request: httpx.Response(200, content=b"a;b\n1;2"))
        self.assertEqual(content, b"a;b\n1;2")
        self.assertEqual(name, "data.csv")

    async def test_declared_size_over_limit_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            await self.download(lambda request: httpx.Response(200, content=b"x" * 2000))

    async def test_stream_without_content_length_is_cut_at_limit(self) -> None:
        async def body():
            yield b"x" * 600
            yield b"x" * 600

        with self.assertRaises(ValueError):
            await self.download(lambda request: httpx.Response(200, content=body()))

    async def test_zip_member_larger_than_limit_is_rejected_before_unpacking(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("big.csv", b"0" * 5000)  # сжимается до малого размера
        archive_bytes = buffer.getvalue()
        self.assertLess(len(archive_bytes), 1000)

        with mock.patch.object(
            cloud, "_client", patched_client(lambda request: httpx.Response(200, content=archive_bytes))
        ), mock.patch.object(cloud, "MAX_FILE_BYTES", 1000):
            with self.assertRaises(ValueError):
                await cloud.download_file(
                    "",
                    "dropbox",
                    {"_zip_path": "big.csv", "_folder_url": "https://www.dropbox.com/sh/abc/xyz"},
                )


class UploadLimitTest(unittest.TestCase):
    def test_oversized_upload_returns_413(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        client, _ = build_test_client(Path(tmp.name))
        analyst = auth_headers(client, "analyst")

        with mock.patch("routers.analyze.MAX_FILE_BYTES", 100):
            response = client.post(
                "/api/analyze",
                headers=analyst,
                data={"service_code": "1"},
                files={"files": ("big.md", b"x" * 200)},
            )
        self.assertEqual(response.status_code, 413)
        self.assertIn("big.md", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
