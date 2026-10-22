"""Lookup tools over the hackathon CSVs. Owner: Dev A.

Step 0 provides only the cached loader; Dev A adds find_transactions, get_atm_journal, etc.
"""
from __future__ import annotations

from functools import lru_cache

from backend.contracts import Complaint
from starter import data as starter_data


@lru_cache(maxsize=1)
def get_db():
    """Load all CSVs once per process (see starter/data.py for the structure)."""
    return starter_data.load()


def load_complaint(complaint_id: str) -> Complaint:
    return Complaint(**get_db().complaints[complaint_id])
