"""Second-issue check: code verification, fail-safe behaviour, the hold, and old runs (offline, stubbed LLM)."""
import asyncio
import csv
from pathlib import Path

import pytest

from backend import config
from backend.agent import issues as issues_mod
from backend.agent.engine import match_and_decide
from backend.agent.issues import detect_issues, other_issues
from backend.agent.pipeline import run_pipeline
from backend.agent.reply_facts import also_raised
from backend.agent.reply_rules import combined_check
from backend.agent.stubs import fake_extract
from backend.agent.tools import load_complaint
from backend.contracts import AgentRun, Complaint, EngineResult, LLMUsage, OtherIssue
from backend.db.queries import case_detail, list_cases
from backend.db.store import CaseStore, run_cost
from backend.llm.prompts import build_draft_messages, load_fewshot_issues

EVAL = Path(__file__).resolve().parents[1] / "eval" / "issues" / "complaints.csv"
TEXT = "Transfer RM46.54 gagal tapi duit dah tolak. Pastu ada caj fee pulak."


def complaint(text=TEXT, subject=""):
    return Complaint(complaint_id="T-1", customer_id="CUS-1", received_at="2026-09-30 10:00", channel="App chat",
                     subject=subject, text=text)


def issue(category, quote):
    return OtherIssue(category=category, quote=quote)


def found(*items, cost="0.0005"):
    async def check(_complaint):
        return list(items), LLMUsage(provider="openrouter", model="stub", cost_myr=cost)
    return check


async def failing(_complaint):
    raise RuntimeError("provider down")


# --- code verification ---

def test_a_different_category_with_a_real_quote_is_kept():
    kept = other_issues([issue("FAILED_TRANSFER", "transfer rm46.54 gagal"), issue("FEE_DISPUTE", "Pastu ada caj fee pulak")],
                        "FAILED_TRANSFER", complaint())
    assert [(i.category, i.quote) for i in kept] == [("FEE_DISPUTE", "Pastu ada caj fee pulak")]


@pytest.mark.parametrize("found_issue, category, why", [
    (issue("FEE_DISPUTE", "annual fee is wrong"), "FAILED_TRANSFER", "invented quote"),
    (issue("FEE_DISPUTE", "caj fee"), "FAILED_TRANSFER", "quote under 8 characters"),
    (issue("FAILED_TRANSFER", "Transfer RM46.54 gagal"), "FAILED_TRANSFER", "same category"),
    (issue("FAILED_TRANSFER", "Transfer RM46.54 gagal"), "SCAM_TRANSFER", "natural overlap"),
    (issue("UNAUTHORISED_CARD", "duit dah tolak"), "SCAM_TRANSFER", "natural overlap"),
    (issue("SCAM_TRANSFER", "Pastu ada caj fee pulak"), "UNAUTHORISED_CARD", "natural overlap"),
])
def test_dropped(found_issue, category, why):
    assert other_issues([found_issue], category, complaint()) == [], why


def test_quotes_match_case_and_spacing_and_the_subject():
    c = complaint(text="ATM tak  keluar duit.\nStaff   kurang ajar sangat", subject="Yuran tahunan pelik")
    kept = other_issues([issue("SERVICE_QUALITY", "staff kurang ajar"), issue("FEE_DISPUTE", "yuran tahunan pelik"),
                         issue("SERVICE_QUALITY", "staff kurang ajar sangat")], "ATM_NOT_DISPENSED", c)
    assert [i.category for i in kept] == ["SERVICE_QUALITY", "FEE_DISPUTE"]  # one per category


# --- detection: off, fake, failure ---

def test_fake_provider_and_off_switch_make_no_call(monkeypatch):
    monkeypatch.setattr(issues_mod, "get_client", lambda: pytest.fail("no call expected"))
    assert asyncio.run(detect_issues(complaint())) == ([], None)  # tests run with fake providers
    monkeypatch.setattr(config, "LLM_EXTRACT", "openrouter:deepseek/x")
    monkeypatch.setattr(config, "LLM_ISSUES", "off")
    assert asyncio.run(detect_issues(complaint())) == ([], None)


def test_detection_uses_the_issues_step(monkeypatch):
    seen = {}

    class Client:
        async def structured(self, spec, messages, **kw):
            seen.update(model=spec.model, reasoning=kw["reasoning_effort"], schema=kw["schema_name"],
                        last=messages[-1]["content"])
            return [issue("FEE_DISPUTE", "Pastu ada caj fee pulak")], LLMUsage(provider="openrouter", model=spec.model)

    monkeypatch.setattr(config, "LLM_EXTRACT", "openrouter:deepseek/x")
    monkeypatch.setattr(config, "LLM_ISSUES", "")
    monkeypatch.setattr(issues_mod, "get_client", lambda: Client())
    found_issues, usage = asyncio.run(detect_issues(complaint()))
    assert found_issues[0].category == "FEE_DISPUTE" and usage.model == "deepseek/x"
    assert seen == {"model": "deepseek/x", "reasoning": "none", "schema": "complaint_issues",
                    "last": seen["last"]} and "caj fee pulak" in seen["last"]


# --- the hold, in the pipeline ---

def test_auto_refund_with_a_second_issue_is_held_and_nothing_scored_changes():
    c = load_complaint("CMP-00001")  # failed transfer, REFUND RM46.54, AUTO_RESOLVE offline
    plain = asyncio.run(run_pipeline(c, issues_check=found()))  # same text, nothing found
    held = asyncio.run(run_pipeline(c, issues_check=found(issue("FEE_DISPUTE", c.text[:30]))))
    scored = ("category", "matched_txn_id", "outcome", "refund_amount_myr", "priority", "reply_language")
    assert plain.decision.route == "AUTO_RESOLVE"
    assert {f: getattr(held.decision, f) for f in scored} == {f: getattr(plain.decision, f) for f in scored}
    assert held.decision.route == "HUMAN_APPROVAL" and held.decision.hold_reason == "second_issue"
    assert plain.decision.category == "FAILED_TRANSFER" and [i.category for i in held.other_issues] == ["FEE_DISPUTE"]
    assert "has been refunded" not in held.reply_text.lower()  # drafted for a pending case
    assert held.self_check.passed and held.prompt_version.endswith("+issues-v2")


def test_fraud_stays_with_the_fraud_team():
    c = load_complaint("CMP-00005")  # SCAM_TRANSFER, INVESTIGATE
    run = asyncio.run(run_pipeline(c, issues_check=found(issue("SERVICE_QUALITY", c.text[:20]))))
    assert run.decision.route == "FRAUD_TEAM" and run.decision.hold_reason == "second_issue"


def test_an_earlier_hold_reason_is_kept():
    c = load_complaint("CMP-00010")  # a fee dispute
    unknown = c.model_copy(update={"complaint_id": "CMP-99999", "customer_id": "CUS-99999"})  # engine holds it
    held = asyncio.run(run_pipeline(unknown, issues_check=found(issue("SERVICE_QUALITY", c.text[:20]))))
    assert held.decision.hold_reason == "customer_not_found" and held.other_issues  # stored, earlier reason kept


def test_a_failed_check_changes_nothing():
    c = load_complaint("CMP-00001")
    plain = asyncio.run(run_pipeline(c))
    failed = asyncio.run(run_pipeline(c, issues_check=failing))
    assert failed.decision.model_dump() == plain.decision.model_dump()
    assert failed.other_issues == [] and "issues check failed" in failed.error
    assert failed.decision.hold_reason != "llm_error"


def test_no_issues_found_changes_nothing():
    c = load_complaint("CMP-00001")
    assert asyncio.run(run_pipeline(c, issues_check=found())).decision.model_dump() == \
        asyncio.run(run_pipeline(c)).decision.model_dump()


# --- storage and the UI read API ---

def test_stored_shown_filtered_and_costed():
    s = CaseStore(":memory:")
    c = load_complaint("CMP-00001")
    run = asyncio.run(run_pipeline(c, issues_check=found(issue("FEE_DISPUTE", c.text[:30]), cost="0.0007")))
    s.register(c)
    s.save_run(c, run, latency_ms=5)
    detail = case_detail(s.conn, "CMP-00001")
    assert detail["other_issues"] == [{"category": "FEE_DISPUTE", "quote": c.text[:30]}]
    assert detail["case"]["waiting_reason"] == "Complaint raises a second issue"
    assert detail["usage"]["issues"]["cost_myr"] == "0.0007"
    assert run_cost(run) >= run.issues_usage.cost_myr
    assert [i["complaint_id"] for i in list_cases(s.conn, hold_reason="second_issue")["items"]] == ["CMP-00001"]


def test_old_runs_without_the_new_fields_still_load():
    old = AgentRun(run_id="r", complaint_id="c").model_dump(mode="json")
    old.pop("other_issues"), old.pop("issues_usage")
    run = AgentRun.model_validate(old)
    assert run.other_issues == [] and run.issues_usage is None and run_cost(run) == 0


# --- the prompt's examples are independent of the evaluation set ---

def test_fewshot_examples_share_nothing_with_the_evaluation_set():
    evaluation = [r["text"].lower() for r in csv.DictReader(open(EVAL, encoding="utf-8"))]
    for example in load_fewshot_issues():
        assert example["text"].lower() not in evaluation
        for item in example["issues"]:
            assert item["quote"].lower() in example["text"].lower()  # examples teach exact quoting
            assert not any(item["quote"].lower() in text for text in evaluation), item["quote"]


# --- the reply mentions the second issue (one sentence, promises nothing) ---

def test_code_reply_mentions_the_second_issue_and_passes_the_check():
    c = load_complaint("CMP-00001")
    run = asyncio.run(run_pipeline(c, issues_check=found(issue("FEE_DISPUTE", c.text[:30]))))
    assert "We have also noted your concern about a fee on your account" in run.reply_text
    assert combined_check(run.reply_text, EngineResult(match=run.match, decision=run.decision,
                                                       evidence=run.evidence)).passed


def test_malay_reply_uses_the_malay_sentence():
    assert also_raised("MS", ["SERVICE_QUALITY"]) == ("Kami juga telah mencatat kebimbangan anda berkenaan pengalaman anda "
                                                      "bersama kami dan memaklumkannya kepada pihak yang berkenaan.")
    assert also_raised("EN", []) is None


def test_unflagged_draft_requests_are_unchanged_so_the_cache_holds():
    c = load_complaint("CMP-00244")
    result = match_and_decide(c, asyncio.run(fake_extract(c))[0])
    assert build_draft_messages(result, c, None, "g") == build_draft_messages(result, c, None, "g", ())
    flagged = build_draft_messages(result, c, None, "g", ["SERVICE_QUALITY"])[1]["content"]
    assert "ALSO RAISED" in flagged and "your recent experience with us" in flagged
