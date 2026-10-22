"""The organisers' API (docs/api.md), plus a fraud acknowledge endpoint. Owner: Dev B.

Handlers only validate input and map store exceptions to status codes; all state rules live in CaseStore.
Background work runs in the server's event loop (AgentService), bounded by LLM_MAX_CONCURRENCY.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, field_validator

from backend.agent.pipeline import run_pipeline
from backend.agent.reply_rules import combined_check
from backend.contracts import AgentRun, Complaint, parse_myt
from backend.db.store import CaseConflict, CaseStore, InvalidAction, NotFound, ReplyRefused, WrongState

log = logging.getLogger(__name__)
router = APIRouter()
REQUIRED = ("complaint_id", "customer_id", "received_at", "text")


class ComplaintIn(BaseModel):
    """The six fields of a complaints.csv row. Extra fields are ignored."""

    model_config = ConfigDict(extra="ignore")
    complaint_id: str
    customer_id: str
    received_at: str
    channel: str = ""
    subject: str = ""
    text: str

    @field_validator("*", mode="before")
    @classmethod
    def _strip(cls, v: Any) -> Any:
        return v.strip() if isinstance(v, str) else ("" if v is None else v)

    @field_validator(*REQUIRED)
    @classmethod
    def _required(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("received_at")
    @classmethod
    def _datetime(cls, v: str) -> str:
        parse_myt(v)  # ValueError → 422
        return v


class ActionIn(BaseModel):
    action: str = ""
    actor: str = ""
    reason: str = ""
    reply_text: str | None = None


class AcknowledgeIn(BaseModel):
    actor: str = ""
    reason: str = ""


Pipeline = Callable[[Complaint], Awaitable[AgentRun]]


class AgentService:
    """Runs complaints through the pipeline in the background and stores every run."""

    def __init__(self, store: CaseStore, concurrency: int, pipeline: Pipeline = run_pipeline):
        self.store = store
        self.pipeline = pipeline
        self.gate = asyncio.Semaphore(concurrency)
        self.tasks: set[asyncio.Task] = set()

    def submit(self, complaint: Complaint) -> None:
        task = asyncio.create_task(self._work(complaint))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def _work(self, complaint: Complaint) -> None:
        async with self.gate:
            began = time.perf_counter()
            try:
                run = await self.pipeline(complaint)
            except Exception as exc:  # never leave a case stuck in processing
                log.exception("pipeline crashed on %s", complaint.complaint_id)
                run = AgentRun(run_id=uuid.uuid4().hex, complaint_id=complaint.complaint_id,
                               error=f"pipeline crashed: {type(exc).__name__}: {exc}")
            latency_ms = max(1, int((time.perf_counter() - began) * 1000))
        try:
            self.store.save_run(complaint, run, latency_ms)
        except Exception:
            log.exception("could not store the run for %s", complaint.complaint_id)

    async def idle(self) -> None:
        """Wait for all background work (tests, shutdown)."""
        while self.tasks:
            await asyncio.gather(*list(self.tasks), return_exceptions=True)


def service(request: Request) -> AgentService:
    return request.app.state.service


@router.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@router.post("/complaints", status_code=202)
async def new_complaint(body: ComplaintIn, request: Request, response: Response) -> dict[str, str]:
    svc = service(request)
    complaint = Complaint(**body.model_dump())
    try:
        case, created = svc.store.register(complaint)
    except CaseConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    if created:
        svc.submit(complaint)
    else:
        response.status_code = 200  # the same complaint again: no second case, no change
    return {"complaint_id": complaint.complaint_id, "status": case["status"]}


@router.get("/cases/{complaint_id}")
async def get_case(complaint_id: str, request: Request) -> dict[str, Any]:
    view = service(request).store.case_view(complaint_id)
    if view is None:
        raise HTTPException(404, f"unknown complaint {complaint_id}")
    return view


def _apply(request: Request, complaint_id: str, change: Callable[[CaseStore], Any]) -> dict[str, Any]:
    store = service(request).store
    try:
        change(store)
    except NotFound as exc:
        raise HTTPException(404, f"unknown complaint {complaint_id}") from exc
    except WrongState as exc:
        raise HTTPException(409, str(exc)) from exc
    except ReplyRefused as exc:
        raise HTTPException(422, {"error": "edited reply fails the self-check; nothing was sent",
                                  "problems": exc.problems}) from exc
    except InvalidAction as exc:
        raise HTTPException(422, str(exc)) from exc
    return store.case_view(complaint_id)


@router.post("/cases/{complaint_id}/actions")
async def act(complaint_id: str, body: ActionIn, request: Request) -> dict[str, Any]:
    return _apply(request, complaint_id, lambda store: store.act(
        complaint_id, body.action, body.actor, body.reason, body.reply_text, check=combined_check))


@router.post("/cases/{complaint_id}/acknowledge")
async def acknowledge(complaint_id: str, body: AcknowledgeIn, request: Request) -> dict[str, Any]:
    """Not in docs/api.md: a fraud analyst releases the agent's holding reply."""
    return _apply(request, complaint_id, lambda store: store.acknowledge(complaint_id, body.actor, body.reason))
