from __future__ import annotations

from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.auth import get_current_user
from routers.reports import REPORTS_DIR, _parse_meta
from services.clients_db import (
    create_client,
    delete_client,
    get_client,
    list_clients,
    update_client,
)

router = APIRouter()

WRITE_ROLES = {"admin", "analyst"}


class ClientCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    cloud_url: Optional[str] = None
    status: str = "lead"
    amount: Optional[float] = None
    services: List[str] = []
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    cloud_url: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    services: Optional[List[str]] = None
    notes: Optional[str] = None


@router.get("")
def list_all(current_user: Annotated[dict, Depends(get_current_user)]) -> list[dict]:
    return list_clients()


@router.post("", status_code=201)
def create(
    body: ClientCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    if current_user["role"] not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    if body.status not in ("lead", "project", "closed"):
        raise HTTPException(status_code=422, detail="Статус должен быть lead/project/closed")
    return create_client(**body.model_dump())


@router.get("/{client_id}")
def get_one(
    client_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client


@router.patch("/{client_id}")
def update(
    client_id: int,
    body: ClientUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    if current_user["role"] not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    if not get_client(client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    if body.status and body.status not in ("lead", "project", "closed"):
        raise HTTPException(status_code=422, detail="Статус должен быть lead/project/closed")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    return update_client(client_id, **fields)


@router.delete("/{client_id}", status_code=204)
def remove(
    client_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> None:
    if current_user["role"] not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    if not delete_client(client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")


@router.get("/{client_id}/reports")
def client_reports(
    client_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> list[dict]:
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    client_name_lower = client["name"].lower()
    all_reports = sorted(
        REPORTS_DIR.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    result = []
    for path in all_reports:
        meta = _parse_meta(path)
        if client_name_lower in meta.client.lower():
            result.append(meta.model_dump())
    return result
