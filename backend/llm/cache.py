"""SQLite cache of validated LLM responses, keyed on the request hash. Survives restarts; never stores failures."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.contracts import now_myt
from backend.llm.types import LLMRaw

SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_cache (
    key           TEXT PRIMARY KEY,
    provider      TEXT NOT NULL,
    model         TEXT NOT NULL,
    response_text TEXT NOT NULL,
    tokens_in     INTEGER NOT NULL,
    tokens_out    INTEGER NOT NULL,
    cost_usd      REAL,
    created_at    TEXT NOT NULL
)
"""


class LLMCache:
    def __init__(self, path: Path | str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute(SCHEMA)
        self._db.commit()

    def get(self, key: str) -> LLMRaw | None:
        row = self._db.execute(
            "SELECT response_text, tokens_in, tokens_out, cost_usd FROM llm_cache WHERE key = ?", (key,)
        ).fetchone()
        return LLMRaw(text=row[0], tokens_in=row[1], tokens_out=row[2], cost_usd=row[3]) if row else None

    def put(self, key: str, provider: str, model: str, raw: LLMRaw) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO llm_cache VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (key, provider, model, raw.text, raw.tokens_in, raw.tokens_out, raw.cost_usd, now_myt().isoformat()),
        )
        self._db.commit()

    def __len__(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
