"""Stand-ins so Dev A and Dev B can work without waiting on each other.

- fake_extract: keyword extractor (from starter/baseline.py) for Dev A until the LLM extractor lands
- stub_engine:  safe fixed decision for Dev B until the category handlers land
- stub_draft / stub_check: template reply and a minimal ID/amount check

Delete each stub once its real implementation is merged.
"""
from __future__ import annotations

import re

from backend.agent.tools import get_db
from backend.contracts import (
    CheckResult,
    Clues,
    Complaint,
    Decision,
    EngineResult,
    Evidence,
    LLMUsage,
    MatchResult,
    to_money,
)
from starter.data import age_on

KEYWORDS = [  # checked in order, copied from starter/baseline.py
    ("SCAM_TRANSFER", ["scam", "tipu", "police", "polis", "safe account", "akaun selamat", "parcel", "bungkusan", "invest", "part-time", "part time", "kerja sambilan", "emergency", "kecemasan"]),
    ("ATM_NOT_DISPENSED", ["atm"]),
    ("DUPLICATE_CHARGE", ["twice", "two times", "dua kali", "2 kali", "double"]),
    ("UNAUTHORISED_CARD", ["did not make", "not authorise", "didn't make", "bukan saya", "tidak membuat", "tak buat", "disputes a card"]),
    ("FEE_DISPUTE", ["fee", "charge", "caj", "yuran"]),
    ("FAILED_TRANSFER", ["transfer", "pindah", "duitnow", "ibg"]),
]
MALAY = {"saya", "dan", "tetapi", "tidak", "kepada", "pada", "akaun", "wang", "dengan", "untuk", "sila", "mohon", "kenapa", "telah", "sebanyak", "lepas", "semalam"}
ENGLISH = {"the", "my", "i", "was", "and", "but", "please", "with", "from", "have", "money"}
APPROX = ["about", "around", "approx", "roughly", "lebih kurang", "kira-kira", "sekitar"]
AMOUNT_RE = re.compile(r"RM\s?([\d,]+(?:\.\d{1,2})?)")
TXN_RE = re.compile(r"TXN-\d{7}")

BASE_PRIORITY = {"SCAM_TRANSFER": "P1", "UNAUTHORISED_CARD": "P1", "DUPLICATE_CHARGE": "P2", "FAILED_TRANSFER": "P2",
                 "ATM_NOT_DISPENSED": "P2", "FEE_DISPUTE": "P3", "SERVICE_QUALITY": "P3"}
BUMP = {"P3": "P2", "P2": "P1", "P1": "P1"}


def fake_extract(complaint: Complaint) -> tuple[Clues, LLMUsage]:
    text = f"{complaint.subject} {complaint.text}".lower()
    category = next((cat for cat, words in KEYWORDS if any(w in text for w in words)), "SERVICE_QUALITY")
    words = set(re.findall(r"[a-z']+", complaint.text.lower()))
    malay, english = len(words & MALAY), len(words & ENGLISH)
    amount = AMOUNT_RE.search(complaint.text)
    return Clues(
        category=category,
        language="MS" if malay >= 2 else "EN",
        is_mixed_language=malay >= 2 and english >= 2,
        is_staff_note=complaint.is_staff_note,
        amount_mentioned=to_money(amount.group(1)) if amount else None,
        amount_approximate=any(w in text for w in APPROX),
    ), LLMUsage(provider="fake", model="keywords")


def stub_engine(complaint: Complaint, clues: Clues) -> EngineResult:
    """No matching: SERVICE_QUALITY → INFO_ONLY, fraud categories → INVESTIGATE, everything else → DECLINE + hold."""
    db = get_db()
    customer = db.customers[complaint.customer_id]
    vulnerable = age_on(customer["date_of_birth"], complaint.received_at.date()) >= 65
    priority = BASE_PRIORITY[clues.category]
    if vulnerable:
        priority = BUMP[priority]
    use_preferred = clues.is_mixed_language or clues.is_staff_note
    language = customer["preferred_language"] if use_preferred else clues.language

    if clues.category == "SERVICE_QUALITY":
        outcome, route, hold, status = "INFO_ONLY", "AUTO_RESOLVE", None, "not_applicable"
    elif clues.category in ("SCAM_TRANSFER", "UNAUTHORISED_CARD"):
        outcome, route, hold, status = "INVESTIGATE", "FRAUD_TEAM", "no_match", "none"
    else:
        outcome, route, hold, status = "DECLINE", "HUMAN_APPROVAL", "no_match", "none"

    return EngineResult(
        match=MatchResult(status=status, category=clues.category),
        decision=Decision(
            category=clues.category,
            outcome=outcome,
            priority=priority,
            reply_language=language,
            route=route,
            rule_id="STUB",
            hold_reason=hold,
            vulnerable=vulnerable,
        ),
        evidence=Evidence(customer=customer, accounts=db.accounts_by_customer[complaint.customer_id]),
    )


def stub_draft(result: EngineResult, feedback: list[str] | None = None) -> tuple[str, LLMUsage]:
    if result.decision.reply_language == "MS":
        text = "Terima kasih kerana menghubungi Teratai Bank. Kami sedang menyemak aduan anda dan akan menghubungi anda semula."
    else:
        text = "Thank you for contacting Teratai Bank. We are reviewing your complaint and will get back to you."
    return text, LLMUsage(provider="stub", model="template")


def stub_check(reply_text: str, result: EngineResult) -> CheckResult:
    ids = TXN_RE.findall(reply_text)
    amounts = [to_money(a) for a in AMOUNT_RE.findall(reply_text)]
    allowed_ids, allowed_amounts = set(result.evidence.allowed_txn_ids), set(result.evidence.allowed_amounts)
    problems = [f"transaction {t} is not in the evidence" for t in ids if t not in allowed_ids]
    problems += [f"amount RM{a} is not in the evidence" for a in amounts if a not in allowed_amounts]
    return CheckResult(passed=not problems, problems=problems, found_txn_ids=ids, found_amounts=amounts)
