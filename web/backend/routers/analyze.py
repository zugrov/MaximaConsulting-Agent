from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.auth import get_current_user
from services.ai import SERVICES, get_services, stream_analysis
from services.parser import parse_file

router = APIRouter()

ALLOWED_ROLES = {"admin", "analyst"}


class ServicesResponse(BaseModel):
    services: list[dict]


@router.get("/services", response_model=ServicesResponse)
def list_services(_: Annotated[dict, Depends(get_current_user)]) -> ServicesResponse:
    return ServicesResponse(services=get_services())


@router.post("/analyze")
async def analyze(
    files: Annotated[list[UploadFile], File()],
    service_code: Annotated[str, Form()],
    client_name: Annotated[str, Form()] = "Клиент",
    context: Annotated[str, Form()] = "",
    current_user: Annotated[dict, Depends(get_current_user)] = None,
) -> StreamingResponse:
    if current_user["role"] not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Недостаточно прав для запуска анализа")

    if service_code not in SERVICES:
        raise HTTPException(status_code=422, detail=f"Неизвестный код услуги: {service_code}")

    if not files:
        raise HTTPException(status_code=422, detail="Не передан ни один файл")

    skill_name, service_name = SERVICES[service_code]

    parts: list[str] = []
    for f in files:
        content = await f.read()
        if not content:
            continue
        parsed = parse_file(content, f.filename or "file")
        parts.append(f"=== {parsed['source_file']} ===\n{parsed['raw']}")

    if not parts:
        raise HTTPException(status_code=422, detail="Все переданные файлы пусты")

    combined_raw = "\n\n".join(parts)
    source_label = ", ".join(f.filename or "file" for f in files)

    return StreamingResponse(
        stream_analysis(
            raw_content=combined_raw,
            source_file=source_label,
            truncated=False,
            skill_name=skill_name,
            service_name=service_name,
            context=context,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Client-Name": quote(client_name, safe=""),
            "X-Service-Name": quote(service_name, safe=""),
        },
    )
