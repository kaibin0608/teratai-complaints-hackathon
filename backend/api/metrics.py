"""UI route: the dashboard numbers, including cost and latency per complaint. Owner: Dev B."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.contract import service
from backend.auth.dependencies import manager_only, viewer
from backend.auth.users import User
from backend.contracts import now_myt
from backend.db.queries import BadQuery, metrics, when

router = APIRouter(prefix="/api")


@router.get("/metrics")
async def dashboard(request: Request, as_of: str | None = None, user: User | None = Depends(viewer)) -> dict[str, Any]:
    """as_of sets the clock for the SLA view (the demo uses the live-round day, 2026-09-30). Manager only."""
    manager_only(user)
    try:
        clock = when(as_of) if as_of else now_myt().replace(microsecond=0)
    except BadQuery as exc:
        raise HTTPException(422, str(exc)) from exc
    return metrics(service(request).store.conn, clock)
