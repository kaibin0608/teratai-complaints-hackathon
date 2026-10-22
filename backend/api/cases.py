"""UI routes: the case queues and one case's full decision trail. Owner: Dev B.

Read-only and open for now (docs/UI_API.md); the bonus login adds role checks to these same routes later.
The UI's buttons use the contract routes (POST /cases/{id}/actions, /acknowledge).
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from backend.api.contract import service
from backend.db.queries import BadQuery, case_detail, list_cases

router = APIRouter(prefix="/api")


@router.get("/cases")
async def cases(request: Request, queue: str | None = None, route: str | None = None, category: str | None = None,
                priority: str | None = None, hold_reason: str | None = None, q: str | None = None,
                sort: Literal["priority", "recent"] = "priority", limit: int = Query(50, ge=1, le=500),
                offset: int = Query(0, ge=0)) -> dict[str, Any]:
    try:
        return list_cases(service(request).store.conn, queue=queue, route=route, category=category,
                          priority=priority, hold_reason=hold_reason, q=q, sort=sort, limit=limit, offset=offset)
    except BadQuery as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/cases/{complaint_id}")
async def case(complaint_id: str, request: Request) -> dict[str, Any]:
    detail = case_detail(service(request).store.conn, complaint_id)
    if detail is None:
        raise HTTPException(404, f"unknown complaint {complaint_id}")
    return detail
