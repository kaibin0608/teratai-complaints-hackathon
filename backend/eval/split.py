"""Pick the fixed 50-complaint pilot and a held-back slice from labels_train.csv (seeded, reproducible).

The pilot covers every (category, channel) pair present; the holdout is 20% of the remaining labels
and is only used to check prompt/matcher changes, never to tune them.

Usage: python -m backend.eval.split
"""
from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path

from starter.data import read

OUT = Path(__file__).resolve().parent
PILOT_SIZE = 50
HOLDOUT_SHARE = 0.2
SEED = 42


def main() -> None:
    channel = {c["complaint_id"]: c["channel"] for c in read("complaints.csv")}
    labels = read("labels_train.csv")
    rng = random.Random(SEED)
    rng.shuffle(labels)

    pilot: list[str] = []
    seen: set[tuple[str, str]] = set()
    for r in labels:  # one of each (category, channel) first
        key = (r["category"], channel[r["complaint_id"]])
        if key not in seen:
            seen.add(key)
            pilot.append(r["complaint_id"])
    by_category = defaultdict(list)
    for r in labels:
        if r["complaint_id"] not in pilot:
            by_category[r["category"]].append(r["complaint_id"])
    cats = sorted(by_category)
    i = 0
    while len(pilot) < PILOT_SIZE:  # top up round-robin by category
        pool = by_category[cats[i % len(cats)]]
        if pool:
            pilot.append(pool.pop())
        i += 1
    pilot = pilot[:PILOT_SIZE]

    rest = [r["complaint_id"] for r in labels if r["complaint_id"] not in set(pilot)]
    holdout = rest[: int(len(rest) * HOLDOUT_SHARE)]

    (OUT / "pilot_ids.txt").write_text("\n".join(sorted(pilot)) + "\n", encoding="utf-8")
    (OUT / "holdout_ids.txt").write_text("\n".join(sorted(holdout)) + "\n", encoding="utf-8")
    print(f"pilot: {len(pilot)} ids, {len(seen)} (category, channel) pairs; holdout: {len(holdout)} ids")


if __name__ == "__main__":
    main()
