"""An LLM failure still gives a held, visible run with a prediction row; an engine bug does not invent a decision."""
import asyncio

from backend.agent.pipeline import run_pipeline
from backend.agent.stubs import stub_engine
from backend.agent.tools import load_complaint
from backend.llm.prompts import CLUES_SCHEMA_VERSION, EXTRACT_PROMPT_VERSION
from backend.llm.types import LLMError


async def failing_extract(complaint):
    raise LLMError("provider down")


async def failing_draft(result, feedback=None):
    raise LLMError("provider down")


def run(cid, **kwargs):
    return asyncio.run(run_pipeline(load_complaint(cid), **kwargs))


def test_extract_failure_falls_back_to_keywords_and_holds():
    r = run("CMP-00001", extract=failing_extract)  # failed DuitNow transfer
    assert r.decision is not None and r.decision.hold_reason == "llm_error"
    assert r.decision.route == "HUMAN_APPROVAL"
    assert r.error.startswith("extract failed") and "provider down" in r.error
    assert r.extract_usage.provider == "fake"
    assert r.prediction_row()["complaint_id"] == "CMP-00001"


def test_llm_error_replaces_engine_hold_reason():
    # stub_engine always says no_match for non-service categories; llm_error must still win
    r = run("CMP-00001", extract=failing_extract, engine=stub_engine)
    assert r.decision.hold_reason == "llm_error"


def test_extract_failure_on_fraud_stays_with_fraud_team():
    r = run("CMP-00005", extract=failing_extract)  # scam transfer → INVESTIGATE
    assert r.decision.outcome == "INVESTIGATE"
    assert (r.decision.route, r.decision.hold_reason) == ("FRAUD_TEAM", "llm_error")


def test_draft_failure_uses_code_reply_and_holds():
    r = run("CMP-00002", draft=failing_draft)  # service complaint, would otherwise auto-resolve
    assert r.reply_text.startswith(("Dear ", "Yang dihormati ", "Tuan/Puan"))  # the code-written reply
    assert (r.decision.hold_reason, r.decision.route) == ("llm_error", "HUMAN_APPROVAL")
    assert "draft failed" in r.error


def test_engine_failure_leaves_no_decision():
    def broken_engine(complaint, clues):
        raise RuntimeError("bug")

    r = run("CMP-00001", engine=broken_engine)
    assert r.decision is None and r.error.startswith("engine failed")


def test_healthy_run_has_no_error_and_records_versions():
    async def llm_like_extract(complaint):
        from backend.agent.stubs import fake_extract
        clues, usage = await fake_extract(complaint)
        return clues, usage.model_copy(update={"provider": "openrouter", "model": "m"})

    r = run("CMP-00001", extract=llm_like_extract)
    assert r.error is None and r.decision.hold_reason != "llm_error"
    assert (r.prompt_version, r.schema_version) == (f"{EXTRACT_PROMPT_VERSION}+code-template", CLUES_SCHEMA_VERSION)


def test_keyword_run_is_labelled_as_such():
    r = run("CMP-00001")  # default config: fake:keywords
    assert r.prompt_version == "keywords+code-template"
