from __future__ import annotations

"""Content-free review rationale for explicitly stored important moments."""

import hashlib
from typing import Any, Mapping

from memory_commit_attribution import public_memory_commit_attribution


IMPORTANT_MOMENT_PROVENANCE_SCHEMA_VERSION = "1"

_RATIONALE_TEXT = {
    "operator_reviewed_exact_content": "The operator explicitly reviewed and retained the exact curated summary.",
    "operator_explicit_pending_review": "The operator explicitly created or corrected this moment, but exact-content retention is not currently confirmed.",
    "generated_turn_attributed": "The moment is linked to a successfully completed generated turn and remains subject to operator curation.",
    "legacy_unknown": "The stored moment predates complete provenance and requires operator review before it should be treated as established continuity.",
}


def _content(memory: Mapping[str, Any]) -> str:
    return " ".join(str(memory.get("content") or memory.get("thought") or memory.get("summary") or "").split())


def build_important_moment_provenance(memory: Mapping[str, Any]) -> dict[str, Any]:
    source = str(memory.get("source") or "")[:80]
    raw_attribution = memory.get("memory_commit_attribution") if isinstance(memory.get("memory_commit_attribution"), dict) else {}
    attribution = public_memory_commit_attribution(raw_attribution)
    attribution_available = bool(attribution.get("available")) or bool(
        raw_attribution.get("eligible_for_durable_commit")
        and raw_attribution.get("provider_generation_completed")
        and raw_attribution.get("operation_completion_claimed")
        and str(raw_attribution.get("completion_state") or "").strip().lower() == "completed"
    )
    operator_explicit = bool(memory.get("operator_explicit")) or source.startswith("operator_relationship_curation")
    retention_confirmed = bool(memory.get("retention_confirmed"))
    if operator_explicit and retention_confirmed:
        rationale_code = "operator_reviewed_exact_content"
    elif operator_explicit:
        rationale_code = "operator_explicit_pending_review"
    elif attribution_available:
        rationale_code = "generated_turn_attributed"
    else:
        rationale_code = "legacy_unknown"

    text = _content(memory)
    temporal_state = str(memory.get("moment_state") or memory.get("temporal_state") or "open").strip().lower() or "open"
    status = str(memory.get("status") or "active").strip().lower() or "active"
    eligible = bool(memory.get("relationship_eligible") is True or memory.get("use_in_conversation") is True)
    if status in {"retracted", "deleted", "rejected", "expired", "stale", "blocked"}:
        eligible = False
    return {
        "schema_version": IMPORTANT_MOMENT_PROVENANCE_SCHEMA_VERSION,
        "available": bool(source or attribution_available),
        "origin": "operator_explicit" if operator_explicit else "generated_turn" if attribution_available else "legacy_unknown",
        "rationale_code": rationale_code,
        "rationale": _RATIONALE_TEXT[rationale_code],
        "operator_explicit": operator_explicit,
        "retention_confirmed": retention_confirmed,
        "review_required": not retention_confirmed,
        "eligibility_state": "eligible" if eligible and temporal_state == "open" else "not_currently_used",
        "temporal_state": temporal_state,
        "importance": str(memory.get("importance") or "medium")[:20],
        "occurred_at": str(memory.get("occurred_at") or "")[:40],
        "created_at": str(memory.get("created_at") or "")[:40],
        "content_digest": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
        "raw_conversation_history_changed": False,
        "provider_invoked": False,
        "transcript_inferred": False,
        "content_free_evidence": True,
        "contains_prompt": False,
        "contains_response": False,
    }
