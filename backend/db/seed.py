"""Demo users for the bonus platform. Owner: Dev B.

Officers get RM2,000: no refund in the data is over RM5,000 (the largest is RM4,687.10), so a RM5,000 limit would
never be reached, while 128 of 466 approval refunds are over RM2,000. The fraud limit applies to the disputed
transaction (126 of 520 fraud cases are over RM5,000). The data is synthetic; all demo users share one password.
"""
from __future__ import annotations

import sqlite3

import bcrypt

DEMO_PASSWORD = "teratai123"
USERS = (  # username, full name, role, approval limit in sen (None = no limit)
    ("officer1", "Aina Rahman", "officer", 200_000),
    ("officer2", "Daniel Lim", "officer", 200_000),
    ("fraud1", "Farid Hassan", "fraud", 500_000),
    ("manager1", "Mei Ling Tan", "manager", None),
)


def seed_users(conn: sqlite3.Connection) -> int:
    """Create the demo users that are missing; never changes existing ones. Returns how many were added."""
    existing = {row[0] for row in conn.execute("SELECT username FROM users")}
    missing = [u for u in USERS if u[0] not in existing]
    if missing:
        with conn:
            conn.executemany(
                "INSERT INTO users (username, password_hash, full_name, role, approval_limit_sen) VALUES (?,?,?,?,?)",
                [(name, bcrypt.hashpw(DEMO_PASSWORD.encode(), bcrypt.gensalt(rounds=10)).decode(), full, role, limit)
                 for name, full, role, limit in missing])
    return len(missing)
