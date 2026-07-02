from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET", "maxima-consulting-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 часов

USERS_FILE = Path(__file__).resolve().parents[1] / "data" / "users.json"


def _load_users() -> list[dict]:
    if not USERS_FILE.exists():
        return []
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def _save_users(users: list[dict]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def get_user_by_email(email: str) -> Optional[dict]:
    for u in _load_users():
        if u["email"].lower() == email.lower():
            return u
    return None


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def list_users() -> list[dict]:
    return [{"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"]} for u in _load_users()]


def create_user(email: str, name: str, password: str, role: str) -> dict:
    users = _load_users()
    new_id = max((u["id"] for u in users), default=0) + 1
    user = {
        "id": new_id,
        "email": email,
        "name": name,
        "role": role,
        "password_hash": hash_password(password),
    }
    users.append(user)
    _save_users(users)
    return {"id": new_id, "email": email, "name": name, "role": role}


def update_user_role(user_id: int, role: str) -> bool:
    users = _load_users()
    for u in users:
        if u["id"] == user_id:
            u["role"] = role
            _save_users(users)
            return True
    return False


def delete_user(user_id: int) -> bool:
    users = _load_users()
    new_users = [u for u in users if u["id"] != user_id]
    if len(new_users) == len(users):
        return False
    _save_users(new_users)
    return True
