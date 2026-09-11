"""HTTP-клиент к сервису llm-router."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

LLM_ROUTER_URL = os.getenv("LLM_ROUTER_URL", "http://127.0.0.1:8020").rstrip("/")
LLM_ROUTER_INTERNAL_SECRET = os.getenv("LLM_ROUTER_INTERNAL_SECRET", "")
LLM_ROUTER_PROJECT = os.getenv("LLM_ROUTER_PROJECT", "maxima-consulting")
LLM_ROUTER_TASK_TYPE = os.getenv("LLM_ROUTER_TASK_TYPE", "client_report")

_ROUTER_TIMEOUT = httpx.Timeout(connect=10, read=600, write=10, pool=10)

_ERROR_MESSAGES = {
    "UNAUTHORIZED": "Неверный или отсутствующий LLM_ROUTER_INTERNAL_SECRET",
    "PROJECT_NOT_ALLOWED": f"Проект {LLM_ROUTER_PROJECT!r} не разрешён в llm-router",
    "INVALID_REQUEST": "Некорректный запрос к llm-router",
    "MODEL_UNAVAILABLE": "Все модели llm-router недоступны, попробуйте позже",
    "STREAM_INTERRUPTED": "Поток ответа llm-router прерван до завершения",
    "DB_UNAVAILABLE": "llm-router недоступен (ошибка БД)",
}


@dataclass
class LlmRouterResult:
    content: str
    model_requested: str
    model_actual: str


class LlmRouterError(Exception):
    def __init__(self, message: str, error_code: str | None = None):
        self.error_code = error_code
        super().__init__(message)


def _extract_error_code(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    detail = payload.get("detail")
    if isinstance(detail, dict):
        code = detail.get("error_code")
        return str(code) if code else None
    code = payload.get("error_code")
    return str(code) if code else None


def _raise_for_error_code(error_code: str | None, fallback: str) -> None:
    message = _ERROR_MESSAGES.get(error_code or "", fallback)
    raise LlmRouterError(message, error_code)


def call_llm_router(system: str, prompt: str, max_tokens: int) -> LlmRouterResult:
    """Отправляет запрос в llm-router и возвращает готовый ответ."""
    if not LLM_ROUTER_INTERNAL_SECRET:
        raise LlmRouterError(
            "LLM_ROUTER_INTERNAL_SECRET не задан в окружении",
            "UNAUTHORIZED",
        )

    url = f"{LLM_ROUTER_URL}/v1/complete"
    headers = {"X-Internal-Secret": LLM_ROUTER_INTERNAL_SECRET}
    payload = {
        "project": LLM_ROUTER_PROJECT,
        "task_type": LLM_ROUTER_TASK_TYPE,
        "system": system,
        "prompt": prompt,
        "max_tokens": max_tokens,
    }

    with httpx.Client(timeout=_ROUTER_TIMEOUT) as client:
        response = client.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        try:
            error_payload = response.json()
        except json.JSONDecodeError:
            error_payload = {}
        error_code = _extract_error_code(error_payload)
        _raise_for_error_code(
            error_code,
            f"llm-router вернул HTTP {response.status_code}",
        )

    try:
        data = response.json()
    except json.JSONDecodeError as err:
        raise LlmRouterError(
            "llm-router вернул некорректный JSON-ответ",
            "STREAM_INTERRUPTED",
        ) from err

    content = (data.get("content") or "").strip()
    if not content:
        raise LlmRouterError(
            "llm-router вернул пустой ответ",
            "STREAM_INTERRUPTED",
        )

    return LlmRouterResult(
        content=content,
        model_requested=data.get("model_requested", ""),
        model_actual=data.get("model_actual", ""),
    )
