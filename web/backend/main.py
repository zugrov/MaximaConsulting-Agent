from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
# Корень проекта нужен для общего пакета utils (имена файлов отчётов)
sys.path.insert(0, str(ROOT_DIR))

# .env лежит в корне consulting-agent/ — загружать ДО импорта routers/services,
# иначе os.getenv в ai.py прочитает пустые значения при import-time.
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, analyze, reports
from routers.clients import router as clients_router
from routers.cloud import router as cloud_router
from services.clients_db import init_db

app = FastAPI(title="maxima consulting AI Agent", version="1.0.0")

_default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
_origins_raw = os.getenv("ALLOWED_ORIGINS", _default_origins)
allow_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация БД клиентов при старте
@app.on_event("startup")
def startup() -> None:
    init_db()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(clients_router, prefix="/api/clients", tags=["clients"])
app.include_router(cloud_router, prefix="/api/cloud", tags=["cloud"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
