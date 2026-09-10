from __future__ import annotations

"""Clause-level distinction between ordinary conversation and live commands.

This module is deterministic and authority-free.  It identifies at most one
live imperative clause for the existing supervised action pipeline while
preserving the full turn for ordinary conversational generation.
"""

import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1206.2"
_MAX_CHARS = 12000
_ACTION_VERBS = (
    r"do|run|perform|execute|inspect|review|check|scan|change|modify|update|"
    r"create|make|build|develop|implement|code|fix|apply|install|delete|remove|switch|pull|start|"
    r"open|show|list|find|continue|begin|launch|test|verify|diagnose|repair"
)
_ACTION_START = re.compile(
    rf"^(?:please\s+)?(?:{_ACTION_VERBS})\b",
    re.I,
)
_WISH_ACTION_BOUNDARY = re.compile(
    rf",?\s+(?:and\s+then|then|and)\s+(?=(?:please\s+)?(?:{_ACTION_VERBS})\b)",
    re.I,
)
_MIXED_ACTION_BOUNDARY = re.compile(
    rf",\s*(?=(?:please\s+)?(?:{_ACTION_VERBS})\b)|\s+(?:and\s+then|then)\s+(?=(?:please\s+)?(?:{_ACTION_VERBS})\b)",
    re.I,
)
_MODAL = re.compile(r"^(?:please\s+)?(?:can|could|would|will)\s+you\s+.*\b(?:build|create|make|develop|implement|code|fix|repair|test|verify|update|modify)\b", re.I)
_HYPOTHETICAL = re.compile(r"\b(?:hypothetically|suppose|imagine|what\s+if|if\s+i\s+(?:said|asked|told\s+you)|in\s+theory)\b", re.I)
_WISH = re.compile(r"^(?:i\s+(?:wish|hope)|it\s+would\s+be\s+(?:nice|cool|great)|wouldn['’]?t\s+it\s+be\s+(?:nice|cool|great))\b", re.I)
_SUGGESTION = re.compile(r"^(?:maybe|perhaps|you\s+(?:could|might|should)|we\s+(?:could|might|should))\b", re.I)
_FULL_QUOTE = re.compile(r"^\s*(?:[\"'`].*[\"'`]|“.*”|‘.*’)\s*[.!?]*$", re.S)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _split(text: str) -> list[str]:
    parts: list[str] = []

    def append_segment(segment: str) -> None:
        cleaned = segment.strip()
        if not cleaned:
            return
        # A wish followed by an imperative in the same sentence contains two
        # distinct acts even without terminal punctuation.
        boundary = _WISH_ACTION_BOUNDARY.search(cleaned) if _WISH.search(cleaned) else _MIXED_ACTION_BOUNDARY.search(cleaned)
        if boundary and not _FULL_QUOTE.fullmatch(cleaned) and not _HYPOTHETICAL.search(cleaned):
            prefix = cleaned[:boundary.start()].rstrip(" ,")
            action = cleaned[boundary.end():].strip()
            if prefix and action:
                parts.extend((prefix, action))
                return
        parts.append(cleaned)

    start = 0
    quote = ""
    pairs = {"“": "”", "‘": "’", '"': '"', "'": "'", "`": "`"}
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = ""
        elif ch in pairs:
            quote = pairs[ch]
        elif ch in ".!?;\n":
            segment = text[start:i + 1].strip()
            append_segment(segment)
            start = i + 1
        i += 1
    tail = text[start:].strip()
    append_segment(tail)
    return parts or ([text.strip()] if text.strip() else [])


def _live_action(clause: str) -> bool:
    cleaned = clause.strip().rstrip(".!?;").strip()
    if not cleaned or _FULL_QUOTE.fullmatch(cleaned):
        return False
    if _HYPOTHETICAL.search(cleaned) or _WISH.search(cleaned) or _SUGGESTION.search(cleaned):
        return False
    return bool(_ACTION_START.search(cleaned) or _MODAL.search(cleaned))


def distinguish_natural_conversation_and_command(user_text: str) -> dict[str, Any]:
    text = str(user_text or "").strip()[:_MAX_CHARS]
    clauses = _split(text)
    live = [clause for clause in clauses if _live_action(clause)]
    conversational = [clause for clause in clauses if clause not in live]
    from release_self_knowledge import is_grouped_release_inspection
    grouped_release_inspection = is_grouped_release_inspection(text)
    if grouped_release_inspection:
        live = [text]
        conversational = []
    status = "conversation_only"
    if live and conversational:
        status = "mixed_conversation_and_action"
    elif live:
        status = "action_only"
    elif len(clauses) > 1:
        status = "multi_clause_conversation"
    action_text = " ".join(live[:1]).strip()
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "clause_count": len(clauses),
        "live_action_clause_count": len(live),
        "conversation_clause_count": len(conversational),
        "action_text": action_text,
        "conversation_text": " ".join(conversational).strip(),
        "mixed_turn": status == "mixed_conversation_and_action",
        "multiple_live_actions": len(live) > 1,
        "requires_clarification": len(live) > 1,
        "grouped_release_inspection": grouped_release_inspection,
        "authorization_inferred": False,
        "provider_contacted": False,
        "source_modified": False,
        "content_free_public_projection": True,
    }
    result["distinction_digest"] = _digest({k: v for k, v in result.items() if k not in {"action_text", "distinction_digest"}})
    return result


def public_conversation_command_distinction(value: dict[str, Any]) -> dict[str, Any]:
    row = {k: v for k, v in value.items() if k not in {"action_text", "conversation_text"}}
    row["conversation_text_exposed"] = False
    row["action_text_exposed"] = False
    row["understanding_summary"] = (
        "I understood one conversational part and one requested action."
        if value.get("mixed_turn") else
        "I understood a requested action." if int(value.get("live_action_clause_count") or 0) == 1 else
        "I understood this as conversation, not a live action."
    )
    return row
