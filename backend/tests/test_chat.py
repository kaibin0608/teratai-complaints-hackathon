"""The read-only case assistant (backend/chat). Owner: Dev A. Offline: keyword extractor, no real LLM."""
import sqlite3
import time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.agent.tools import load_complaint
from backend.chat import app as chat_module
from backend.contracts import LLMUsage
from backend.llm.client import LLMClient
from backend.llm.types import ModelSpec
from backend.main import create_app


def body(cid):
    c = load_complaint(cid)
    return {"complaint_id": c.complaint_id, "customer_id": c.customer_id, "received_at": f"{c.received_at:%Y-%m-%d %H:%M}",
            "channel": c.channel, "subject": c.subject, "text": c.text}


@pytest.fixture
def clients(tmp_path):
    """The main API fills a database; the assistant reads the same file."""
    db = tmp_path / "api.db"
    with TestClient(create_app(db)) as api:
        for cid in ("CMP-00244", "CMP-00005"):  # an approval case (ATM RM550) and a fraud case
            api.post("/complaints", json=body(cid))
        deadline = time.time() + 20
        while any(api.get(f"/cases/{c}").json()["status"] == "processing" for c in ("CMP-00244", "CMP-00005")):
            assert time.time() < deadline
            time.sleep(0.05)
        token = api.post("/api/auth/login", json={"username": "officer1", "password": "teratai123"}).json()["token"]
        with TestClient(chat_module.create_app(db)) as chat:
            yield api, chat, {"Authorization": f"Bearer {token}"}


def test_offline_answer_comes_from_the_stored_decision(clients):
    _, chat, _ = clients
    r = chat.post("/api/chat", json={"question": "Why this refund?", "complaint_id": "CMP-00244"})
    assert r.status_code == 200
    assert "REFUND RM550.00" in r.json()["answer"] and r.json()["model"] == "offline"


def test_question_without_a_case_answers_from_queue_counts(clients):
    _, chat, _ = clients
    r = chat.post("/api/chat", json={"question": "How many cases are waiting?"})
    assert r.status_code == 200 and "awaiting_approval" in r.json()["answer"]


def test_officer_cannot_ask_about_a_fraud_case(clients):
    _, chat, officer = clients
    assert chat.post("/api/chat", json={"question": "Why?", "complaint_id": "CMP-00005"}, headers=officer).status_code == 404
    assert chat.post("/api/chat", json={"question": "Why?", "complaint_id": "CMP-00244"}, headers=officer).status_code == 200


def test_bad_requests(clients):
    _, chat, _ = clients
    assert chat.post("/api/chat", json={"question": "   ", "complaint_id": "CMP-00244"}).status_code == 422
    assert chat.post("/api/chat", json={"question": "x" * 1001}).status_code == 422
    assert chat.post("/api/chat", json={"question": "Why?", "complaint_id": "NO-SUCH"}).status_code == 404
    assert chat.post("/api/chat", json={"question": "Why?"}, headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_the_assistant_cannot_write_to_the_database(clients, tmp_path):
    conn = chat_module._connect(tmp_path / "api.db")
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("UPDATE cases SET case_state = 'approved'")
    conn.close()


def test_llm_gets_the_case_facts_policy_and_question(clients, monkeypatch):
    """With a real model configured, the prompt carries the decision trail, the policy files and the history."""
    _, chat, officer = clients
    seen = {}

    async def fake_text(self, spec, messages, **kwargs):
        seen["messages"] = messages
        return "Refund of RM550.00: the ATM journal shows RM950.00 dispensed of RM1,500.00.", \
            LLMUsage(provider=spec.provider, model=spec.model, cost_myr=Decimal("0.0012"), latency_ms=900)

    monkeypatch.setattr(chat_module, "step_config", lambda step: (ModelSpec(provider="openrouter", model="test"), "prompt"))
    monkeypatch.setattr(LLMClient, "text", fake_text)
    r = chat.post("/api/chat", headers=officer, json={
        "question": "Why RM550?", "complaint_id": "CMP-00244",
        "history": [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]})
    assert r.status_code == 200
    assert r.json() == {"answer": "Refund of RM550.00: the ATM journal shows RM950.00 dispensed of RM1,500.00.",
                        "complaint_id": "CMP-00244", "cost_myr": "0.0012", "latency_ms": 900, "model": "openrouter:test"}
    messages = seen["messages"]
    assert messages[0]["role"] == "system" and "read-only" in messages[0]["content"]
    facts = messages[1]["content"]
    assert "TXN-0088211" in facts and "950.00" in facts and "ATM.SHORTFALL_REFUND" in facts
    assert "officer1" in facts and "fee_schedule.csv" in facts and "similar_cases" in facts
    assert [m["content"] for m in messages[-3:]] == ["Hi", "Hello", "Why RM550?"]


def test_who_can_act_is_worked_out_by_code(clients, tmp_path):
    api, _, _ = clients
    conn = chat_module._connect(tmp_path / "api.db")
    from backend.auth.users import get_user
    officer = get_user(conn, "officer1")
    within = chat_module.who_can_act(conn, "CMP-00244", officer)  # refund RM550, officer limit RM2,000
    assert within["first_tier_can_clear_it"] is True and within["the_person_asking_can_clear_it"] is True
    assert within["amount"] == "RM550.00" and within["limit_measured_on"] == "refund"
    fraud = chat_module.who_can_act(conn, "CMP-00005", None)  # disputed RM8,085.08, fraud limit RM5,000
    assert fraud["first_tier_can_clear_it"] is False and "over the fraud limit RM5,000.00" in fraud["why"]
    assert "the_person_asking_can_clear_it" not in fraud  # no login: nobody to judge
    conn.close()
    api.post("/cases/CMP-00244/actions", json={"action": "approve", "actor": "Aina"})
    conn = chat_module._connect(tmp_path / "api.db")
    assert chat_module.who_can_act(conn, "CMP-00244", officer)["open_for_a_decision"] is False
    conn.close()
