"""LLM step: complaint text → validated Clues. Owner: Dev B.

Implements the Extractor protocol. The provider and model come from LLM_EXTRACT; "fake:<anything>" runs the
offline keyword extractor, so tests and fresh clones need no key.
"""
from __future__ import annotations

from backend.agent.stubs import fake_extract
from backend.contracts import Clues, Complaint, LLMUsage
from backend.llm.client import get_client
from backend.llm.prompts import CLUES_WIRE_SCHEMA, build_extract_messages, wire_to_clues
from backend.llm.registry import step_config


async def extract(complaint: Complaint) -> tuple[Clues, LLMUsage]:
    spec, json_mode = step_config("extract")
    if spec.provider == "fake":
        return await fake_extract(complaint)
    return await get_client().structured(
        spec,
        build_extract_messages(complaint),
        schema=CLUES_WIRE_SCHEMA,
        schema_name="complaint_clues",
        convert=wire_to_clues,
        json_mode=json_mode,
        temperature=0.0,
        max_tokens=600,
    )
