"""Settings from environment variables (.env locally, never committed)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

DATA_DIR = ROOT / "data"
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "backend" / "teratai.db"))
INBOX_DIR = Path(os.getenv("INBOX_DIR", ROOT / "inbox"))
TEAM_NAME = os.getenv("TEAM_NAME", "teratai-team")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "fake")
LLM_EXTRACT_MODEL = os.getenv("LLM_EXTRACT_MODEL", "")
LLM_DRAFT_MODEL = os.getenv("LLM_DRAFT_MODEL", "")
LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "8"))
USD_TO_MYR = float(os.getenv("USD_TO_MYR", "4.20"))  # provider prices are in USD; costs are reported in RM
