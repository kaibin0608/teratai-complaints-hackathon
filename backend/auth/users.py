"""Platform users (seeded by backend/db/seed.py). Owner: Dev B."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

import bcrypt

# Checked when the username is unknown, so a wrong username takes as long as a wrong password.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-password", bcrypt.gensalt(rounds=10))


@dataclass(frozen=True)
class User:
    username: str
    full_name: str
    role: str  # officer | fraud | manager
    approval_limit_sen: int | None  # None = no limit

    @property
    def limit_myr(self) -> Decimal | None:
        return None if self.approval_limit_sen is None else Decimal(self.approval_limit_sen) / 100

    def public(self) -> dict[str, str | None]:
        return {"username": self.username, "full_name": self.full_name, "role": self.role,
                "approval_limit_myr": None if self.limit_myr is None else f"{self.limit_myr:.2f}"}


def get_user(conn: sqlite3.Connection, username: str) -> User | None:
    row = conn.execute("SELECT username, full_name, role, approval_limit_sen FROM users WHERE username = ?",
                       (username,)).fetchone()
    return User(*row) if row else None


def all_users(conn: sqlite3.Connection) -> list[User]:
    rows = conn.execute("SELECT username, full_name, role, approval_limit_sen FROM users ORDER BY role, username")
    return [User(*r) for r in rows]


def check_password(conn: sqlite3.Connection, username: str, password: str) -> User | None:
    row = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    ok = bcrypt.checkpw(password.encode(), row[0].encode() if row else _DUMMY_HASH)
    return get_user(conn, username) if row and ok else None
