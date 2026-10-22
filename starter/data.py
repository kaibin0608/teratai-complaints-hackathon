"""Load the hackathon CSVs into plain Python structures (standard library only).

    from data import load
    db = load()
    db.complaints["CMP-00012"], db.customers["CUS-00001"], db.txns_by_customer["CUS-00001"]
"""
import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def read(name):
    with open(DATA / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class DB:
    pass


def load():
    db = DB()
    db.complaints = {r["complaint_id"]: r for r in read("complaints.csv")}
    db.customers = {r["customer_id"]: r for r in read("customers.csv")}
    db.accounts = {r["account_id"]: r for r in read("accounts.csv")}
    db.accounts_by_customer = defaultdict(list)
    for a in db.accounts.values():
        db.accounts_by_customer[a["customer_id"]].append(a)
    db.txns = {}
    db.txns_by_customer = defaultdict(list)
    db.reversal_of = {}  # original txn_id -> reversal txn
    for t in read("transactions.csv"):
        t["amount"] = float(t["amount_myr"])
        t["time"] = dt.datetime.strptime(t["txn_time"], "%Y-%m-%d %H:%M:%S")
        db.txns[t["txn_id"]] = t
        db.txns_by_customer[t["customer_id"]].append(t)
        if t["channel"] == "Reversal":
            db.reversal_of[t["description"].split()[-1]] = t
    db.atm_journal = {r["txn_id"]: r for r in read("atm_journal.csv")}
    db.fee_schedule = read("fee_schedule.csv")
    db.policy = {r["category"]: r for r in read("complaint_policy.csv")}
    db.params = {r["parameter"]: r["value"] for r in read("policy_parameters.csv")}
    db.sla = {r["priority"]: r for r in read("sla_policy.csv")}
    return db


def age_on(date_of_birth, day):
    dob = dt.date.fromisoformat(date_of_birth)
    return day.year - dob.year - ((day.month, day.day) < (dob.month, dob.day))


def received(complaint):
    return dt.datetime.strptime(complaint["received_at"], "%Y-%m-%d %H:%M")
