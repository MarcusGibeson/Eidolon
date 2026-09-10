from __future__ import annotations

"""v1090.6 provider-free state assembly for the repair-candidate console."""

from typing import Any, Iterable
import hashlib
import json

from conversation_evaluation_finding import EvaluationFindingError
from repair_candidate_comparison import build_repair_candidate_comparison
from repair_candidate_lineage import build_repair_candidate_lineage
from repair_candidate_long_session import build_repair_candidate_window
from repair_candidate_registration import build_repair_candidate_registrations
from repair_candidate_review import build_repair_candidate_review
from repair_candidate_review_protocol import build_repair_candidate_review_protocol
from repair_candidate_verification_evidence import build_repair_candidate_verification_evidence

REPAIR_CANDIDATE_CONSOLE_SCHEMA_VERSION = "1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_repair_candidate_console_state(
    *,
    finding_id: str = "",
    candidate_id: str = "",
    comparison_candidate_ids: Iterable[str] = (),
    candidate_kind: str = "",
    review_state: str = "",
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    finding_token = str(finding_id or "").strip()
    candidate_token = str(candidate_id or "").strip()
    protocol = build_repair_candidate_review_protocol()
    window = build_repair_candidate_window(
        finding_id=finding_token,
        candidate_kind=candidate_kind,
        review_state=review_state,
        offset=offset,
        limit=limit,
    )
    registrations = review = verification = lineage = comparison = None
    selection_status = "none_selected"
    if finding_token:
        try:
            registrations = build_repair_candidate_registrations(finding_token)
            lineage = build_repair_candidate_lineage(finding_token)
            if candidate_token:
                review = build_repair_candidate_review(finding_token, candidate_token)
                verification = build_repair_candidate_verification_evidence(finding_token, candidate_token)
                selection_status = "available"
            else:
                selection_status = "finding_selected"
        except EvaluationFindingError:
            selection_status = "not_found"
    comparison_ids = [str(item or "").strip() for item in comparison_candidate_ids if str(item or "").strip()]
    if finding_token and len(dict.fromkeys(comparison_ids)) >= 2:
        try:
            comparison = build_repair_candidate_comparison(finding_token, comparison_ids)
        except EvaluationFindingError:
            comparison = None
    stable = {
        "selection_status": selection_status,
        "selected_finding_id": finding_token if selection_status in {"finding_selected", "available"} else "",
        "selected_candidate_id": candidate_token if selection_status == "available" else "",
        "selected_finding_revision": max(0, int((registrations or {}).get("finding_revision") or 0)),
        "protocol_digest": str(protocol.get("protocol_digest") or ""),
        "window_digest": str(window.get("window_digest") or ""),
        "registrations_digest": str((registrations or {}).get("registrations_digest") or ""),
        "review_digest": str((review or {}).get("review_digest") or ""),
        "verification_evidence_digest": str((verification or {}).get("verification_evidence_digest") or ""),
        "lineage_digest": str((lineage or {}).get("lineage_digest") or ""),
        "comparison_digest": str((comparison or {}).get("comparison_digest") or ""),
    }
    return {
        "ok": True,
        "type": "desktop_alpha_operator_repair_candidate_console_state",
        "schema_version": REPAIR_CANDIDATE_CONSOLE_SCHEMA_VERSION,
        "selection_status": selection_status,
        "selected_finding_id": stable["selected_finding_id"],
        "selected_candidate_id": stable["selected_candidate_id"],
        "protocol": protocol,
        "candidate_window": window,
        "registrations": registrations,
        "review": review,
        "verification_evidence": verification,
        "lineage": lineage,
        "comparison": comparison,
        "console_digest": _digest(stable),
        "operator_confirmation_required_for_mutation": True,
        "optimistic_revision_required": True,
        "mutation_route": "/api/conversation/evaluation-finding",
        "read_routes_only_for_evidence": True,
        "private_labels_returned": False,
        "private_references_returned": False,
        "private_review_notes_returned": False,
        "private_verification_notes_returned": False,
        "private_lineage_notes_returned": False,
        "transcript_inspected": False,
        "prompt_inspected": False,
        "memory_inspected": False,
        "provider_invoked": False,
        "generation_invoked": False,
        "automatic_test_execution": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_prioritization": False,
        "candidate_ranked": False,
        "winner_selected": False,
        "patch_generated": False,
        "patch_reviewed_automatically": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }
