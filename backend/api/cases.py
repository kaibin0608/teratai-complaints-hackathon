"""UI routes: the case queues and one case's full decision trail. Owner: Dev B.

With a login token the lists and detail are filtered to the viewer's team (backend/db/workflow.py TEAM_OF_ROLE);
without one, while AUTH_REQUIRED is off, they show everything (docs/UI_API.md).
The UI's buttons use backend/api/actions.py (with a login) or the contract routes (POST /cases/{id}/actions).
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.api.contract import service
from backend.auth.dependencies import viewer
from backend.auth.users import User
from backend.db.queries import BadQuery, case_detail, list_cases
from backend.db.workflow import TEAM_OF_ROLE

router = APIRouter(prefix="/api")


def scope_of(user: User | None) -> str | None:
    """The team a viewer may see; None = everything (the manager, or no token in open mode)."""
    return None if user is None or user.role == "manager" else TEAM_OF_ROLE[user.role]


@router.get("/cases")
async def cases(request: Request, queue: str | None = None, route: str | None = None, category: str | None = None,
                priority: str | None = None, hold_reason: str | None = None, workflow: str | None = None,
                sensitive: bool | None = None, assigned_to: str | None = None, overridden: bool | None = None,
                q: str | None = None, sort: Literal["priority", "recent"] = "priority",
                limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                user: User | None = Depends(viewer)) -> dict[str, Any]:
    try:
        return list_cases(service(request).store.conn, queue=queue, route=route, category=category,
                          priority=priority, hold_reason=hold_reason, workflow=workflow, sensitive=sensitive,
                          assigned_to=assigned_to, overridden=overridden, q=q, sort=sort, limit=limit, offset=offset,
                          scope=scope_of(user), me=user and user.username)
    except BadQuery as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/cases/{complaint_id}")
async def case(complaint_id: str, request: Request, user: User | None = Depends(viewer)) -> dict[str, Any]:
    detail = case_detail(service(request).store.conn, complaint_id, scope=scope_of(user))
    if detail is None:  # unknown, or another team's case: don't reveal which
        raise HTTPException(404, f"unknown complaint {complaint_id}")
    return detail
