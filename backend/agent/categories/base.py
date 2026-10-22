"""Base class for category handlers. Owner: Dev A.

Each handler implements match() and decide(). The engine calls them in sequence:
1. match() finds the transaction candidate(s)
2. decide() applies the policy rule given the matched transaction and evidence
"""
from __future__ import annotations

import abc
from decimal import Decimal
from typing import Any

from backend.contracts import (
    Candidate,
    Category,
    Clues,
    Complaint,
    Decision,
    Evidence,
    MatchResult,
    to_money,
)


class CategoryHandler(abc.ABC):
    category: Category
    base_priority: str  # "P1", "P2", "P3"
    channel_family: str | None = None  # maps to tools.CHANNEL_FAMILIES

    @abc.abstractmethod
    def match(self, complaint: Complaint, clues: Clues) -> tuple[MatchResult, Evidence]:
        """Find the transaction. Don't decide outcome here."""
        ...

    @abc.abstractmethod
    def decide(self, match: MatchResult, evidence: Evidence, complaint: Complaint, clues: Clues) -> Decision:
        """Apply the policy rule. Returns Decision with outcome, refund, rule_id, calculation.
        Priority, language, route are set by the engine's router, not here."""
        ...

    @property
    def reply_guidance(self) -> str:
        """Category-specific guidance passed to the LLM drafter."""
        return ""

    # --- Shared helpers for scoring candidates ---

    @staticmethod
    def score_amount(txn_amount: float, target: Decimal | None, approximate: bool) -> float:
        if target is None or target == 0:
            return 0.0
        txn_dec = to_money(txn_amount)
        if txn_dec == target:
            return 1.0
        diff = abs(txn_dec - target) / target
        if approximate and diff <= Decimal("0.10"):
            return max(0.5, float(1 - diff))
        if diff <= Decimal("0.01"):
            return 0.8
        return 0.0

    @staticmethod
    def score_counterparty(description: str, target: str | None) -> float:
        if not target:
            return 0.0
        desc_lower = description.lower()
        target_lower = target.lower()
        if target_lower in desc_lower:
            return 1.0
        # partial token match
        target_tokens = target_lower.split()
        if any(tok in desc_lower for tok in target_tokens if len(tok) > 2):
            return 0.6
        return 0.0

    @staticmethod
    def score_date(txn_date: Any, date_range: tuple[Any, Any]) -> float:
        import datetime as dt
        if isinstance(txn_date, dt.datetime):
            txn_date = txn_date.date()
        if date_range[0] <= txn_date <= date_range[1]:
            return 1.0
        return 0.0

    @staticmethod
    def pick_best(candidates: list[Candidate]) -> MatchResult:
        """Given scored candidates, return a MatchResult."""
        if not candidates:
            return MatchResult(status="none", category="SERVICE_QUALITY")
        candidates.sort(key=lambda c: c.score, reverse=True)
        best = candidates[0]
        if len(candidates) == 1 or best.score - candidates[1].score >= 0.15:
            return MatchResult(status="confident", txn_id=best.txn_id, candidates=candidates, category="SERVICE_QUALITY")
        return MatchResult(status="ambiguous", txn_id=best.txn_id, candidates=candidates, category="SERVICE_QUALITY")
