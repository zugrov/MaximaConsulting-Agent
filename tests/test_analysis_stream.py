"""Потоковый анализ: ответы и ошибки llm-router (сам роутер подменяется, сеть не используется)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

import support  # noqa: F401
from services import ai
from support import auth_headers, build_test_client


def router_response(status: int, **kwargs) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("POST", "http://router/v1/complete"), **kwargs)


def decode_report(body: str) -> str:
    """Собирает текст отчёта так же, как клиент: JSON-фрагменты, служебные строки пропускаются."""
    parts = []
    for line in body.splitlines():
        if line.startswith('data: "'):
            parts.append(json.loads(line[len("data: "):]))
    return "".join(parts)


async def collect(router_result=None, router_error=None, secret="test-secret") -> str:
    async def fake_request(system_prompt: str, user_message: str) -> httpx.Response:
        if router_error:
            raise router_error
        return router_result

    with mock.patch.object(ai, "LLM_ROUTER_INTERNAL_SECRET", secret), \
            mock.patch.object(ai, "_request_llm_router", fake_request):
        events = [
            event
            async for event in ai.stream_analysis(
                raw_content="данные",
                source_file="a.csv",
                truncated=False,
                skill_name="diagnostic",
                service_name="Финансовая диагностика",
            )
        ]
    return "".join(events)


class StreamAnalysisTest(unittest.IsolatedAsyncioTestCase):
    async def test_success_streams_content_and_done(self) -> None:
        body = await collect(router_response(200, json={"content": "# Отчёт\nМаржа 20%"}))
        self.assertIn("[STARTED]", body)
        self.assertTrue(body.rstrip().endswith("data: [DONE]"))
        self.assertEqual(decode_report(body), "# Отчёт\nМаржа 20%")

    async def test_backslashes_and_long_text_survive_the_stream(self) -> None:
        text = ("Путь C:\\new\\table и \\n в тексте.\n" + "строка " * 300 + "\n") * 3
        body = await collect(router_response(200, json={"content": text}))
        self.assertEqual(decode_report(body), text.strip())  # сервер обрезает края ответа

    async def test_model_unavailable_gives_readable_error(self) -> None:
        response = router_response(503, json={"detail": {"error_code": "MODEL_UNAVAILABLE"}})
        self.assertIn("[ОШИБКА: llm-router — модели временно недоступны", await collect(response))

    async def test_string_detail_does_not_break_stream(self) -> None:
        response = router_response(401, json={"detail": "Unauthorized"})
        body = await collect(response)
        self.assertIn("[ОШИБКА:", body)
        self.assertIn("HTTP_401", body)

    async def test_non_json_error_and_non_json_success_are_reported(self) -> None:
        self.assertIn("[ОШИБКА:", await collect(router_response(502, text="Bad Gateway")))
        self.assertIn("[ОШИБКА:", await collect(router_response(200, text="<html>")))

    async def test_empty_content_is_reported(self) -> None:
        self.assertIn("пустой ответ", await collect(router_response(200, json={"content": " "})))

    async def test_unreachable_router_is_reported(self) -> None:
        body = await collect(router_error=httpx.ConnectError("refused"))
        self.assertIn("[ОШИБКА: llm-router недоступен", body)

    async def test_missing_secret_is_reported(self) -> None:
        self.assertIn("LLM_ROUTER_INTERNAL_SECRET", await collect(secret=""))


class AnalyzeEndpointTest(unittest.TestCase):
    def test_analyze_streams_report_through_api(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        client, _ = build_test_client(Path(tmp.name))

        async def fake_request(system_prompt: str, user_message: str) -> httpx.Response:
            self.assertIn("Источник: a.csv", user_message)
            self.assertIn("выручка;100", user_message)
            return router_response(200, json={"content": "Готовый отчёт"})

        with mock.patch.object(ai, "LLM_ROUTER_INTERNAL_SECRET", "test-secret"), \
                mock.patch.object(ai, "_request_llm_router", fake_request):
            response = client.post(
                "/api/analyze",
                headers=auth_headers(client, "analyst"),
                data={"service_code": "1", "client_name": "ООО Тест"},
                files={"files": ("a.csv", "показатель;значение\nвыручка;100\n".encode())},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Готовый отчёт", response.text)
        self.assertIn("[DONE]", response.text)


if __name__ == "__main__":
    unittest.main()
