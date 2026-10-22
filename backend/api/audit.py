"""UI route: the append-only audit log across every case. Owner: Dev B."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from backend.api.contract import service
from backend.db.queries import BadQuery, audit

router = APIRouter(prefix="/api")


@router.get("/audit")
async def audit_log(request: Request, actor: str | None = None, action: str | None = None,
                    complaint_id: str | None = None, since: str | None = None, until: str | None = None,
                    people_only: bool = False, limit: int = Query(100, ge=1, le=1000),
                    offset: int = Query(0, ge=0)) -> dict[str, Any]:
    try:
        return audit(service(request).store.conn, actor=actor, action=action, complaint_id=complaint_id,
                     since=since, until=until, people_only=people_only, limit=limit, offset=offset)
    except BadQuery as exc:
        raise HTTPException(422, str(exc)) from exc
