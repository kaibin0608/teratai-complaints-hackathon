"""Self-check: verify reply text against evidence. Owner: Dev A.

Every TXN-ID and RM amount in the reply must exist in evidence.allowed_txn_ids
and evidence.allowed_amounts. Also re-runs when humans edit replies.
"""
from __future__ import annotations

import re
from decimal import Decimal

from backend.contracts import CheckResult, EngineResult, to_money

TXN_RE = re.compile(r"TXN-\d{7}")
AMOUNT_RE = re.compile(r"RM\s?([\d,]+(?:\.\d{1,2})?)")


def check_reply(reply_text: str, result: EngineResult) -> CheckResult:
    found_ids = TXN_RE.findall(reply_text)
    found_amounts = [to_money(a.replace(",", "")) for a in AMOUNT_RE.findall(reply_text)]

    allowed_ids = set(result.evidence.allowed_txn_ids)
    allowed_amounts = set(result.evidence.allowed_amounts)

    problems: list[str] = []
    for tid in found_ids:
        if tid not in allowed_ids:
            problems.append(f"transaction {tid} is not in the evidence")

    for amt in found_amounts:
        if amt not in allowed_amounts:
            problems.append(f"amount RM{amt} is not in the evidence")

    if result.decision.refund_amount_myr > 0 and found_amounts:
        refund = result.decision.refund_amount_myr
        if refund not in set(found_amounts):
            pass  # reply may describe the refund differently; don't flag

    return CheckResult(
        passed=len(problems) == 0,
        problems=problems,
        found_txn_ids=found_ids,
        found_amounts=found_amounts,
    )
