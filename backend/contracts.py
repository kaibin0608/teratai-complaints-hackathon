"""Shared contracts between the decision engine (Dev A) and the platform (Dev B).

Change this file only in a dedicated PR approved by both developers.
Money is Decimal, rounded to the sen. Timestamps are naive Malaysia time (UTC+8), as in the CSVs.
"""
from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator

Category = Literal[
    "DUPLICATE_CHARGE",
    "FAILED_TRANSFER",
    "ATM_NOT_DISPENSED",
    "UNAUTHORISED_CARD",
    "SCAM_TRANSFER",
    "FEE_DISPUTE",
    "SERVICE_QUALITY",
]
Outcome = Literal["REFUND", "DECLINE", "INVESTIGATE", "INFO_ONLY"]
Priority = Literal["P1", "P2", "P3"]
Language = Literal["EN", "MS"]
Route = Literal["AUTO_RESOLVE", "HUMAN_APPROVAL", "FRAUD_TEAM"]
MatchStatus = Literal["confident", "ambiguous", "none", "not_applicable"]
HoldReason = Literal["ambiguous_match", "no_match", "self_check_failed", "unknown_auth_method", "llm_error"]
RunKind = Literal["autonomous", "reprocess"]

SEN = Decimal("0.01")


def to_money(value: Any) -> Decimal:
    """Parse a CSV/float/str amount into Decimal rounded to the sen."""
    return Decimal(str(value).replace(",", "")).quantize(SEN, rounding=ROUND_HALF_UP)


class Complaint(BaseModel):
    """One row of complaints.csv, or one live-round complaint."""

    complaint_id: str
    customer_id: str
    received_at: dt.datetime
    channel: str
    subject: str = ""
    text: str

    @field_validator("received_at", mode="before")
    @classmethod
    def _parse_received(cls, v: Any) -> Any:
        if isinstance(v, str):
            return dt.datetime.strptime(v.strip(), "%Y-%m-%d %H:%M")
        return v

    @property
    def is_staff_note(self) -> bool:
        return self.channel == "Call centre note"


class Clues(BaseModel):
    """Structured output of the LLM extraction step. Raw text clues only; code resolves them."""

    category: Category
    language: Language
    is_mixed_language: bool = False
    is_staff_note: bool = False
    amount_mentioned: Decimal | None = None
    amount_approximate: bool = False
    merchant_name: str | None = None
    recipient_name: str | None = None
    counterparty_bank: str | None = None
    date_phrase: str | None = None
    card_last4: str | None = None
    fee_type: str | None = None
    fee_month: str | None = None


class Candidate(BaseModel):
    txn_id: str
    score: float
    reasons: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    status: MatchStatus
    txn_id: str | None = None  # best candidate, also set when ambiguous (exported, but the case is held)
    candidates: list[Candidate] = Field(default_factory=list)
    category: Category  # final category; may differ from Clues.category after fallback
    category_revised: bool = False


class Evidence(BaseModel):
    """Snapshot of what the decision used. Rows are the raw CSV dicts."""

    customer: dict[str, Any]
    accounts: list[dict[str, Any]] = Field(default_factory=list)
    matched_txn: dict[str, Any] | None = None
    related_txns: list[dict[str, Any]] = Field(default_factory=list)
    reversal: dict[str, Any] | None = None
    atm_journal: dict[str, Any] | None = None
    fee_schedule_row: dict[str, Any] | None = None
    allowed_txn_ids: list[str] = Field(default_factory=list)  # what the self-check accepts in a reply
    allowed_amounts: list[Decimal] = Field(default_factory=list)


class Decision(BaseModel):
    """The agent's decision. Field names match the predictions.csv columns."""

    category: Category
    matched_txn_id: str | None = None
    outcome: Outcome
    refund_amount_myr: Decimal = Decimal("0.00")
    priority: Priority
    reply_language: Language
    route: Route
    rule_id: str  # e.g. "ATM.SHORTFALL_REFUND"
    calculation: dict[str, Any] = Field(default_factory=dict)  # e.g. {"requested": "1500.00", "dispensed": "950.00"}
    hold_reason: HoldReason | None = None
    vulnerable: bool = False  # 65+ on received_at

    @field_validator("refund_amount_myr", mode="before")
    @classmethod
    def _money(cls, v: Any) -> Decimal:
        return to_money(v)


class EngineResult(BaseModel):
    """What match_and_decide returns."""

    match: MatchResult
    decision: Decision
    evidence: Evidence


class CheckResult(BaseModel):
    passed: bool
    problems: list[str] = Field(default_factory=list)
    found_txn_ids: list[str] = Field(default_factory=list)
    found_amounts: list[Decimal] = Field(default_factory=list)


class LLMUsage(BaseModel):
    provider: str = "none"
    model: str = "none"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0")
    latency_ms: int = 0
    retries: int = 0
    cached: bool = False


class AgentRun(BaseModel):
    """One immutable pipeline run. The autonomous run is what predictions.csv exports."""

    run_id: str
    complaint_id: str
    run_kind: RunKind = "autonomous"
    clues: Clues | None = None
    match: MatchResult | None = None
    decision: Decision | None = None
    evidence: Evidence | None = None
    reply_text: str = ""
    self_check: CheckResult | None = None
    redraft_count: int = 0
    error: str | None = None
    extract_usage: LLMUsage = Field(default_factory=LLMUsage)
    draft_usage: list[LLMUsage] = Field(default_factory=list)
    prompt_version: str = "v0"
    schema_version: str = "v0"
    policy_version: str = "v0"
    created_at: dt.datetime = Field(default_factory=dt.datetime.now)

    def prediction_row(self) -> dict[str, str]:
        """Row for submissions/<team>/predictions.csv."""
        d = self.decision
        if d is None:
            raise ValueError(f"{self.complaint_id}: run has no decision ({self.error})")
        return {
            "complaint_id": self.complaint_id,
            "category": d.category,
            "matched_txn_id": d.matched_txn_id or "",
            "outcome": d.outcome,
            "refund_amount_myr": f"{d.refund_amount_myr:.2f}",
            "priority": d.priority,
            "reply_language": d.reply_language,
            "route": d.route,
            "reply_text": self.reply_text,
        }


# --- The seams. Each side implements its own, codes against the other's. ---


class Extractor(Protocol):  # Dev B (LLM)
    def __call__(self, complaint: Complaint) -> tuple[Clues, LLMUsage]: ...


class Engine(Protocol):  # Dev A (code)
    def __call__(self, complaint: Complaint, clues: Clues) -> EngineResult: ...


class Drafter(Protocol):  # Dev B (LLM); language is decision.reply_language
    def __call__(self, result: EngineResult, feedback: list[str] | None = None) -> tuple[str, LLMUsage]: ...


class Checker(Protocol):  # Dev A (code); also used on human-edited replies
    def __call__(self, reply_text: str, result: EngineResult) -> CheckResult: ...


PREDICTION_COLUMNS = [
    "complaint_id",
    "category",
    "matched_txn_id",
    "outcome",
    "refund_amount_myr",
    "priority",
    "reply_language",
    "route",
    "reply_text",
]
