"""FastAPI app: the organisers' API over the agent. Owner: Dev B.

Run:  uvicorn backend.main:app --host 0.0.0.0 --port 8000
Test: python scoring/api_check.py http://localhost:8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.agent.tools import get_db
from backend.api import actions, audit, cases, metrics
from backend.api.contract import AgentService, Pipeline, router
from backend.auth import router as auth
from backend.db.seed import seed_users
from backend.db.store import CaseStore
from backend.llm.registry import check_config

log = logging.getLogger(__name__)


def create_app(db_path: Path | str | None = None, pipeline: Pipeline | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        check_config()  # unknown provider or missing key: refuse to start
        store = CaseStore(db_path or config.API_DB_PATH)
        seed_users(store.conn)
        store.reset_reprocessing()  # a send back cut off by a restart goes back to its queue
        if config.JWT_SECRET == "dev-only-not-secret":
            log.warning("JWT_SECRET is not set: login tokens use a development key")
        get_db()  # load the CSVs once, before the first complaint
        svc = AgentService(store, config.LLM_MAX_CONCURRENCY, **({"pipeline": pipeline} if pipeline else {}))
        app.state.service = svc
        for complaint_id in store.processing_ids():  # left mid-run by a crash or restart
            svc.submit(store.complaint(complaint_id))
        yield
        for task in list(svc.tasks):  # their cases stay processing and are re-queued at the next start
            task.cancel()

    app = FastAPI(title="Teratai complaints agent", lifespan=lifespan)
    # The React UI runs on another origin (localhost:5173 or a teammate's laptop). No cookies, so "*" is safe.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(router)
    for ui in (auth, cases, actions, metrics, audit):
        app.include_router(ui.router)
    return app


app = create_app()
