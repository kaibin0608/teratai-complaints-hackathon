"""Code checks on a reply beyond Dev A's evidence check. Owner: Dev B.

These mirror the organisers' automatic reply checks (docs/scoring.md): not empty, right language, a refund reply
states the refund amount. They also enforce the wording rule that only an auto-resolved refund may say the money
has already moved. Run on every LLM draft and, later, on human-edited replies.
"""
from __future__ import annotations

import re

from backend.agent.self_check import AMOUNT_RE, check_reply
from backend.contracts import CheckResult, EngineResult, to_money

MAX_CHARS = 1500
DONE_CLAIMS = {  # phrases that say the money already moved
    "EN": ["has been refunded", "have refunded", "has been credited", "have credited", "was refunded", "was credited"],
    "MS": ["telah dikreditkan", "telah dikembalikan", "telah dibayar balik", "sudah dikreditkan", "sudah dikembalikan",
           "telah membayar balik"],
}
FUNCTION_WORDS = {
    "EN": {"the", "your", "we", "you", "and", "to", "of", "is", "our", "has", "will", "for"},
    "MS": {"anda", "kami", "dan", "yang", "untuk", "akan", "telah", "ini", "kepada", "dengan", "pihak", "tidak"},
}


def may_say_refunded(result: EngineResult) -> bool:
    """Money really has moved: an auto-resolved refund, or a decline because a reversal already returned it."""
    d = result.decision
    return (d.outcome == "REFUND" and d.route == "AUTO_RESOLVE") or (
        d.outcome == "DECLINE" and result.evidence.reversal is not None)


def check(reply_text: str, result: EngineResult) -> CheckResult:
    d = result.decision
    text = reply_text.strip()
    if not text:
        return CheckResult(passed=False, problems=["the reply is empty"])
    problems: list[str] = []
    if len(text) > MAX_CHARS:
        problems.append(f"the reply is {len(text)} characters; keep it under {MAX_CHARS}")

    if d.refund_amount_myr > 0:
        stated = {to_money(a) for a in AMOUNT_RE.findall(text)}
        if d.refund_amount_myr not in stated:
            problems.append(f"the reply does not state the refund amount RM{d.refund_amount_myr:,.2f}")

    if not may_say_refunded(result):
        lowered = text.lower()
        for phrase in DONE_CLAIMS["EN"] + DONE_CLAIMS["MS"]:
            if phrase in lowered:
                problems.append(f'the reply says "{phrase}" but no money has moved yet; say it will be credited '
                                f"after review, or make no refund claim")

    words = re.findall(r"[a-z]+", text.lower())
    hits = {lang: sum(w in vocab for w in words) for lang, vocab in FUNCTION_WORDS.items()}
    other = "MS" if d.reply_language == "EN" else "EN"
    if hits[d.reply_language] <= hits[other]:
        problems.append(f"the reply is not in {d.reply_language}")
    return CheckResult(passed=not problems, problems=problems)


def combined_check(reply_text: str, result: EngineResult) -> CheckResult:
    """Dev A's evidence check (IDs and amounts) plus these rules: the pipeline's self-check."""
    evidence, rules = check_reply(reply_text, result), check(reply_text, result)
    return CheckResult(passed=evidence.passed and rules.passed, problems=evidence.problems + rules.problems,
                       found_txn_ids=evidence.found_txn_ids, found_amounts=evidence.found_amounts)
