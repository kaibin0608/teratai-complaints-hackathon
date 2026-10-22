"""Category handler registry. Owner: Dev A.

Maps Category literal to handler instance. Supports fallback to related handlers.
"""
from __future__ import annotations

from backend.contracts import Category

from .base import CategoryHandler

_HANDLERS: dict[Category, CategoryHandler] = {}

RELATED_FAMILIES: dict[str, list[str]] = {
    "card": ["DUPLICATE_CHARGE", "UNAUTHORISED_CARD"],
    "transfer": ["FAILED_TRANSFER", "SCAM_TRANSFER"],
}


def register(cls: type[CategoryHandler]) -> type[CategoryHandler]:
    instance = cls()
    _HANDLERS[instance.category] = instance
    return cls


def get_handler(category: Category) -> CategoryHandler:
    if category not in _HANDLERS:
        raise KeyError(f"no handler registered for {category}")
    return _HANDLERS[category]


def get_fallback_categories(category: Category) -> list[Category]:
    """Related categories on the same channel family, for fallback matching."""
    for _family, cats in RELATED_FAMILIES.items():
        if category in cats:
            return [c for c in cats if c != category and c in _HANDLERS]
    return []


def registered_categories() -> list[Category]:
    return list(_HANDLERS.keys())
