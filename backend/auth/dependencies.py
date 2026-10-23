"""Who is calling an /api route. Owner: Dev B.

viewer: read routes. No token and AUTH_REQUIRED off → None, meaning the manager's view (the UI before its login page).
actor: write actions. Always needs a valid token: the person acting comes from it.
The user is loaded from the database on every request, so a role change applies at once.
Both are async on purpose: FastAPI runs plain-function dependencies in a thread pool, and the store has one SQLite
connection that must only be used from the event loop (several requests at once collided and gave false 401s).
Never used on the organisers' contract routes.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from backend import config
from backend.auth.tokens import BadToken, read_token
from backend.auth.users import User, get_user


def _unauthorised(detail: str) -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if not header:
        return None
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorised("use 'Authorization: Bearer <token>'")
    return token.strip()


def _user(request: Request, token: str) -> User:
    try:
        username = read_token(token)
    except BadToken as exc:
        raise _unauthorised("login expired or invalid; log in again") from exc
    user = get_user(request.app.state.service.store.conn, username)
    if user is None:
        raise _unauthorised("unknown user; log in again")
    return user


async def viewer(request: Request) -> User | None:
    token = _bearer(request)
    if token is None:
        if config.AUTH_REQUIRED:
            raise _unauthorised("login required")
        return None
    return _user(request, token)


async def actor(request: Request) -> User:
    token = _bearer(request)
    if token is None:
        raise _unauthorised("login required")
    return _user(request, token)


def manager_only(user: User | None) -> None:
    """For metrics, audit and users: a signed-in officer or analyst gets 403; no token (open mode) is the manager."""
    if user is not None and user.role != "manager":
        raise HTTPException(403, "manager only")
