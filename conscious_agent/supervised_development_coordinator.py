from __future__ import annotations

"""Durable product coordinator for the v1490-v1500 supervised developer chain."""

import re
from pathlib import Path
from typing import Any, Mapping

from continuous_development_campaign import apply_campaign_event, campaign_public_projection, new_campaign
from development_authority import is_hex64
from dynamic_development_backlog import DynamicDevelopmentBacklog
from dynamic_implementation_planning import build_evidence_bound_plan
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock


CONTRACT_VERSION = "v1500.0.1"
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,160}")


def _campaign_path(runtime_root: str | Path, candidate_id: str) -> Path:
    cid = str(candidate_id or "")
    if not _ID.fullmatch(cid):
        raise ValueError("development_campaign_candidate_id_invalid")
    return Path(runtime_root).expanduser().resolve() / "development" / "campaigns" / f"{cid}.json"


def _save_campaign(path: Path, state: Mapping[str, Any]) -> None:
    with metadata_mutation_lock(path, timeout_seconds=5):
        write_json_atomic(path, dict(state), expected_type=dict, sort_keys=True, coordinate=False)


def _load_campaign(path: Path) -> dict[str, Any]:
    return load_json_file(path, {}, expected_type=dict)


def start_selected_campaign(
    runtime_root: str | Path,
    *,
    event_id: str,
    comparison: Mapping[str, Any],
    candidate: Mapping[str, Any],
    baseline_source_digest: str,
    operator_selection_receipt: Mapping[str, Any],
    available_test_files: tuple[str, ...] = (),
) -> dict[str, Any]:
    cid = str(candidate.get("candidate_id") or "")
    evidence_digest = str(candidate.get("eligibility_digest") or candidate.get("evidence_digest") or "")
    if not _ID.fullmatch(cid) or not is_hex64(evidence_digest) or not is_hex64(baseline_source_digest):
        return {"ok": False, "status": "campaign_identity_or_evidence_invalid", "content_free": True}
    backlog = DynamicDevelopmentBacklog(runtime_root)
    ingestion = backlog.ingest_comparison(f"{event_id}:comparison", comparison)
    selection = backlog.transition(
        f"{event_id}:selection",
        cid,
        "operator_selected",
        evidence_digest=evidence_digest,
        operator_authorization_receipt=operator_selection_receipt,
    )
    if selection.get("status") != "backlog_transitioned":
        return {"ok": False, "status": "campaign_selection_blocked", "selection": selection, "content_free": True}
    plan = build_evidence_bound_plan(
        candidate,
        operator_selection_receipt=operator_selection_receipt,
        available_test_files=available_test_files,
    )
    if not plan.get("plan_created") or not is_hex64(plan.get("plan_digest")):
        return {"ok": False, "status": "campaign_plan_blocked", "content_free": True}
    planned = backlog.transition(f"{event_id}:plan", cid, "planned", evidence_digest=str(plan["plan_digest"]))
    campaign = new_campaign(campaign_id=f"campaign-{cid}", candidate_id=cid, baseline_source_digest=baseline_source_digest)
    for event in (
        {"event_id": f"{event_id}:campaign-comparison", "action": "record_comparison", "current_source_digest": baseline_source_digest, "evidence_digest": str(comparison.get("comparison_digest") or "")},
        {"event_id": f"{event_id}:campaign-selection", "action": "operator_select", "current_source_digest": baseline_source_digest, "evidence_digest": evidence_digest, "operator_authorization_receipt": dict(operator_selection_receipt)},
        {"event_id": f"{event_id}:campaign-plan", "action": "record_plan", "current_source_digest": baseline_source_digest, "evidence_digest": str(plan["plan_digest"])},
    ):
        transition = apply_campaign_event(campaign, event)
        if not transition.get("accepted"):
            return {"ok": False, "status": "campaign_state_transition_blocked", "reason": transition.get("reason"), "content_free": True}
        campaign = transition["state"]
    path = _campaign_path(runtime_root, cid)
    _save_campaign(path, campaign)
    return {
        "ok": planned.get("status") == "backlog_transitioned",
        "status": "campaign_planned",
        "candidate_id": cid,
        "plan": plan,
        "backlog_ingestion": ingestion,
        "campaign": campaign_public_projection(campaign),
        "content_free": True,
    }


def record_workspace_prepared(
    runtime_root: str | Path,
    *,
    event_id: str,
    candidate_id: str,
    plan_digest: str,
    workspace_manifest_digest: str,
    operator_authorization_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if not is_hex64(plan_digest) or not is_hex64(workspace_manifest_digest):
        return {"ok": False, "status": "workspace_evidence_invalid", "content_free": True}
    backlog = DynamicDevelopmentBacklog(runtime_root)
    transition = backlog.transition(
        f"{event_id}:workspace",
        candidate_id,
        "workspace_authorized",
        evidence_digest=workspace_manifest_digest,
        authority_digest=plan_digest,
        operator_authorization_receipt=operator_authorization_receipt,
    )
    path = _campaign_path(runtime_root, candidate_id)
    campaign = _load_campaign(path)
    result = apply_campaign_event(campaign, {
        "event_id": f"{event_id}:campaign-workspace",
        "action": "authorize_workspace",
        "current_source_digest": campaign.get("baseline_source_digest"),
        "evidence_digest": workspace_manifest_digest,
        "authority_digest": plan_digest,
        "operator_authorization_receipt": dict(operator_authorization_receipt),
    })
    if transition.get("status") != "backlog_transitioned" or not result.get("accepted"):
        return {"ok": False, "status": "workspace_campaign_transition_blocked", "content_free": True}
    _save_campaign(path, result["state"])
    return {"ok": True, "status": "workspace_recorded", "campaign": campaign_public_projection(result["state"]), "content_free": True}


def record_review_ready(
    runtime_root: str | Path,
    *,
    event_id: str,
    candidate_id: str,
    implementation_digest: str,
    verification_digest: str,
    review_digest: str,
) -> dict[str, Any]:
    evidence = (implementation_digest, verification_digest, review_digest)
    if not all(is_hex64(value) for value in evidence):
        return {"ok": False, "status": "review_evidence_invalid", "content_free": True}
    backlog = DynamicDevelopmentBacklog(runtime_root)
    path = _campaign_path(runtime_root, candidate_id)
    campaign = _load_campaign(path)
    stages = (
        ("implemented", implementation_digest, "record_implementation"),
        ("verified", verification_digest, "record_verification"),
        ("review_ready", review_digest, "record_review"),
    )
    for index, (state, evidence_digest, action) in enumerate(stages, 1):
        transitioned = backlog.transition(f"{event_id}:{state}", candidate_id, state, evidence_digest=evidence_digest)
        campaign_result = apply_campaign_event(campaign, {"event_id": f"{event_id}:campaign-{state}", "action": action, "current_source_digest": campaign.get("baseline_source_digest"), "evidence_digest": evidence_digest})
        if transitioned.get("status") != "backlog_transitioned" or not campaign_result.get("accepted"):
            return {"ok": False, "status": f"review_stage_{index}_blocked", "content_free": True}
        campaign = campaign_result["state"]
    _save_campaign(path, campaign)
    return {"ok": True, "status": "campaign_review_ready", "campaign": campaign_public_projection(campaign), "content_free": True}


def campaign_status(runtime_root: str | Path, candidate_id: str) -> dict[str, Any]:
    state = _load_campaign(_campaign_path(runtime_root, candidate_id))
    return campaign_public_projection(state) if state else {"candidate_id": candidate_id, "stage": "missing", "content_free": True}


__all__ = ["CONTRACT_VERSION", "campaign_status", "record_review_ready", "record_workspace_prepared", "start_selected_campaign"]
