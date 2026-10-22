"""FastAPI app: the organisers' API over the agent. Owner: Dev B.

Run:  uvicorn backend.main:app --host 0.0.0.0 --port 8000
Test: python scoring/api_check.py http://localhost:8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from backend import config
from backend.agent.tools import get_db
from backend.api.contract import AgentService, Pipeline, router
from backend.db.store import CaseStore
from backend.llm.registry import check_config


def create_app(db_path: Path | str | None = None, pipeline: Pipeline | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        check_config()  # unknown provider or missing key: refuse to start
        store = CaseStore(db_path or config.API_DB_PATH)
        get_db()  # load the CSVs once, before the first complaint
        svc = AgentService(store, config.LLM_MAX_CONCURRENCY, **({"pipeline": pipeline} if pipeline else {}))
        app.state.service = svc
        for complaint_id in store.processing_ids():  # left mid-run by a crash or restart
            svc.submit(store.complaint(complaint_id))
        yield
        for task in list(svc.tasks):  # their cases stay processing and are re-queued at the next start
            task.cancel()

    app = FastAPI(title="Teratai complaints agent", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
