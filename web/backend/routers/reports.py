from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from routers.auth import get_current_user

router = APIRouter()

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ReportMeta(BaseModel):
    filename: str
    size_kb: float
    modified: str
    client: str
    service: str


class SaveReportRequest(BaseModel):
    content: str
    client_name: str
    service_name: str


def _parse_meta(path: Path) -> ReportMeta:
    stat = path.stat()
    # filename: 20260621_123456_ООО_Ромашка--Диагностика.md  (new format with --)
    # legacy:   20260621_123456_ООО_Ромашка_Диагностика.md
    parts = path.stem.split("_", 2)
    remainder = parts[2] if len(parts) > 2 else path.stem
    if "--" in remainder:
        # new format: client--service
        client_raw, service_raw = remainder.split("--", 1)
        client_clean = client_raw.replace("_", " ").strip()
        service_clean = service_raw.replace("_", " ").strip()
    else:
        # legacy format: split at last underscore to separate service suffix
        service_parts = remainder.rsplit("_", 1)
        client_clean = service_parts[0].replace("_", " ").strip() if len(service_parts) > 1 else remainder.replace("_", " ").strip()
        service_clean = service_parts[1].replace("_", " ").strip() if len(service_parts) > 1 else ""
    return ReportMeta(
        filename=path.name,
        size_kb=round(stat.st_size / 1024, 1),
        modified=datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
        client=client_clean,
        service=service_clean,
    )


@router.get("", response_model=list[ReportMeta])
def list_reports(current_user: Annotated[dict, Depends(get_current_user)]) -> list[ReportMeta]:
    reports = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [_parse_meta(r) for r in reports[:50]]


@router.get("/{filename}")
def get_report(
    filename: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    # безопасность: только имя файла, без path traversal
    safe = re.sub(r"[^a-zA-Z0-9_\-\u0400-\u04FF.]", "", filename)
    path = REPORTS_DIR / safe
    if not path.exists() or path.suffix != ".md":
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    return {"filename": safe, "content": path.read_text(encoding="utf-8")}


@router.get("/{filename}/download")
def download_report(
    filename: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> FileResponse:
    safe = re.sub(r"[^a-zA-Z0-9_\-\u0400-\u04FF.]", "", filename)
    path = REPORTS_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    return FileResponse(path, media_type="text/markdown", filename=safe)


@router.post("", status_code=201)
def save_report(
    body: SaveReportRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    if current_user["role"] not in ("admin", "analyst"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_client = re.sub(r"[^\w\-]", "_", body.client_name, flags=re.UNICODE)[:30]
    safe_service = re.sub(r"[^\w\-]", "_", body.service_name, flags=re.UNICODE)[:24]
    # "--" is used as a clear separator so _parse_meta can reliably split client and service
    filename = f"{timestamp}_{safe_client}--{safe_service}.md"
    (REPORTS_DIR / filename).write_text(body.content, encoding="utf-8")
    return {"filename": filename}
