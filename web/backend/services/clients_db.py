from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "clients.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                contact    TEXT,
                cloud_url  TEXT,
                status     TEXT NOT NULL DEFAULT 'lead',
                amount     REAL,
                services   TEXT,
                notes      TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _row_to_dict(row: sqlite3.Row) -> Dict:
    d = dict(row)
    d["services"] = json.loads(d["services"]) if d.get("services") else []
    return d


def list_clients() -> List[Dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM clients ORDER BY updated_at DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_client(client_id: int) -> Optional[Dict]:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def create_client(
    name: str,
    contact: Optional[str] = None,
    cloud_url: Optional[str] = None,
    status: str = "lead",
    amount: Optional[float] = None,
    services: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> Dict:
    now = datetime.now().isoformat()
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO clients
                (name, contact, cloud_url, status, amount, services, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                contact,
                cloud_url,
                status,
                amount,
                json.dumps(services or [], ensure_ascii=False),
                notes,
                now,
                now,
            ),
        )
        client_id = cur.lastrowid
    return get_client(client_id)  # type: ignore[return-value]


def update_client(client_id: int, **fields) -> Optional[Dict]:
    if not fields:
        return get_client(client_id)
    fields["updated_at"] = datetime.now().isoformat()
    if "services" in fields:
        fields["services"] = json.dumps(fields["services"] or [], ensure_ascii=False)
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [client_id]
    with _conn() as con:
        con.execute(f"UPDATE clients SET {cols} WHERE id = ?", vals)
    return get_client(client_id)


def delete_client(client_id: int) -> bool:
    with _conn() as con:
        affected = con.execute(
            "DELETE FROM clients WHERE id = ?", (client_id,)
        ).rowcount
    return affected > 0
