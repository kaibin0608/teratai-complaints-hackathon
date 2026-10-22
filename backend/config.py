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

# Each LLM step is "provider:model". Providers: openrouter, openai_compatible, fake (offline keywords/template).
LLM_EXTRACT = os.getenv("LLM_EXTRACT", "fake:keywords")
LLM_DRAFT = os.getenv("LLM_DRAFT", "fake:template")
LLM_EXTRACT_JSON_MODE = os.getenv("LLM_EXTRACT_JSON_MODE", "json_schema")  # json_schema | json_object | prompt
LLM_DRAFT_JSON_MODE = os.getenv("LLM_DRAFT_JSON_MODE", "prompt")
LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "8"))
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "30"))
LLM_CACHE_PATH = ROOT / os.getenv("LLM_CACHE_PATH", "backend/.cache/llm_cache.db")  # relative to repo root
USD_TO_MYR = float(os.getenv("USD_TO_MYR", "4.20"))  # provider prices are in USD; costs are reported in RM

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_COMPAT_API_KEY = os.getenv("OPENAI_COMPAT_API_KEY", "")
OPENAI_COMPAT_BASE_URL = os.getenv("OPENAI_COMPAT_BASE_URL", "")
