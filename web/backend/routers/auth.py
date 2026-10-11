from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import AfterValidator, BaseModel, Field, field_validator

from services.auth import (
    MAX_PASSWORD_BYTES,
    create_access_token,
    create_user,
    decode_token,
    delete_user,
    get_user_by_email,
    list_users,
    set_user_password,
    update_user_role,
    verify_password,
)
from services.login_limiter import LoginLimiter

router = APIRouter()
login_limiter = LoginLimiter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def _check_password_bytes(value: str) -> str:
    if len(value.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Пароль слишком длинный: не более {MAX_PASSWORD_BYTES} байт")
    return value


NewPassword = Annotated[
    str, Field(min_length=MIN_PASSWORD_LENGTH), AfterValidator(_check_password_bytes)
]


class UserCreate(BaseModel):
    email: str
    name: str = Field(min_length=1)
    password: NewPassword
    role: str = "analyst"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip()
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Некорректный email")
        return value


class RoleUpdate(BaseModel):
    role: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: NewPassword


class PasswordReset(BaseModel):
    new_password: NewPassword


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    user = get_user_by_email(payload.get("email", ""))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    if payload.get("pwd", 0) != user.get("password_version", 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия завершена, войдите снова",
        )
    return user


def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права admin")
    return current_user


def _client_ip(request: Request) -> str:
    # nginx дописывает реальный адрес в конец X-Forwarded-For; левые элементы подделываются клиентом
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=Token)
def login(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    ip = _client_ip(request)
    wait = login_limiter.retry_after(ip, form_data.username)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Слишком много неудачных попыток входа. Повторите через {wait // 60 + 1} мин.",
            headers={"Retry-After": str(wait)},
        )

    user = get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        login_limiter.register_failure(ip, form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    login_limiter.reset_account(ip, form_data.username)
    token = create_access_token({
        "email": user["email"],
        "role": user["role"],
        "pwd": user.get("password_version", 0),
    })
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[dict, Depends(get_current_user)]) -> UserOut:
    return UserOut(**{k: current_user[k] for k in ("id", "email", "name", "role")})


@router.post("/me/password", status_code=204)
def change_own_password(
    body: PasswordChange,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> None:
    if not verify_password(body.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=422, detail="Новый пароль совпадает с текущим")
    set_user_password(current_user["id"], body.new_password)


@router.put("/users/{user_id}/password", status_code=204)
def reset_user_password(
    user_id: int,
    body: PasswordReset,
    _: Annotated[dict, Depends(require_admin)],
) -> None:
    if not set_user_password(user_id, body.new_password):
        raise HTTPException(status_code=404, detail="Пользователь не найден")


@router.get("/users", response_model=list[UserOut])
def get_users(_: Annotated[dict, Depends(require_admin)]) -> list[UserOut]:
    return [UserOut(**u) for u in list_users()]


@router.post("/users", response_model=UserOut, status_code=201)
def add_user(
    body: UserCreate,
    _: Annotated[dict, Depends(require_admin)],
) -> UserOut:
    if get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=422, detail="Роль должна быть admin/analyst/viewer")
    user = create_user(body.email, body.name, body.password, body.role)
    return UserOut(**user)


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(
    user_id: int,
    body: RoleUpdate,
    _: Annotated[dict, Depends(require_admin)],
) -> UserOut:
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=422, detail="Роль должна быть admin/analyst/viewer")
    if not update_user_role(user_id, body.role):
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    users = list_users()
    user = next(u for u in users if u["id"] == user_id)
    return UserOut(**user)


@router.delete("/users/{user_id}", status_code=204)
def remove_user(
    user_id: int,
    current_user: Annotated[dict, Depends(require_admin)],
) -> None:
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="Пользователь не найден")
