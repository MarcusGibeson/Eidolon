from __future__ import annotations

"""v1089.6 provider-free state assembly for the operator findings console."""

from typing import Any, Iterable
import hashlib
import json

from conversation_evaluation_finding import EvaluationFindingError, load_evaluation_finding
from conversation_evaluation_finding_aggregation import build_evaluation_finding_aggregation
from conversation_evaluation_finding_comparison import build_evaluation_finding_comparison
from conversation_evaluation_finding_long_session import build_evaluation_finding_window
from conversation_evaluation_finding_repair_candidates import build_finding_repair_candidates
from conversation_evaluation_finding_reproducibility import build_finding_reproducibility
from conversation_evaluation_finding_triage import build_evaluation_finding_triage

EVALUATION_FINDING_CONSOLE_SCHEMA_VERSION = "1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_evaluation_finding_console_state(
    *,
    finding_id: str = "",
    campaign_id: str = "",
    evaluation_id: str = "",
    state: str = "",
    comparison_finding_ids: Iterable[str] = (),
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    token = str(finding_id or "").strip()
    window = build_evaluation_finding_window(
        campaign_id=campaign_id,
        evaluation_id=evaluation_id,
        state=state,
        offset=offset,
        limit=limit,
    )
    aggregation = build_evaluation_finding_aggregation(
        campaign_id=str(campaign_id or "").strip(),
        evaluation_id=str(evaluation_id or "").strip(),
    )
    selected = reproducibility = repair_candidates = triage = comparison = None
    selection_status = "none_selected"
    if token:
        try:
            selected = load_evaluation_finding(token)
            reproducibility = build_finding_reproducibility(token)
            repair_candidates = build_finding_repair_candidates(token)
            triage = build_evaluation_finding_triage(token)
            selection_status = "available"
        except EvaluationFindingError:
            selection_status = "not_found"
    comparison_ids = [str(item or "").strip() for item in comparison_finding_ids if str(item or "").strip()]
    if len(dict.fromkeys(comparison_ids)) >= 2:
        try:
            comparison = build_evaluation_finding_comparison(comparison_ids)
        except EvaluationFindingError:
            comparison = None
    stable = {
        "selection_status": selection_status,
        "selected_finding_id": token if selection_status == "available" else "",
        "selected_finding_revision": int((selected or {}).get("revision") or 0),
        "window_digest": str(window.get("window_digest") or ""),
        "aggregation_digest": str(aggregation.get("aggregation_digest") or ""),
        "reproducibility_digest": str((reproducibility or {}).get("attempts_digest") or ""),
        "repair_references_digest": str((repair_candidates or {}).get("references_digest") or ""),
        "triage_digest": str((triage or {}).get("triage_digest") or ""),
        "comparison_digest": str((comparison or {}).get("comparison_digest") or ""),
    }
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_findings_console_state",
        "schema_version": EVALUATION_FINDING_CONSOLE_SCHEMA_VERSION,
        "selection_status": selection_status,
        "selected_finding_id": stable["selected_finding_id"],
        "selected_finding": selected,
        "reproducibility": reproducibility,
        "repair_candidates": repair_candidates,
        "triage": triage,
        "aggregation": aggregation,
        "comparison": comparison,
        "finding_window": window,
        "console_digest": _digest(stable),
        "operator_confirmation_required_for_mutation": True,
        "optimistic_revision_required": True,
        "mutation_route": "/api/conversation/evaluation-finding",
        "read_routes_only_for_evidence": True,
        "private_finding_content_returned": False,
        "private_reproduction_notes_returned": False,
        "private_environment_labels_returned": False,
        "private_repair_reference_values_returned": False,
        "private_triage_notes_returned": False,
        "transcript_inspected": False,
        "prompt_inspected": False,
        "memory_inspected": False,
        "provider_invoked": False,
        "generation_invoked": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_prioritization": False,
        "patch_generated": False,
        "patch_reviewed": False,
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
