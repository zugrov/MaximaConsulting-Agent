from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, analyze, reports
from routers.clients import router as clients_router
from routers.cloud import router as cloud_router
from services.clients_db import init_db

# .env лежит в корне consulting-agent/
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="maxima consulting AI Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ],
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
