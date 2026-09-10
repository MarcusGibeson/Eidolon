from __future__ import annotations

"""v1087.8 deterministic privacy-safe evaluation review and client export packet."""

from typing import Any, Mapping
import hashlib
import json

from conversation_daily_evaluation import load_daily_evaluation
from conversation_evaluation_long_session import build_long_session_evaluation
from conversation_evaluation_recovery_scenarios import build_restart_outage_evaluation
from conversation_evaluation_reproduction import build_reproduction_packet
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

EVALUATION_REVIEW_EXPORT_SCHEMA_VERSION = "1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_evaluation_review_export(evaluation_id: str) -> dict[str, Any]:
    summary = load_daily_evaluation(evaluation_id)
    reproduction = build_reproduction_packet(evaluation_id)
    recovery = build_restart_outage_evaluation(evaluation_id)
    long_session = build_long_session_evaluation(evaluation_id)
    outcome = dict(summary.get("outcome") or {})
    review = {
        "type": "desktop_alpha_daily_evaluation_review",
        "schema_version": EVALUATION_REVIEW_EXPORT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "evaluation_id": str(summary.get("evaluation_id") or ""),
        "evaluation_state": str(summary.get("state") or "active"),
        "evaluation_revision": int(summary.get("revision") or 0),
        "observation_count": int(summary.get("observation_count") or 0),
        "observation_evidence_digest": str(summary.get("observation_evidence_digest") or ""),
        "outcome": str(outcome.get("outcome") or outcome.get("outcome_code") or "unclassified"),
        "outcome_reason": str(outcome.get("reason") or ""),
        "reproduction_packet_digest": str(reproduction.get("packet_digest") or ""),
        "restart_outage_status": str(recovery.get("coverage_status") or "incomplete"),
        "restart_outage_covered_count": int(recovery.get("covered_count") or 0),
        "restart_outage_required_count": int(recovery.get("required_count") or 0),
        "long_session_status": str(long_session.get("coverage_status") or "incomplete"),
        "long_session_covered_count": int(long_session.get("covered_count") or 0),
        "long_session_required_count": int(long_session.get("required_count") or 0),
        "issue_domains": list(reproduction.get("issue_domains") or ()),
        "severities": list(reproduction.get("severities") or ()),
        "signals": list(reproduction.get("signals") or ()),
        "reproducible_observation_count": int(reproduction.get("reproducible_observation_count") or 0),
        "operator_review_required": True,
        "release_decision": "operator_only",
        "installation_decision": "operator_only",
        "promotion_decision": "operator_only",
        "provider_invoked": False,
        "generation_invoked": False,
        "transcript_included": False,
        "prompt_included": False,
        "private_notes_included": False,
        "memory_content_included": False,
        "provider_payload_included": False,
        "credentials_included": False,
        "vectors_included": False,
        "hidden_reasoning_included": False,
        "content_free": True,
        "redacted": True,
    }
    review["review_digest"] = _digest(review)
    document = json.dumps(review, indent=2, sort_keys=True) + "\n"
    return {
        "type": "desktop_alpha_daily_evaluation_review_export",
        "schema_version": EVALUATION_REVIEW_EXPORT_SCHEMA_VERSION,
        "filename": f"{review['evaluation_id']}_privacy_safe_review.json",
        "media_type": "application/json",
        "document_sha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
        "document": document,
        "review": review,
        "server_file_written": False,
        "client_download_ready": True,
        "operator_review_required": True,
        "release_certified": False,
        "promotion_performed": False,
        "installation_performed": False,
        "provider_invoked": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }


def evaluation_review_export_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "note", "notes", "message", "messages", "transcript", "prompt",
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
