"""Login routes: /api/auth/login, /api/auth/me, /api/users. Owner: Dev B."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.api.contract import service
from backend.auth.dependencies import actor, manager_only, viewer
from backend.auth.tokens import make_token
from backend.auth.users import User, all_users, check_password

router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    username: str = ""
    password: str = ""


@router.post("/auth/login")
async def login(body: LoginIn, request: Request) -> dict[str, Any]:
    user = check_password(service(request).store.conn, body.username.strip(), body.password)
    if user is None:
        raise HTTPException(401, "wrong username or password")
    return {"token": make_token(user.username, user.role), "user": user.public()}


@router.get("/auth/me")
async def me(user: User = Depends(actor)) -> dict[str, Any]:
    return user.public()


@router.get("/users")
async def users(request: Request, user: User | None = Depends(viewer)) -> list[dict[str, Any]]:
    manager_only(user)
    return [u.public() for u in all_users(service(request).store.conn)]
