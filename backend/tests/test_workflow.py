"""Bonus platform workflow rules (offline pipeline): limits, sensitivity, two tiers, fraud steps, send back."""
import asyncio
import json

import pytest

from backend.agent.pipeline import run_pipeline
from backend.agent.reply_rules import combined_check
from backend.agent.tools import load_complaint
from backend.auth.users import get_user
from backend.db.seed import seed_users
from backend.db.store import CaseStore, InvalidAction, ReplyRefused, WrongState
from backend.db.workflow import Forbidden, Workflow

# Offline decisions: approval refunds 00244 RM550 and 00023 RM2,788.60 (over the RM2,000 officer limit);
# 00105 RM653.49 for a 65+ customer; fraud 00003 (transaction RM1,404.18) and 00005 (RM8,085.08, over RM5,000).
OK_REFUND, BIG_REFUND, ELDERLY, FRAUD_LOW, FRAUD_HIGH = "CMP-00244", "CMP-00023", "CMP-00105", "CMP-00003", "CMP-00005"
INVENTED = "Dear customer, we will refund RM999.00 for TXN-0000001."


@pytest.fixture
def store():
    s = CaseStore(":memory:")
    seed_users(s.conn)
    for cid in (OK_REFUND, BIG_REFUND, ELDERLY, FRAUD_LOW, FRAUD_HIGH):
        c = load_complaint(cid)
        s.register(c)
        s.save_run(c, asyncio.run(run_pipeline(c)), latency_ms=5)
    return s


@pytest.fixture
def wf(store):
    return Workflow(store)


@pytest.fixture
def users(store):
    return {name: get_user(store.conn, name) for name in ("officer1", "officer2", "fraud1", "manager1")}


def case(store, cid):
    return store.get_case(cid)


def actions(store, cid):
    return [(e["actor"], e["action"]) for e in store.events(cid) if e["actor"] != "agent"]


# --- first tier: limits and sensitivity ---

def test_officer_approves_within_the_limit(store, wf, users):
    wf.approve(OK_REFUND, users["officer1"], "checked the ATM journal")
    c = case(store, OK_REFUND)
    assert c["case_state"] == "approved" and c["sent"]
    assert [(m["kind"], m["authorised_by"], m["refund_sen"]) for m in store.outbound(OK_REFUND)] == [
        ("resolution", "officer1", 55000)]
    assert json.loads(c["human_action"])["actor"] == "officer1"


def test_over_the_limit_must_escalate(store, wf, users):
    with pytest.raises(Forbidden) as err:
        wf.approve(BIG_REFUND, users["officer1"])
    assert err.value.error == "escalate to a manager"
    assert err.value.why == "refund RM2,788.60 is over your limit RM2,000.00"
    assert err.value.info == {"limit": "2000.00", "amount": "2788.60"}
    assert store.outbound(BIG_REFUND) == [] and case(store, BIG_REFUND)["case_state"] == "awaiting_approval"


def test_elderly_customer_is_sensitive(store, wf, users):
    with pytest.raises(Forbidden) as err:
        wf.approve(ELDERLY, users["officer1"])
    assert err.value.why == "sensitive: Customer aged 65+"


def test_manual_flag_makes_a_case_sensitive(store, wf, users):
    wf.flag_sensitive(OK_REFUND, users["officer1"], "customer is recently bereaved")
    with pytest.raises(Forbidden, match="sensitive: customer is recently bereaved"):
        wf.approve(OK_REFUND, users["officer2"])
    with pytest.raises(WrongState):
        wf.flag_sensitive(OK_REFUND, users["officer1"], "again")
    with pytest.raises(InvalidAction):
        wf.flag_sensitive(BIG_REFUND, users["officer1"], "  ")


def test_manager_approves_directly_with_no_limit(store, wf, users):
    wf.approve(BIG_REFUND, users["manager1"])
    wf.approve(ELDERLY, users["manager1"])
    assert case(store, BIG_REFUND)["sent"] and case(store, ELDERLY)["sent"]


def test_reject_needs_a_reason_and_sends_nothing(store, wf, users):
    with pytest.raises(InvalidAction):
        wf.reject(OK_REFUND, users["officer1"], "")
    assert case(store, OK_REFUND)["case_state"] == "awaiting_approval"
    wf.reject(OK_REFUND, users["officer1"], "customer withdrew the complaint")
    assert case(store, OK_REFUND)["case_state"] == "rejected" and store.outbound(OK_REFUND) == []


# --- edits ---

def test_edit_with_an_invented_amount_locks_approve(store, wf, users):
    checked = wf.edit_reply(OK_REFUND, users["officer1"], INVENTED, "friendlier")
    assert not checked.passed and any("RM999.00" in p for p in checked.problems)
    draft = json.loads(case(store, OK_REFUND)["draft_reply"])
    assert draft["self_check"] == "flagged" and draft["text"] == INVENTED
    with pytest.raises(ReplyRefused):
        wf.approve(OK_REFUND, users["officer1"])
    assert store.outbound(OK_REFUND) == []

    agent_reply = store.current_run(case(store, OK_REFUND)).reply_text
    fixed = agent_reply.replace("Dear", "Dear valued customer", 1)
    assert wf.edit_reply(OK_REFUND, users["officer1"], fixed, "warmer greeting").passed
    wf.approve(OK_REFUND, users["officer1"])
    assert store.outbound(OK_REFUND)[0]["reply_text"] == fixed
    edits = [e for e in store.events(OK_REFUND) if e["action"] == "edit_reply"]
    assert json.loads(edits[0]["detail"])["old"] == agent_reply
    assert json.loads(edits[1]["detail"])["old"] == INVENTED


# --- escalation and the second tier ---

def test_escalate_then_manager_approves(store, wf, users):
    wf.escalate(BIG_REFUND, users["officer1"], "over my limit")
    c = case(store, BIG_REFUND)
    assert c["workflow"] == "escalated" and not c["sent"] and c["case_state"] == "awaiting_approval"
    assert json.loads(c["escalation"])["proposal"]["action"] == "approve"

    with pytest.raises(WrongState):  # first tier can't clear it
        wf.approve(BIG_REFUND, users["officer2"])
    with pytest.raises(WrongState):  # nor can the open contract route
        store.act(BIG_REFUND, "approve", "judge", check=combined_check)
    with pytest.raises(Forbidden):
        wf.second_tier(BIG_REFUND, users["officer1"], True, "self-approval")

    wf.second_tier(BIG_REFUND, users["manager1"], True, "verified with branch")
    c = case(store, BIG_REFUND)
    assert c["case_state"] == "approved" and c["sent"] and c["workflow"] == "closed"
    assert [m["authorised_by"] for m in store.outbound(BIG_REFUND)] == ["manager1"]
    assert actions(store, BIG_REFUND) == [("officer1", "escalate"), ("manager1", "second_tier_approve")]


def test_manager_rejects_an_escalation(store, wf, users):
    wf.escalate(BIG_REFUND, users["officer1"], "not sure the transfer failed")
    with pytest.raises(InvalidAction):
        wf.second_tier(BIG_REFUND, users["manager1"], False, "")
    wf.second_tier(BIG_REFUND, users["manager1"], False, "transfer reached the recipient")
    c = case(store, BIG_REFUND)
    assert c["case_state"] == "rejected" and not c["sent"] and c["workflow"] == "closed"
    with pytest.raises(WrongState):
        wf.second_tier(BIG_REFUND, users["manager1"], True, "changed my mind")


def test_manager_edits_while_escalated_and_the_edit_is_sent(store, wf, users):
    wf.escalate(BIG_REFUND, users["officer1"], "over my limit")
    with pytest.raises(WrongState):  # the officer can't edit once it's escalated
        wf.edit_reply(BIG_REFUND, users["officer1"], "x", "y")
    reply = store.current_run(case(store, BIG_REFUND)).reply_text + " "
    wf.edit_reply(BIG_REFUND, users["manager1"], reply.strip() + "\n\nWe apologise for the delay.", "apology")
    wf.second_tier(BIG_REFUND, users["manager1"], True, "ok")
    assert store.outbound(BIG_REFUND)[0]["reply_text"].endswith("We apologise for the delay.")


def test_manager_does_not_escalate_to_themselves(store, wf, users):
    with pytest.raises(Forbidden):
        wf.escalate(BIG_REFUND, users["manager1"], "why not")


# --- team, assignee and reassign ---

def test_officer_cannot_touch_fraud_cases_and_analyst_cannot_approve(store, wf, users):
    with pytest.raises(Forbidden):
        wf.record_outcome(FRAUD_LOW, users["officer1"], "not_fraud", "x")
    with pytest.raises(Forbidden):
        wf.approve(OK_REFUND, users["fraud1"])
    with pytest.raises(WrongState):  # the manager can act anywhere, but approve is not a fraud action
        wf.approve(FRAUD_LOW, users["manager1"])


def test_reassign_and_the_assignee_rule(store, wf, users):
    with pytest.raises(InvalidAction):
        wf.reassign(OK_REFUND, users["manager1"], "fraud1")
    with pytest.raises(InvalidAction):
        wf.reassign(OK_REFUND, users["manager1"], "nobody")
    with pytest.raises(Forbidden):
        wf.reassign(OK_REFUND, users["officer1"], "officer2")
    wf.reassign(OK_REFUND, users["manager1"], "officer2", "officer1 on leave")
    assert case(store, OK_REFUND)["assigned_to"] == "officer2"
    with pytest.raises(Forbidden, match="assigned to officer2"):
        wf.approve(OK_REFUND, users["officer1"])
    wf.approve(OK_REFUND, users["officer2"])
    detail = json.loads([e for e in store.events(OK_REFUND) if e["action"] == "reassign"][0]["detail"])
    assert detail == {"from": None, "to": "officer2", "reason": "officer1 on leave"}


# --- fraud ---

def test_fraud_acknowledge_investigate_record(store, wf, users):
    with pytest.raises(WrongState):  # nothing before acknowledgement
        wf.record_outcome(FRAUD_LOW, users["fraud1"], "not_fraud", "x")
    wf.acknowledge(FRAUD_LOW, users["fraud1"])
    assert case(store, FRAUD_LOW)["workflow"] == "investigating"
    assert [(m["kind"], m["authorised_by"]) for m in store.outbound(FRAUD_LOW)] == [("holding_reply", "fraud1")]
    wf.investigate(FRAUD_LOW, users["fraud1"], "called the customer", "investigation")
    wf.investigate(FRAUD_LOW, users["fraud1"], "recall requested from receiving bank", "recall_attempt")
    with pytest.raises(InvalidAction):
        wf.investigate(FRAUD_LOW, users["fraud1"], "x", "gossip")
    with pytest.raises(InvalidAction):
        wf.record_outcome(FRAUD_LOW, users["fraud1"], "maybe", "x")
    wf.record_outcome(FRAUD_LOW, users["fraud1"], "confirmed_fraud", "card cloned at a fuel station")
    c = case(store, FRAUD_LOW)
    assert c["workflow"] == "closed" and json.loads(c["fraud_outcome"])["outcome"] == "confirmed_fraud"
    assert c["case_state"] == "with_fraud_team" and len(store.outbound(FRAUD_LOW)) == 1
    assert [a for _, a in actions(store, FRAUD_LOW)] == ["acknowledge", "investigate", "investigate", "record_outcome"]


def test_high_value_fraud_goes_to_the_manager(store, wf, users):
    wf.acknowledge(FRAUD_HIGH, users["fraud1"])
    with pytest.raises(Forbidden) as err:
        wf.record_outcome(FRAUD_HIGH, users["fraud1"], "confirmed_fraud", "mule account")
    assert err.value.why == "disputed transaction RM8,085.08 is over your limit RM5,000.00"
    with pytest.raises(InvalidAction):  # a fraud escalation carries the proposed outcome
        wf.escalate(FRAUD_HIGH, users["fraud1"], "high value")
    wf.escalate(FRAUD_HIGH, users["fraud1"], "high value", outcome="confirmed_fraud")
    wf.second_tier(FRAUD_HIGH, users["manager1"], False, "check the device logs first")
    assert case(store, FRAUD_HIGH)["workflow"] == "investigating"  # back to the analyst
    wf.escalate(FRAUD_HIGH, users["fraud1"], "device logs checked", outcome="confirmed_fraud")
    wf.second_tier(FRAUD_HIGH, users["manager1"], True, "agreed")
    outcome = json.loads(case(store, FRAUD_HIGH)["fraud_outcome"])
    assert outcome["outcome"] == "confirmed_fraud" and outcome["by"] == "manager1" and outcome["proposed_by"] == "fraud1"
    assert case(store, FRAUD_HIGH)["workflow"] == "closed"


# --- send back ---

def test_send_back_marks_the_case_and_blocks_actions(store, wf, users):
    with pytest.raises(InvalidAction):
        wf.send_back(OK_REFUND, users["officer1"], "")
    wf.send_back(OK_REFUND, users["officer1"], "the charge was on 17-07-2026")
    assert case(store, OK_REFUND)["workflow"] == "reprocessing"
    for attempt in (lambda: wf.approve(OK_REFUND, users["officer1"]),
                    lambda: wf.send_back(OK_REFUND, users["officer1"], "again"),
                    lambda: store.act(OK_REFUND, "approve", "judge", check=combined_check)):
        with pytest.raises(WrongState):
            attempt()


def test_double_click_sends_once(store, wf, users):
    wf.approve(OK_REFUND, users["officer1"])
    with pytest.raises(WrongState):
        wf.approve(OK_REFUND, users["officer1"])
    assert len(store.outbound(OK_REFUND)) == 1
