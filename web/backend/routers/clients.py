from __future__ import annotations

from pathlib import Path
from typing import Annotated, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from routers.auth import get_current_user
from routers.reports import REPORTS_DIR, _parse_meta
from services.clients_db import (
    create_client,
    delete_client,
    get_client,
    list_clients,
    update_client,
)
from utils.report_files import client_key

router = APIRouter()

WRITE_ROLES = {"admin", "analyst"}
SERVICE_CODES = {str(code) for code in range(1, 9)}


def _validate_name(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Название не может быть пустым")
    return value


def _validate_services(value: Optional[List[str]]) -> Optional[List[str]]:
    if value is None:
        return None
    unknown = [code for code in value if code not in SERVICE_CODES]
    if unknown:
        raise ValueError(f"Неизвестные коды услуг: {', '.join(unknown)}")
    return list(dict.fromkeys(value))


def _validate_cloud_url(value: Optional[str]) -> Optional[str]:
    if value and urlparse(value).scheme not in ("http", "https"):
        raise ValueError("Ссылка на облако должна начинаться с http:// или https://")
    return value


class ClientCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    cloud_url: Optional[str] = None
    status: str = "lead"
    amount: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    services: List[str] = []
    notes: Optional[str] = None

    _check_name = field_validator("name")(_validate_name)
    _check_services = field_validator("services")(_validate_services)
    _check_cloud_url = field_validator("cloud_url")(_validate_cloud_url)


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    cloud_url: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    services: Optional[List[str]] = None
    notes: Optional[str] = None

    _check_name = field_validator("name")(_validate_name)
    _check_services = field_validator("services")(_validate_services)
    _check_cloud_url = field_validator("cloud_url")(_validate_cloud_url)


# Поля, которые нельзя обнулить через PATCH (NOT NULL в схеме или обязательные значения)
REQUIRED_UPDATE_FIELDS = {"name", "status", "services"}


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
    # exclude_unset: явный null очищает поле (например, сумму), а не переданные поля не меняются
    fields = {
        key: value
        for key, value in body.model_dump(exclude_unset=True).items()
        if value is not None or key not in REQUIRED_UPDATE_FIELDS
    }
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

    key = client_key(client["name"])
    if not key:
        return []

    all_reports = sorted(
        REPORTS_DIR.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    result = []
    for path in all_reports:
        meta = _parse_meta(path)
        # точное совпадение, а не подстрока: «ООО Ром» не должен видеть отчёты «ООО Ромашка»
        if client_key(meta.client) == key:
            result.append(meta.model_dump())
    return result
