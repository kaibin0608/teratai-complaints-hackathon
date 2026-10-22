"""Shared contracts between the decision engine (Dev A) and the platform (Dev B).

Change this file only in a dedicated PR approved by both developers; never inside a feature branch.

Conventions:
- Money is Decimal rounded to the sen; costs are in RM.
- Every datetime is naive Malaysia time (MYT, UTC+8), matching the CSVs. Use now_myt(), never datetime.now().
- Input dates are accepted as YYYY-MM-DD or DD-MM-YYYY (also DD/MM/YYYY); display uses DD-MM-YYYY HH:MM:SS (fmt_myt).
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
HoldReason = Literal[
    "customer_not_found", "ambiguous_match", "no_match", "category_revised", "self_check_failed",
    "unknown_auth_method", "llm_error",
]
RunKind = Literal["autonomous", "reprocess"]
FeeType = Literal["Monthly service charge", "Debit card annual fee", "Credit card annual fee"]  # fee_schedule.csv fee_name

SEN = Decimal("0.01")
MYT = dt.timezone(dt.timedelta(hours=8), "MYT")
DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S",
]
DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]


def to_money(value: Any) -> Decimal:
    """Parse a CSV/float/str amount into Decimal rounded to the sen."""
    return Decimal(str(value).replace(",", "")).quantize(SEN, rounding=ROUND_HALF_UP)


def now_myt() -> dt.datetime:
    """Current Malaysia time as a naive datetime, whatever the machine's timezone."""
    return dt.datetime.now(MYT).replace(tzinfo=None)


def parse_myt(value: str) -> dt.datetime:
    """Parse a MYT datetime given as YYYY-MM-DD or DD-MM-YYYY (or DD/MM/YYYY), with or without seconds."""
    value = value.strip().replace("T", " ")
    for fmt in DATETIME_FORMATS:
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised datetime {value!r}; use DD-MM-YYYY HH:MM or YYYY-MM-DD HH:MM")


def parse_date(value: str) -> dt.date:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {value!r}; use DD-MM-YYYY or YYYY-MM-DD")


def fmt_myt(value: dt.datetime | dt.date) -> str:
    """Display format for UI and replies: DD-MM-YYYY (HH:MM:SS for datetimes)."""
    return value.strftime("%d-%m-%Y %H:%M:%S" if isinstance(value, dt.datetime) else "%d-%m-%Y")


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
        return parse_myt(v) if isinstance(v, str) else v

    @property
    def is_staff_note(self) -> bool:
        return self.channel == "Call centre note"


class Clues(BaseModel):
    """Structured output of the LLM extraction step. Raw clues only; code resolves dates and matches.

    language is the main language of the text; Dev A's router picks the reply language
    (preferred_language when is_mixed_language or the complaint is a call-centre note).
    """

    model_config = ConfigDict(extra="forbid")  # bad LLM output fails validation

    category: Category
    language: Language
    is_mixed_language: bool = False
    amount_mentioned: Decimal | None = None  # the disputed / requested amount
    other_amounts: list[Decimal] = Field(default_factory=list)  # e.g. ATM "got only RM950"
    amount_approximate: bool = False
    counterparty_name: str | None = None  # merchant or transfer recipient, as written
    counterparty_bank: str | None = None
    atm_location: str | None = None
    date_phrase: str | None = None  # raw, e.g. "hari Selasa lepas"; code resolves it
    date_exact: dt.date | None = None  # only when the text names a calendar date
    card_last4: str | None = Field(default=None, pattern=r"^\d{4}$")
    fee_type: FeeType | None = None
    fee_month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")  # "YYYY-MM" when explicit, else None

    @field_validator("date_exact", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> Any:
        return parse_date(v) if isinstance(v, str) else v


class Candidate(BaseModel):
    txn_id: str
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    status: MatchStatus
    txn_id: str | None = None  # best candidate, also set when ambiguous (exported, but the case is held)
    candidates: list[Candidate] = Field(default_factory=list)
    category: Category  # final category; may differ from Clues.category after fallback
    category_revised: bool = False


class Evidence(BaseModel):
    """Snapshot of what the decision used. Rows are the raw CSV dicts.

    allowed_txn_ids / allowed_amounts are strict: only the matched transaction, its duplicate pair or reversal,
    ATM journal amounts, the computed refund, the fee due and the RM500 approval limit. The self-check
    accepts nothing else in a reply.
    """

    customer: dict[str, Any] | None = None  # None when customer_id is unknown (hold: customer_not_found)
    accounts: list[dict[str, Any]] = Field(default_factory=list)
    matched_txn: dict[str, Any] | None = None
    related_txns: list[dict[str, Any]] = Field(default_factory=list)  # e.g. the earlier charge of a duplicate
    reversal: dict[str, Any] | None = None
    atm_journal: dict[str, Any] | None = None
    fee_schedule_row: dict[str, Any] | None = None
    allowed_txn_ids: list[str] = Field(default_factory=list)
    allowed_amounts: list[Decimal] = Field(default_factory=list)


class Calculation(BaseModel):
    explanation: str = ""  # e.g. "1500.00 requested − 950.00 dispensed = 550.00"; shown in UI and chatbot
    inputs: dict[str, str] = Field(default_factory=dict)  # e.g. {"requested": "1500.00", "dispensed": "950.00"}


class Decision(BaseModel):
    """The agent's decision. Field names match the predictions.csv columns."""

    category: Category
    matched_txn_id: str | None = None
    outcome: Outcome
    refund_amount_myr: Decimal = Decimal("0.00")
    priority: Priority
    reply_language: Language
    route: Route  # final route, including any hold; this is exported
    policy_route: Route | None = None  # route from the policy before any hold; defaults to route
    rule_id: str  # "CATEGORY.RULE", e.g. "ATM.SHORTFALL_REFUND"; Dev A publishes the list
    calculation: Calculation = Field(default_factory=Calculation)
    hold_reason: HoldReason | None = None
    vulnerable: bool = False  # 65+ on received_at
    ack_due_at: dt.datetime | None = None  # sla_policy.csv, MYT
    resolve_due_at: dt.datetime | None = None

    @field_validator("refund_amount_myr", mode="before")
    @classmethod
    def _money(cls, v: Any) -> Decimal:
        return to_money(v)

    @model_validator(mode="after")
    def _default_policy_route(self) -> Decision:
        if self.policy_route is None:
            self.policy_route = self.route
        return self


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
    cost_myr: Decimal = Decimal("0")  # converted from provider USD pricing with config.USD_TO_MYR
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
    created_at: dt.datetime = Field(default_factory=now_myt)

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


class Extractor(Protocol):  # Dev B (LLM), async for parallel batch runs
    async def __call__(self, complaint: Complaint) -> tuple[Clues, LLMUsage]: ...


class Engine(Protocol):  # Dev A (code)
    """Never raises for business cases (no match, unknown auth method, ...): returns a Decision with hold_reason.
    Unknown customer_id: no transaction lookup, category from clues, hold customer_not_found
    (FRAUD_TEAM if INVESTIGATE, else HUMAN_APPROVAL). Intake accepts it; nothing is dropped.
    Raises only on bugs; the pipeline catches them and marks the run failed."""

    def __call__(self, complaint: Complaint, clues: Clues) -> EngineResult: ...


class Drafter(Protocol):  # Dev B (LLM), async; language is decision.reply_language
    async def __call__(self, result: EngineResult, feedback: list[str] | None = None) -> tuple[str, LLMUsage]: ...


class Checker(Protocol):  # Dev A (code)
    """Also used on human-edited replies: Dev B passes a copy of EngineResult carrying the human's decision."""

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
