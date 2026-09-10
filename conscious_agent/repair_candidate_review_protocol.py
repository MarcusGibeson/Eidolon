from __future__ import annotations

"""v1090.0 bounded repair-candidate review protocol.

The protocol defines review vocabulary and operator boundaries only. It never
registers, generates, opens, executes, applies, installs, promotes, or certifies
an artifact, and it never invokes a provider.
"""

from typing import Any, Mapping
import hashlib
import json

REPAIR_CANDIDATE_REVIEW_PROTOCOL_SCHEMA_VERSION = "1"
REPAIR_CANDIDATE_KINDS = ("source_archive", "patch_artifact", "test_fixture", "external_candidate")
REPAIR_CANDIDATE_REVIEW_STATES = (
    "registered", "reviewing", "needs_changes", "acceptable_for_testing", "rejected", "superseded"
)
REPAIR_CANDIDATE_REVIEW_AREAS = (
    "artifact_integrity", "source_scope", "verification_evidence", "privacy_boundary", "operator_boundary"
)
MAX_REPAIR_CANDIDATES_PER_FINDING = 24
MAX_REPAIR_CANDIDATE_REVIEW_EVENTS = 32
MAX_CANDIDATE_LABEL_CHARS = 200
MAX_CANDIDATE_REFERENCE_CHARS = 1000
MAX_CANDIDATE_REVIEW_NOTE_CHARS = 2000


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def build_repair_candidate_review_protocol() -> dict[str, Any]:
    contract = {
        "candidate_kinds": list(REPAIR_CANDIDATE_KINDS),
        "review_states": list(REPAIR_CANDIDATE_REVIEW_STATES),
        "review_areas": list(REPAIR_CANDIDATE_REVIEW_AREAS),
        "maximum_candidates_per_finding": MAX_REPAIR_CANDIDATES_PER_FINDING,
        "maximum_review_events_per_candidate": MAX_REPAIR_CANDIDATE_REVIEW_EVENTS,
        "maximum_private_label_chars": MAX_CANDIDATE_LABEL_CHARS,
        "maximum_private_reference_chars": MAX_CANDIDATE_REFERENCE_CHARS,
        "maximum_private_review_note_chars": MAX_CANDIDATE_REVIEW_NOTE_CHARS,
        "artifact_sha256_required": True,
        "finding_id_required": True,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "most_favorable_review_state": "acceptable_for_testing",
        "application_approval_state_exists": False,
        "release_decision": "operator_only",
    }
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_review_protocol",
        "schema_version": REPAIR_CANDIDATE_REVIEW_PROTOCOL_SCHEMA_VERSION,
        "protocol_status": "ready",
        **contract,
        "protocol_digest": _digest(contract),
        "candidate_generation": False,
        "automatic_registration": False,
        "automatic_test_execution": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_prioritization": False,
        "candidate_ranking": False,
        "winner_selection": False,
        "patch_generated": False,
        "patch_reviewed_automatically": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "provider_invoked": False,
        "generation_invoked": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def repair_candidate_review_protocol_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {"private_label", "private_reference", "private_note", "content", "text", "transcript", "prompt", "provider_payload", "credentials", "vectors", "hidden_reasoning", "chain_of_thought"}
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
