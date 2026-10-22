"""The facts a reply may use, built in code from the decision and evidence. Shared by the LLM prompt and the
code-written fallback, so both say the same things in the same formats. Owner: Dev B.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from backend.contracts import EngineResult, to_money

Purpose = Literal["refunded", "will_credit", "decline", "investigate", "info"]

TOPIC = {
    "EN": {"DUPLICATE_CHARGE": "a card payment charged twice", "FAILED_TRANSFER": "a transfer that did not go through",
           "ATM_NOT_DISPENSED": "an ATM withdrawal", "UNAUTHORISED_CARD": "a card transaction you did not make",
           "SCAM_TRANSFER": "a transfer you were tricked into making", "FEE_DISPUTE": "a fee on your account",
           "SERVICE_QUALITY": "your recent experience with us"},
    "MS": {"DUPLICATE_CHARGE": "bayaran kad yang dicaj dua kali", "FAILED_TRANSFER": "pemindahan wang yang tidak berjaya",
           "ATM_NOT_DISPENSED": "pengeluaran wang di ATM", "UNAUTHORISED_CARD": "transaksi kad yang tidak anda lakukan",
           "SCAM_TRANSFER": "pemindahan wang akibat penipuan", "FEE_DISPUTE": "caj pada akaun anda",
           "SERVICE_QUALITY": "pengalaman anda bersama kami"},
}
SAFETY_ADVICE = {  # the only advice a reply may give (decided with Dev B)
    "SCAM_TRANSFER": {
        "EN": ["Please never share your OTP, PIN or online banking password with anyone, including callers who say "
               "they are from the bank or the police.",
               "The bank will never ask you to move your money to a 'safe account'."],
        "MS": ["Sila jangan sekali-kali berkongsi OTP, PIN atau kata laluan perbankan dalam talian anda dengan sesiapa, "
               "termasuk pemanggil yang mengaku dari pihak bank atau polis.",
               "Pihak bank tidak akan meminta anda memindahkan wang ke 'akaun selamat'."],
    },
    "UNAUTHORISED_CARD": {
        "EN": ["Please never share your OTP or PIN with anyone.",
               "You can block your card at any time in the Teratai app or by calling our hotline."],
        "MS": ["Sila jangan berkongsi OTP atau PIN anda dengan sesiapa.",
               "Anda boleh menyekat kad anda pada bila-bila masa melalui aplikasi Teratai atau dengan menghubungi talian "
               "khidmat pelanggan kami."],
    },
}


def money(amount: Decimal) -> str:
    """RM1,234.56: Dev A's self-check regex strips the comma."""
    return f"RM{to_money(amount):,.2f}"


def dmy(value: str) -> str:
    """'2026-07-17 07:20:56' or '2026-07-17' → '17-07-2026'."""
    y, m, d = value[:10].split("-")
    return f"{d}-{m}-{y}"


def _fee_reason(inputs: dict[str, str]) -> str:
    waiver = inputs.get("waiver", "").lower()
    if "60+" in waiver:
        return "customers aged 60 and above are exempt from the debit card annual fee, so this fee is being refunded"
    if "year" in waiver or "anniversary" in waiver:
        return "the credit card annual fee is waived for the first year of the card, so this fee is being refunded"
    if "basic" in waiver:
        return "Basic Savings accounts have no monthly service charge, so this fee is being refunded"
    due = to_money(inputs.get("amount_due", "0"))
    if due > 0:
        return f"the correct fee for your account is {money(due)}, so the amount charged above it is being refunded"
    return "this fee should not have been charged to your account, so it is being refunded"


def reason(result: EngineResult) -> str | None:
    """Why the outcome is what it is, in words a customer may read. Never the internal calculation text
    (it holds authentication methods, timestamps and rule details)."""
    d = result.decision
    inputs = d.calculation.inputs
    rule = d.rule_id
    if rule == "FEE.OVERCHARGE_REFUND":
        return _fee_reason(inputs)
    if rule == "FEE.CORRECT_CHARGE":
        return "the fee charged matches our published fee schedule for your account, and no waiver applies"
    if rule == "ATM.SHORTFALL_REFUND":
        dispensed = to_money(inputs.get("dispensed", "0"))
        got = "no cash was dispensed" if dispensed == 0 else f"only {money(dispensed)} was dispensed"
        return (f"the ATM records show {got} of the {money(to_money(inputs['requested']))} you requested, "
                f"so the difference is being refunded")
    if rule == "ATM.FULLY_DISPENSED":
        return "the ATM records show the full amount was dispensed"
    if rule == "FAILED.FAILED_NO_REVERSAL":
        return "the transfer failed and the amount was not returned to your account, so it is being refunded"
    if rule == "FAILED.ALREADY_REVERSED":
        when = inputs.get("reversal_time")
        return "the amount was already returned to your account" + (f" on {dmy(when)}" if when else "")
    if rule == "FAILED.COMPLETED":
        return "our records show the transfer was completed and the money reached the recipient's bank"
    if rule == "DUP.VALID_PAIR_REFUND":
        return "the same amount was charged twice at the same merchant within minutes, so the second charge is being refunded"
    if rule == "DUP.NO_PAIR":
        return "our records show separate purchases, not the same payment charged twice"
    if rule == "DUP.ALREADY_REVERSED":
        return "the duplicate charge has already been reversed to your account"
    if rule == "UNAUTH.NO_AUTH_REFUND":
        return "after reviewing the transaction, we are refunding it"
    if rule.startswith("UNAUTH."):
        return "the transaction needs further investigation by our fraud team before any decision"
    if rule.startswith("SCAM."):
        return "our fraud team will investigate and try to recall the transfer from the receiving bank"
    return None


def purpose(result: EngineResult) -> Purpose:
    d = result.decision
    if d.outcome == "REFUND":
        return "refunded" if d.route == "AUTO_RESOLVE" else "will_credit"
    return {"DECLINE": "decline", "INVESTIGATE": "investigate"}.get(d.outcome, "info")


@dataclass
class ReplyFacts:
    language: str
    category: str
    purpose: Purpose
    name: str | None
    refund: str | None                  # "RM550.00", only when refunding
    transaction: str | None             # "TXN-0088211 on 17-07-2026 (RM1,500.00)"
    transaction_ms: str | None          # same, Malay connective
    reason: str | None                  # customer-safe, from code (never the internal calculation)
    next_update: str | None             # "29-07-2026" for fraud and pending cases
    advice: list[str] = field(default_factory=list)
    allowed_ids: list[str] = field(default_factory=list)
    allowed_amounts: list[str] = field(default_factory=list)


def build_facts(result: EngineResult) -> ReplyFacts:
    d, e = result.decision, result.evidence
    txn = e.matched_txn
    if txn:
        ref = (txn["txn_id"], dmy(txn["txn_time"]), money(to_money(txn["amount_myr"])))
        transaction, transaction_ms = f"{ref[0]} on {ref[1]} ({ref[2]})", f"{ref[0]} pada {ref[1]} ({ref[2]})"
    else:
        transaction = transaction_ms = None
    p = purpose(result)
    pending = p == "investigate" or d.route == "HUMAN_APPROVAL"
    return ReplyFacts(
        language=d.reply_language,
        category=d.category,
        purpose=p,
        name=(e.customer or {}).get("full_name") or None,
        refund=money(d.refund_amount_myr) if d.refund_amount_myr > 0 else None,
        transaction=transaction,
        transaction_ms=transaction_ms,
        reason=reason(result),
        next_update=dmy(f"{d.resolve_due_at:%Y-%m-%d}") if pending and d.resolve_due_at else None,
        advice=SAFETY_ADVICE.get(d.category, {}).get(d.reply_language, []),
        allowed_ids=list(dict.fromkeys(e.allowed_txn_ids)),
        allowed_amounts=list(dict.fromkeys(money(a) for a in e.allowed_amounts)),
    )
