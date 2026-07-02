from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from services.auth import (
    create_access_token,
    create_user,
    decode_token,
    delete_user,
    get_user_by_email,
    list_users,
    update_user_role,
    verify_password,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str


class UserCreate(BaseModel):
    email: str
    name: str
    password: str = Field(min_length=6)
    role: str = "analyst"


class RoleUpdate(BaseModel):
    role: str


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    user = get_user_by_email(payload.get("email", ""))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user


def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права admin")
    return current_user


@router.post("/login", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    token = create_access_token({"email": user["email"], "role": user["role"]})
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[dict, Depends(get_current_user)]) -> UserOut:
    return UserOut(**{k: current_user[k] for k in ("id", "email", "name", "role")})


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
