"""Bonus platform actions: POST /api/cases/{id}/<action>, with a login token. Owner: Dev B.

Handlers only parse the body and map errors to status codes; the rules live in backend/db/workflow.py.
Each returns the case detail (GET /api/cases/{id}) so the UI can redraw from one response.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from backend.api.contract import service
from backend.auth.dependencies import actor
from backend.auth.users import User
from backend.db.queries import case_detail
from backend.db.store import InvalidAction, NotFound, ReplyRefused, WrongState
from backend.db.workflow import TEAM_OF_ROLE, Forbidden, Workflow

router = APIRouter(prefix="/api/cases")


class ReasonIn(BaseModel):
    reason: str = ""


class EditIn(BaseModel):
    reply_text: str = ""
    reason: str = ""


class NoteIn(BaseModel):
    note: str = ""
    kind: str = "investigation"


class EscalateIn(BaseModel):
    reason: str = ""
    outcome: str | None = None


class OutcomeIn(BaseModel):
    outcome: str = ""
    reason: str = ""


class ReassignIn(BaseModel):
    username: str = ""
    reason: str = ""


def _do(request: Request, complaint_id: str, user: User, change: Callable[[Workflow], Any]) -> dict[str, Any]:
    store = service(request).store
    try:
        change(Workflow(store))
    except NotFound as exc:
        raise HTTPException(404, f"unknown complaint {complaint_id}") from exc
    except Forbidden as exc:
        detail = {"error": exc.error, "why": exc.why, **exc.info} if exc.why else exc.error
        raise HTTPException(403, detail) from exc
    except WrongState as exc:
        raise HTTPException(409, str(exc)) from exc
    except ReplyRefused as exc:
        raise HTTPException(422, {"error": "the reply fails the self-check; nothing was sent",
                                  "problems": exc.problems}) from exc
    except InvalidAction as exc:
        raise HTTPException(422, str(exc)) from exc
    return case_detail(store.conn, complaint_id, scope=None if user.role == "manager" else TEAM_OF_ROLE[user.role])


@router.post("/{complaint_id}/approve")
async def approve(complaint_id: str, body: ReasonIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.approve(complaint_id, user, body.reason))


@router.post("/{complaint_id}/reject")
async def reject(complaint_id: str, body: ReasonIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.reject(complaint_id, user, body.reason))


@router.post("/{complaint_id}/edit-reply")
async def edit_reply(complaint_id: str, body: EditIn, request: Request, user: User = Depends(actor)):
    """Saves the edit whether or not it passes; the detail's draft_reply carries the self-check result."""
    return _do(request, complaint_id, user, lambda wf: wf.edit_reply(complaint_id, user, body.reply_text, body.reason))


@router.post("/{complaint_id}/send-back", status_code=202)
async def send_back(complaint_id: str, body: NoteIn, request: Request, user: User = Depends(actor)):
    """The agent re-runs in the background; the case shows workflow = reprocessing until it's done."""
    svc = service(request)

    def change(wf: Workflow) -> None:
        note = wf.send_back(complaint_id, user, body.note)
        svc.reprocess(svc.store.complaint(complaint_id), note)

    return _do(request, complaint_id, user, change)


@router.post("/{complaint_id}/escalate")
async def escalate(complaint_id: str, body: EscalateIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.escalate(complaint_id, user, body.reason, body.outcome))


@router.post("/{complaint_id}/flag-sensitive")
async def flag_sensitive(complaint_id: str, body: ReasonIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.flag_sensitive(complaint_id, user, body.reason))


@router.post("/{complaint_id}/second-tier-approve")
async def second_tier_approve(complaint_id: str, body: ReasonIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.second_tier(complaint_id, user, True, body.reason))


@router.post("/{complaint_id}/second-tier-reject")
async def second_tier_reject(complaint_id: str, body: ReasonIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.second_tier(complaint_id, user, False, body.reason))


@router.post("/{complaint_id}/reassign")
async def reassign(complaint_id: str, body: ReassignIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.reassign(complaint_id, user, body.username, body.reason))


@router.post("/{complaint_id}/acknowledge")
async def acknowledge(complaint_id: str, body: ReasonIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.acknowledge(complaint_id, user, body.reason))


@router.post("/{complaint_id}/investigate")
async def investigate(complaint_id: str, body: NoteIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.investigate(complaint_id, user, body.note, body.kind))


@router.post("/{complaint_id}/record-outcome")
async def record_outcome(complaint_id: str, body: OutcomeIn, request: Request, user: User = Depends(actor)):
    return _do(request, complaint_id, user, lambda wf: wf.record_outcome(complaint_id, user, body.outcome, body.reason))
