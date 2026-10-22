"""Read-only queries behind /api/cases, /api/cases/{id}, /api/metrics and /api/audit (offline pipeline)."""
import asyncio
import datetime as dt
from decimal import Decimal

import pytest

from backend.agent.pipeline import run_pipeline
from backend.agent.reply_rules import combined_check
from backend.agent.tools import load_complaint
from backend.contracts import Complaint, LLMUsage
from backend.db import queries as Q
from backend.db.store import CaseStore, ReplyRefused

# Offline decisions: 00001 auto refund 46.54, 00002 auto info, 00005 fraud, 00007 decline (approval),
# 00010 held ambiguous_match, 00011 refund 600 / 00014 refund 709.62 / 00244 refund 550 (approval).
OFFICER = "Aina (officer)"

# Pinned shapes: docs/UI_API.md documents exactly these keys.
LIST_KEYS = {"total", "limit", "offset", "counts", "items"}
ITEM_KEYS = {"complaint_id", "customer_id", "customer_name", "received_at", "channel", "subject", "status", "queue",
             "case_state", "sent", "category", "outcome", "refund_amount_myr", "priority", "route", "hold_reason",
             "self_check", "vulnerable", "resolve_due_at", "waiting_reason", "human_action", "updated_at"}
DETAIL_KEYS = {"case", "complaint", "customer", "clues", "match", "decision", "evidence", "reply", "usage", "runs",
               "events", "outbound"}
CASE_KEYS = {"complaint_id", "status", "queue", "case_state", "sent", "error", "waiting_reason", "human_action",
             "autonomous_run_id", "current_run_id", "created_at", "updated_at"}
METRIC_KEYS = {"cases", "auto_resolve_rate", "holds", "self_check", "human", "sla", "cost_myr", "latency_ms",
               "models", "throughput"}
AUDIT_KEYS = {"total", "limit", "offset", "facets", "items"}
EVENT_KEYS = {"id", "complaint_id", "actor", "action", "run_id", "detail", "created_at"}


def put(store, cid, *, complaint=None, cost=None, **decision):
    """Run the offline pipeline and store the run; decision fields can be overridden for ordering tests."""
    c = complaint or load_complaint(cid)
    run = asyncio.run(run_pipeline(c))
    if decision:
        run = run.model_copy(update={"decision": run.decision.model_copy(update=decision)})
    if cost is not None:
        run = run.model_copy(update={"extract_usage": LLMUsage(cost_myr=Decimal(cost)), "draft_usage": []})
    store.register(c)
    store.save_run(c, run, latency_ms=5)


def act(store, cid, action, actor=OFFICER, reason="checked", reply_text=None):
    return store.act(cid, action, actor, reason, reply_text, check=combined_check)


def ids(result):
    return [i["complaint_id"] for i in result["items"]]


@pytest.fixture
def store():
    s = CaseStore(":memory:")
    s.register(load_complaint("CMP-00003"))  # still processing
    for cid in ("CMP-00001", "CMP-00244", "CMP-00007"):
        put(s, cid)
    return s


# --- queues ---

def test_mixed_database_counts_and_processing_item(store):
    r = Q.list_cases(store.conn)
    assert set(r) == LIST_KEYS and r["total"] == 4
    assert r["counts"] == {"processing": 1, "error": 0, "auto_resolved": 1, "awaiting_approval": 2,
                           "with_fraud_team": 0, "approved": 0, "rejected": 0}
    assert all(set(i) == ITEM_KEYS for i in r["items"])
    processing = next(i for i in r["items"] if i["complaint_id"] == "CMP-00003")
    assert processing["queue"] == "processing" and processing["outcome"] is None and processing["vulnerable"] is None
    assert processing["waiting_reason"] == "Agent is working on it"


def test_officer_queue_keeps_counts_for_every_case(store):
    r = Q.list_cases(store.conn, queue="awaiting_approval")
    assert sorted(ids(r)) == ["CMP-00007", "CMP-00244"] and r["total"] == 2
    assert sum(r["counts"].values()) == 4


def test_several_values_combine(store):
    put(store, "CMP-00011")
    act(store, "CMP-00244", "approve")
    act(store, "CMP-00007", "reject")
    act(store, "CMP-00011", "approve")
    assert sorted(ids(Q.list_cases(store.conn, queue="approved,rejected"))) == ["CMP-00007", "CMP-00011", "CMP-00244"]
    transfers = Q.list_cases(store.conn, queue="approved,rejected", category="FAILED_TRANSFER,SCAM_TRANSFER")
    assert ids(transfers) == ["CMP-00007"]


@pytest.mark.parametrize("kwargs", [{"queue": "nonsense"}, {"route": "AUTO"}, {"priority": "P4"},
                                    {"hold_reason": "tired"}, {"sort": "random"}])
def test_bad_filter_value(store, kwargs):
    with pytest.raises(Q.BadQuery):
        Q.list_cases(store.conn, **kwargs)


def test_urgent_first():
    s = CaseStore(":memory:")
    put(s, "CMP-00014", priority="P2", resolve_due_at=dt.datetime(2026, 10, 1, 9))
    put(s, "CMP-00011", priority="P1", resolve_due_at=dt.datetime(2026, 10, 3, 9))
    put(s, "CMP-00244", priority="P1", resolve_due_at=dt.datetime(2026, 9, 30, 9))
    s.register(load_complaint("CMP-00003"))  # no priority yet: last
    assert ids(Q.list_cases(s.conn)) == ["CMP-00244", "CMP-00011", "CMP-00014", "CMP-00003"]


def test_newest_activity_first(store):
    act(store, "CMP-00244", "approve")
    assert ids(Q.list_cases(store.conn, sort="recent", limit=1)) == ["CMP-00244"]


def test_paging(store):
    page = Q.list_cases(store.conn, limit=2, offset=2)
    assert page["total"] == 4 and len(page["items"]) == 2
    assert ids(page) == ids(Q.list_cases(store.conn))[2:]


def test_waiting_reasons():
    s = CaseStore(":memory:")
    for cid in ("CMP-00244", "CMP-00007", "CMP-00010", "CMP-00005", "CMP-00001"):
        put(s, cid)
    unknown = Complaint(**{**load_complaint("CMP-00005").model_dump(), "complaint_id": "CMP-90005",
                           "customer_id": "CUS-99999"})
    put(s, None, complaint=unknown)
    reasons = {i["complaint_id"]: i["waiting_reason"] for i in Q.list_cases(s.conn)["items"]}
    assert reasons == {
        "CMP-00244": "Refund over RM500",
        "CMP-00007": "Decline needs approval",
        "CMP-00010": "Ambiguous match",
        "CMP-00005": "Fraud investigation",
        "CMP-90005": "Fraud investigation · Customer not found",
        "CMP-00001": None,
    }
    held = Q.list_cases(s.conn, hold_reason="none", queue="awaiting_approval")
    assert sorted(ids(held)) == ["CMP-00007", "CMP-00244"]


def test_search(store):
    name = Q.list_cases(store.conn, q="CMP-00244")["items"][0]["customer_name"]
    assert ids(Q.list_cases(store.conn, q="cmp-00244")) == ["CMP-00244"]
    assert "CMP-00244" in ids(Q.list_cases(store.conn, q=name.split()[0].lower()))
    assert Q.list_cases(store.conn, q="no such text")["total"] == 0


def test_formats(store):
    item = Q.list_cases(store.conn, q="CMP-00001")["items"][0]
    assert item["refund_amount_myr"] == "46.54" and item["sent"] is True
    assert dt.datetime.fromisoformat(item["received_at"]) and "T" in item["received_at"]
    assert dt.datetime.fromisoformat(item["resolve_due_at"])


# --- one case ---

def test_detail_of_refund_awaiting_approval(store):
    d = Q.case_detail(store.conn, "CMP-00244")
    assert set(d) == DETAIL_KEYS and set(d["case"]) == CASE_KEYS
    assert d["decision"]["rule_id"] and d["decision"]["calculation"]["explanation"]
    assert d["decision"]["refund_amount_myr"] == "550.00"
    top = d["match"]["candidates"][0]
    assert top["txn_id"] == d["decision"]["matched_txn_id"] and 0 < top["score"] <= 1 and top["reasons"]
    assert d["reply"]["self_check"]["passed"] is True and d["reply"]["text"]
    assert d["case"]["waiting_reason"] == "Refund over RM500"
    assert d["customer"]["full_name"] and d["customer"]["accounts"]
    assert d["evidence"]["matched_txn"]["txn_id"] == d["decision"]["matched_txn_id"]
    assert d["usage"]["latency_ms"] == 5 and d["usage"]["extract"]["model"]
    assert d["outbound"] == [] and [e["action"] for e in d["events"]] == ["ingest", "agent_run"]
    assert [r["run_kind"] for r in d["runs"]] == ["autonomous"]


def test_detail_after_an_approval(store):
    before = Q.case_detail(store.conn, "CMP-00244")
    act(store, "CMP-00244", "approve")
    d = Q.case_detail(store.conn, "CMP-00244")
    assert d["case"]["case_state"] == "approved" and d["case"]["sent"] is True
    assert d["case"]["waiting_reason"] is None and d["case"]["human_action"]["actor"] == OFFICER
    assert d["events"][-1]["action"] == "approve" and d["events"][-1]["actor"] == OFFICER
    assert [(m["kind"], m["authorised_by"], m["refund_amount_myr"]) for m in d["outbound"]] == [
        ("resolution", OFFICER, "550.00")]
    assert d["decision"] == before["decision"] and d["reply"] == before["reply"]


def test_detail_while_processing(store):
    d = Q.case_detail(store.conn, "CMP-00003")
    assert d["case"]["queue"] == "processing" and d["complaint"]["text"]
    assert [e["action"] for e in d["events"]] == ["ingest"] and d["runs"] == []
    assert all(d[k] is None for k in ("customer", "clues", "match", "decision", "evidence", "reply", "usage"))


def test_detail_of_unknown_case(store):
    assert Q.case_detail(store.conn, "NO-SUCH-CASE") is None


# --- dashboard ---

def test_metrics_on_a_small_known_database():
    s = CaseStore(":memory:")
    for cid, cost in (("CMP-00001", "0.0010"), ("CMP-00002", "0.0020"), ("CMP-00244", "0.0030"),
                      ("CMP-00007", "0.0040")):
        put(s, cid, cost=cost)
    act(s, "CMP-00244", "approve")
    act(s, "CMP-00007", "reject")
    m = Q.metrics(s.conn, dt.datetime(2026, 9, 30, 16, 30))
    assert set(m) == METRIC_KEYS
    assert m["cases"]["total"] == 4 and m["cases"]["by_queue"]["approved"] == 1
    assert m["auto_resolve_rate"] == 0.5
    assert m["human"] == {"approved": 1, "rejected": 1, "edited_and_approved": 0, "acknowledged": 0,
                          "override_rate": 0.5}
    assert m["cost_myr"] == {"total": "0.0100", "mean": "0.0025", "p50": "0.0020", "p95": "0.0040", "max": "0.0040"}
    assert m["latency_ms"] == {"mean": 5, "p50": 5, "p95": 5, "max": 5}
    assert m["throughput"]["decided"] == 4 and sum(m["models"]["extract"].values()) == 4


def test_metrics_on_an_empty_database():
    m = Q.metrics(CaseStore(":memory:").conn, dt.datetime(2026, 9, 30))
    assert m["cases"]["total"] == 0 and set(m["cases"]["by_queue"].values()) == {0}
    assert m["auto_resolve_rate"] is None and m["human"]["override_rate"] is None
    assert m["cost_myr"]["mean"] is None and m["latency_ms"]["p95"] is None
    assert m["throughput"] == {"decided": 0, "first_at": None, "last_at": None, "per_hour": None}


def test_metrics_sla_as_of_the_live_round_day():
    s = CaseStore(":memory:")
    put(s, "CMP-00244", resolve_due_at=dt.datetime(2026, 9, 29, 10))
    put(s, "CMP-00011", resolve_due_at=dt.datetime(2026, 10, 3, 10))
    put(s, "CMP-00001")  # auto-resolved: not open
    sla = Q.metrics(s.conn, dt.datetime(2026, 9, 30, 16, 30))["sla"]
    assert sla == {"as_of": "2026-09-30T16:30:00", "open": 2, "overdue": 1, "due_within_24h": 0}


def test_metrics_counts_refused_edits_and_holds(store):
    put(store, "CMP-00010")
    with pytest.raises(ReplyRefused):
        act(store, "CMP-00244", "edit_approve", reply_text="We will refund RM999.99 for TXN-0000001.")
    m = Q.metrics(store.conn, dt.datetime(2026, 9, 30))
    assert m["self_check"]["human_edits_refused"] == 1
    assert m["holds"]["total"] == 1 and m["holds"]["by_reason"]["ambiguous_match"] == 1


def test_when_parses_dates_and_datetimes():
    assert Q.when("2026-09-30") == dt.datetime(2026, 9, 30)
    assert Q.when("30-09-2026", end_of_day=True) == dt.datetime(2026, 9, 30, 23, 59, 59)
    assert Q.when("2026-09-30T16:30") == dt.datetime(2026, 9, 30, 16, 30)
    with pytest.raises(Q.BadQuery):
        Q.when("yesterday")


# --- audit log ---

def test_who_did_what(store):
    act(store, "CMP-00244", "approve", reason="within limit")
    act(store, "CMP-00007", "reject", reason="customer is right")
    a = Q.audit(store.conn, actor=OFFICER)
    assert set(a) == AUDIT_KEYS and all(set(i) == EVENT_KEYS for i in a["items"])
    assert a["total"] == 2 and [i["action"] for i in a["items"]] == ["reject", "approve"]
    assert a["items"][0]["detail"]["reason"] == "customer is right"
    assert OFFICER in a["facets"]["actors"] and "approve" in a["facets"]["actions"]


def test_refused_edit_is_visible(store):
    with pytest.raises(ReplyRefused):
        act(store, "CMP-00244", "edit_approve", reply_text="We will refund RM999.99 for TXN-0000001.")
    items = Q.audit(store.conn, action="edit_approve_refused")["items"]
    assert len(items) == 1 and items[0]["detail"]["problems"] and "RM999.99" in items[0]["detail"]["reply_text"]


def test_people_only_dates_and_paging(store):
    act(store, "CMP-00244", "approve")
    assert [i["actor"] for i in Q.audit(store.conn, people_only=True)["items"]] == [OFFICER]
    everything = Q.audit(store.conn)["total"]
    assert Q.audit(store.conn, until="2000-01-01")["total"] == 0
    assert Q.audit(store.conn, since="2000-01-01", until="2999-12-31")["total"] == everything
    assert len(Q.audit(store.conn, limit=1)["items"]) == 1
    assert Q.audit(store.conn, action="ingest,approve", complaint_id="CMP-00244")["total"] == 2
    with pytest.raises(Q.BadQuery):
        Q.audit(store.conn, since="last week")


def test_reads_never_write(store):
    act(store, "CMP-00244", "approve")
    before = store.conn.total_changes
    Q.list_cases(store.conn)
    Q.case_detail(store.conn, "CMP-00244")
    Q.metrics(store.conn, dt.datetime(2026, 9, 30))
    Q.audit(store.conn)
    assert store.conn.total_changes == before
