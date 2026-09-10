from __future__ import annotations

"""v1087.6 content-free long-session daily-use evaluation evidence.

This module evaluates only explicit operator-recorded signals and bounded public
summary metadata. It never reads transcript text, private notes, prompts,
memories, provider payloads, or hidden reasoning, and it never invokes a model.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_daily_evaluation import load_daily_evaluation
from conversation_long_session_hardening import build_long_session_hardening_state

LONG_SESSION_EVALUATION_SCHEMA_VERSION = "1"
REQUIRED_LONG_SESSION_SIGNALS = (
    "consecutive_use",
    "long_history",
    "topic_transition",
    "draft_continuity",
    "scroll_anchor",
    "jump_to_latest",
    "pinned_context",
    "message_branch",
    "memory_correction",
    "context_inspection",
    "multi_tab",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_long_session_evaluation(evaluation_id: str) -> dict[str, Any]:
    summary = load_daily_evaluation(evaluation_id)
    session_id = str(summary.get("session_id") or "")
    hardening = build_long_session_hardening_state(session_id)
    observed = {
        str(signal)
        for row in list(summary.get("observations") or ())
        if isinstance(row, Mapping)
        for signal in list(row.get("signals") or ())
    }
    coverage = {signal: signal in observed for signal in REQUIRED_LONG_SESSION_SIGNALS}
    missing = [signal for signal, covered in coverage.items() if not covered]
    evidence = {
        "evaluation_id": str(summary.get("evaluation_id") or ""),
        "revision": int(summary.get("revision") or 0),
        "observation_evidence_digest": str(summary.get("observation_evidence_digest") or ""),
        "coverage": coverage,
        "hardening_contract_digest": str(hardening.get("contract_digest") or ""),
    }
    return {
        "type": "desktop_alpha_long_session_daily_use_evaluation",
        "schema_version": LONG_SESSION_EVALUATION_SCHEMA_VERSION,
        "evaluation_id": evidence["evaluation_id"],
        "evaluation_state": str(summary.get("state") or "active"),
        "evaluation_revision": evidence["revision"],
        "required_signals": list(REQUIRED_LONG_SESSION_SIGNALS),
        "signal_coverage": coverage,
        "covered_count": sum(1 for covered in coverage.values() if covered),
        "required_count": len(coverage),
        "missing_signals": missing,
        "coverage_status": "complete" if not missing else "incomplete",
        "bounded_history_contract_available": bool(hardening),
        "initial_complete_turn_limit": int(hardening.get("initial_render_limit") or 0),
        "earlier_complete_turn_limit": int(hardening.get("earlier_history_window_limit") or 0),
        "narrow_layout_contained": bool(hardening.get("narrow_layout_contained")),
        "scroll_anchor_preserved": bool(hardening.get("scroll_anchor_preserved_on_prepend")),
        "jump_to_latest_available": bool(hardening.get("jump_to_latest_preserved")),
        "evidence_digest": _digest(evidence),
        "transcript_inspected": False,
        "private_notes_inspected": False,
        "memory_content_inspected": False,
        "provider_invoked": False,
        "generation_invoked": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }


def long_session_evaluation_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "text", "message", "transcript", "prompt", "note", "notes",
        "memory", "memories", "provider_payload", "credentials", "vectors",
        "embedding", "hidden_reasoning", "chain_of_thought",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
