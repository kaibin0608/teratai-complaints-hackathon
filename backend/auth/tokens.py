"""Login tokens: HS256 JWTs signed with config.JWT_SECRET. Owner: Dev B."""
from __future__ import annotations

import datetime as dt

from jose import JWTError, jwt

from backend import config

TOKEN_HOURS = 12
ALGORITHM = "HS256"


class BadToken(Exception):
    """Missing, expired, tampered or otherwise unusable token."""


def make_token(username: str, role: str, *, now: dt.datetime | None = None) -> str:
    issued = now or dt.datetime.now(dt.timezone.utc)
    claims = {"sub": username, "role": role, "iat": issued, "exp": issued + dt.timedelta(hours=TOKEN_HOURS)}
    return jwt.encode(claims, config.JWT_SECRET, algorithm=ALGORITHM)


def read_token(token: str) -> str:
    """The username in a valid token; raises BadToken otherwise (expired included)."""
    try:
        claims = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise BadToken(str(exc)) from exc
    if not isinstance(claims.get("sub"), str):
        raise BadToken("token has no user")
    return claims["sub"]
