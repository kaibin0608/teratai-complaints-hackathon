"""Score a predictions file against a labels file (the same scorer runs the leaderboard).

Usage:
    python scoring/score.py <predictions.csv> <labels.csv> [--details out.csv]

Only complaints that are in the labels file are scored. A complaint missing from the predictions scores 0.
Per complaint (max 100): matched_txn_id 25, outcome 25, refund_amount_myr 25, category 10, priority 10, reply_language 5.
Outcome and refund points only count when matched_txn_id is also right: a decision about the wrong transaction is not a decision.
Critical errors: a refund the bank does not owe (predicted refund > 0 when the answer is DECLINE or INVESTIGATE),
or a fraud case not sent to investigation (the answer is INVESTIGATE, the prediction is not).
Final score = mean points x (1 - 2 x critical error rate), never below 0.
"""
import csv
import sys
from collections import Counter

WEIGHTS = {"matched_txn_id": 25, "outcome": 25, "refund_amount_myr": 25, "category": 10, "priority": 10, "reply_language": 5}
GATED = ("outcome", "refund_amount_myr")  # need the right transaction
REQUIRED = ["complaint_id", "category", "matched_txn_id", "outcome", "refund_amount_myr", "priority", "reply_language", "route", "reply_text"]


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return {r["complaint_id"].strip(): {k: (v or "").strip() for k, v in r.items() if k} for r in rows}, (rows[0].keys() if rows else [])


def money(v):
    try:
        return round(float(v.replace(",", "").replace("RM", "")), 2) if v else 0.0
    except ValueError:
        return None


def field_ok(field, pred, truth):
    if field == "refund_amount_myr":
        p = money(pred)
        return p is not None and abs(p - money(truth)) < 0.005
    return pred.upper() == truth.upper()


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    preds, cols = load(sys.argv[1])
    labels, _ = load(sys.argv[2])
    missing_cols = [c for c in REQUIRED if c not in cols]
    if missing_cols:
        print(f"WARNING: predictions file is missing columns: {', '.join(missing_cols)}")
    hits, points, critical, detail = Counter(), [], Counter(), []
    missing = 0
    for cid, t in labels.items():
        p = preds.get(cid)
        if p is None:
            missing += 1; points.append(0); detail.append([cid, 0, "missing"]); continue
        got = {f: field_ok(f, p.get(f, ""), t[f]) for f in WEIGHTS}
        for f in GATED:
            got[f] = got[f] and got["matched_txn_id"]
        for f, ok in got.items():
            hits[f] += ok
        points.append(sum(WEIGHTS[f] for f, ok in got.items() if ok))
        notes = []
        if (money(p.get("refund_amount_myr", "")) or 0) > 0 and t["outcome"] in ("DECLINE", "INVESTIGATE"):
            critical["refund the bank does not owe"] += 1; notes.append("CRITICAL wrongful refund")
        if t["outcome"] == "INVESTIGATE" and p.get("outcome", "").upper() != "INVESTIGATE":
            critical["fraud case not investigated"] += 1; notes.append("CRITICAL missed fraud")
        notes += [f"{f}: got {p.get(f, '')!r}, expected {t[f]!r}" for f, ok in got.items() if not ok]
        detail.append([cid, points[-1], "; ".join(notes)])
    n = len(labels)
    mean = sum(points) / n if n else 0
    crit = sum(critical.values())
    final = max(0.0, mean * (1 - 2 * crit / n)) if n else 0
    print(f"Scored {n} complaints ({missing} missing from predictions, {len(set(preds) - set(labels))} predictions not in labels ignored)\n")
    print(f"{'field':<20}{'accuracy':>10}{'weight':>8}   (outcome and refund count only with the right transaction)")
    for f, w in WEIGHTS.items():
        print(f"{f:<20}{hits[f] / n:>10.1%}{w:>8}")
    if "route" in cols:
        r = sum(1 for cid, t in labels.items() if cid in preds and preds[cid].get("route", "").upper() == t.get("route", "").upper())
        print(f"{'route (not scored)':<20}{r / n:>10.1%}{'-':>8}")
    print(f"\nmean points          {mean:.2f} / 100")
    print(f"critical errors      {crit} ({crit / n:.1%})" + "".join(f"\n  - {k}: {v}" for k, v in critical.items()))
    print(f"FINAL SCORE          {final:.2f}")
    if "--details" in sys.argv:
        out = sys.argv[sys.argv.index("--details") + 1]
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["complaint_id", "points", "notes"]); w.writerows(detail)
        print(f"\nper-complaint details: {out}")


if __name__ == "__main__":
    main()
