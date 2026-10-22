"""Build the evidence pack for one complaint: the complaint, the customer, their accounts, and every debit in the
matching window, annotated with reversals and ATM journal results. This is what an agent should reason over:
the facts it may cite, and nothing else.

Usage: python starter/evidence_pack.py CMP-00012
"""
import datetime as dt
import sys

from data import load, age_on, received


def evidence_pack(db, complaint_id):
    c = db.complaints[complaint_id]
    cust = db.customers[c["customer_id"]]
    recv = received(c)
    window = int(db.params["MATCH_WINDOW_DAYS"])
    age = age_on(cust["date_of_birth"], recv.date())
    lines = [
        f"COMPLAINT {complaint_id} received {c['received_at']} via {c['channel']}" + (f" | subject: {c['subject']}" if c["subject"] else ""),
        f"TEXT: {c['text']}",
        "",
        f"CUSTOMER {cust['customer_id']}: {cust['full_name']}, age {age} on the received date"
        + (" (VULNERABLE: priority moves up one level)" if age >= int(db.params["VULNERABLE_AGE"]) else "")
        + f", preferred language {cust['preferred_language']}, {cust['segment']}, {cust['city']}",
        "ACCOUNTS:",
    ]
    for a in db.accounts_by_customer[cust["customer_id"]]:
        lines.append(f"  {a['account_id']} {a['product']} opened {a['open_date']}" + (f", card ending {a['card_last4']}" if a["card_last4"] else ""))
    lines.append(f"DEBITS IN THE {window} DAYS BEFORE THE COMPLAINT (newest first):")
    since = recv - dt.timedelta(days=window + 1)
    for t in sorted(db.txns_by_customer[cust["customer_id"]], key=lambda t: t["time"], reverse=True):
        if t["direction"] != "DR" or not (since <= t["time"] <= recv):
            continue
        extra = []
        if t["card_last4"]:
            extra.append(f"card {t['card_last4']}")
        if t["auth_method"] not in ("", "N/A"):
            extra.append(f"auth {t['auth_method']}")
        if t["merchant_country"] and t["merchant_country"] != "MY":
            extra.append(f"country {t['merchant_country']}")
        if t["counterparty_account"]:
            extra.append(f"to {t['counterparty_account']} at {t['counterparty_bank']}")
        if t["status"] != "Completed":
            extra.append(f"STATUS {t['status']}")
        if t["txn_id"] in db.reversal_of:
            r = db.reversal_of[t["txn_id"]]
            extra.append(f"REVERSED by {r['txn_id']} on {r['txn_time']}")
        if t["txn_id"] in db.atm_journal:
            j = db.atm_journal[t["txn_id"]]
            extra.append(f"ATM {j['atm_id']} journal: requested RM{j['requested_myr']}, dispensed RM{j['dispensed_myr']} ({j['journal_status']})")
        desc = f" '{t['description']}'" if t["description"] else ""
        lines.append(f"  {t['txn_id']} {t['txn_time']} {t['account_id']} {t['channel']} RM{t['amount']:.2f} {t['merchant_or_counterparty']}{desc}"
                     + (f" [{'; '.join(extra)}]" if extra else ""))
    return "\n".join(lines)


if __name__ == "__main__":
    db = load()
    print(evidence_pack(db, sys.argv[1] if len(sys.argv) > 1 else "CMP-00012"))
