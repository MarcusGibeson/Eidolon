from __future__ import annotations
"""v1377 content-free conflict detection and reconciliation planning for durable campaigns.

The contract is deliberately conservative: it can detect drift before a campaign
result is applied and can prepare a reconciliation disposition, but it never
mutates a project, rebases a worktree, consumes approval, or grants apply authority.
"""

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1377.8"
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,120}$")
ORIGINS = {"campaign", "operator", "upstream", "other_session", "unknown"}
KINDS = {"added", "modified", "deleted", "renamed", "metadata"}
DISPOSITIONS = {"preserve_current", "rebuild_candidate", "reconcile_manually", "defer", "discard_candidate"}
DENIED = {
    "application_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "worktree_mutation_authorized": False,
    "rebase_authorized": False,
    "approval_granted": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}


def _d(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _valid_digest(value: object) -> bool:
    return bool(DIGEST_RE.fullmatch(str(value or "")))


def assess_campaign_conflicts(
    *,
    campaign_record_digest: str,
    candidate_digest: str,
    baseline_source_digest: str,
    current_source_digest: str,
    baseline_workspace_digest: str,
    current_workspace_digest: str,
    expected_upstream_digest: str,
    current_upstream_digest: str,
    owner_session_digest: str,
    active_session_digests: Sequence[str] = (),
    observed_changes: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a deterministic, content-free pre-apply conflict assessment.

    ``observed_changes`` rows carry only digests and classifications, never raw
    paths or file content. A row may contain: ``path_digest``, ``change_digest``,
    ``origin`` and ``kind``. Campaign-owned changes do not themselves constitute
    a conflict; operator/upstream/other-session/unknown changes do.
    """

    digests = (
        campaign_record_digest,
        candidate_digest,
        baseline_source_digest,
        current_source_digest,
        baseline_workspace_digest,
        current_workspace_digest,
        expected_upstream_digest,
        current_upstream_digest,
        owner_session_digest,
    )
    if any(not _valid_digest(x) for x in digests):
        return {"ok": False, "status": "conflict_lineage_invalid", "action_executed": False, **DENIED}
    sessions = [str(x) for x in active_session_digests]
    if len(sessions) > 64 or any(not _valid_digest(x) for x in sessions):
        return {"ok": False, "status": "active_session_set_invalid", "action_executed": False, **DENIED}
    sessions = sorted(set(sessions))

    normalized: list[dict[str, str]] = []
    for raw in observed_changes:
        path_digest = str(raw.get("path_digest") or "")
        change_digest = str(raw.get("change_digest") or "")
        origin = str(raw.get("origin") or "unknown")
        kind = str(raw.get("kind") or "modified")
        if not _valid_digest(path_digest) or not _valid_digest(change_digest) or origin not in ORIGINS or kind not in KINDS:
            return {"ok": False, "status": "observed_change_invalid", "action_executed": False, **DENIED}
        normalized.append({"path_digest": path_digest, "change_digest": change_digest, "origin": origin, "kind": kind})
    if len(normalized) > 4096:
        return {"ok": False, "status": "observed_change_set_too_large", "action_executed": False, **DENIED}

    operator_rows = [r for r in normalized if r["origin"] == "operator"]
    upstream_rows = [r for r in normalized if r["origin"] == "upstream"]
    competing_rows = [r for r in normalized if r["origin"] == "other_session"]
    unknown_rows = [r for r in normalized if r["origin"] == "unknown"]
    campaign_rows = [r for r in normalized if r["origin"] == "campaign"]
    competing_sessions = [s for s in sessions if s != owner_session_digest]

    source_drift = current_source_digest != baseline_source_digest
    workspace_drift = current_workspace_digest != baseline_workspace_digest
    upstream_drift = current_upstream_digest != expected_upstream_digest
    operator_edit_detected = bool(operator_rows)
    competing_session_detected = bool(competing_rows or competing_sessions)
    unknown_change_detected = bool(unknown_rows)
    stale_worktree_detected = workspace_drift and not normalized

    reasons: list[str] = []
    if operator_edit_detected:
        reasons.append("operator_edits_detected")
    if upstream_drift or upstream_rows:
        reasons.append("upstream_changes_detected")
    if stale_worktree_detected:
        reasons.append("unexplained_worktree_drift")
    if competing_session_detected:
        reasons.append("competing_session_detected")
    if unknown_change_detected:
        reasons.append("unknown_change_origin")
    if source_drift and not normalized:
        reasons.append("source_digest_drift_unexplained")
    if source_drift and normalized and not campaign_rows and "source_digest_drift_unexplained" not in reasons:
        reasons.append("source_changed_outside_campaign")

    conflict_detected = bool(reasons)
    assessment = {
        "contract_version": CONTRACT_VERSION,
        "campaign_record_digest": campaign_record_digest,
        "candidate_digest": candidate_digest,
        "baseline_source_digest": baseline_source_digest,
        "current_source_digest": current_source_digest,
        "baseline_workspace_digest": baseline_workspace_digest,
        "current_workspace_digest": current_workspace_digest,
        "expected_upstream_digest": expected_upstream_digest,
        "current_upstream_digest": current_upstream_digest,
        "owner_session_digest": owner_session_digest,
        "active_session_set_digest": _d(sessions),
        "active_session_count": len(sessions),
        "competing_session_count": len(competing_sessions),
        "observed_change_set_digest": _d(sorted(normalized, key=lambda r: (r["path_digest"], r["change_digest"], r["origin"], r["kind"]))),
        "observed_change_count": len(normalized),
        "campaign_owned_change_count": len(campaign_rows),
        "operator_change_count": len(operator_rows),
        "upstream_change_count": len(upstream_rows),
        "competing_session_change_count": len(competing_rows),
        "unknown_change_count": len(unknown_rows),
        "source_drift_detected": source_drift,
        "workspace_drift_detected": workspace_drift,
        "upstream_drift_detected": upstream_drift,
        "operator_edit_detected": operator_edit_detected,
        "stale_worktree_detected": stale_worktree_detected,
        "competing_session_detected": competing_session_detected,
        "unknown_change_detected": unknown_change_detected,
        "conflict_detected": conflict_detected,
        "apply_guard": "blocked_reconciliation_required" if conflict_detected else "clear_no_conflict_observed",
        "conflict_reason_codes": reasons,
        "raw_paths_persisted": False,
        "raw_content_persisted": False,
        "content_free": True,
        "read_only": True,
        "action_executed": False,
        **DENIED,
    }
    assessment["assessment_digest"] = _d(assessment)
    return {"ok": True, "status": "campaign_conflicts_assessed", "conflict_assessment": assessment, "action_executed": False, **DENIED}


def prepare_reconciliation_disposition(
    *,
    conflict_assessment: Mapping[str, Any],
    expected_assessment_digest: str,
    disposition: str,
    operator_reviewed: bool,
) -> dict[str, Any]:
    """Prepare a non-executing reconciliation decision bound to exact evidence."""

    supplied = str(conflict_assessment.get("assessment_digest") or "")
    base = dict(conflict_assessment)
    base.pop("assessment_digest", None)
    if not _valid_digest(expected_assessment_digest) or supplied != expected_assessment_digest or supplied != _d(base):
        return {"ok": False, "status": "conflict_assessment_stale_or_tampered", "action_executed": False, **DENIED}
    if disposition not in DISPOSITIONS:
        return {"ok": False, "status": "reconciliation_disposition_invalid", "action_executed": False, **DENIED}
    if not operator_reviewed:
        return {"ok": False, "status": "operator_review_required", "action_executed": False, **DENIED}
    if not conflict_assessment.get("conflict_detected") and disposition in {"reconcile_manually", "discard_candidate"}:
        return {"ok": False, "status": "reconciliation_not_required", "action_executed": False, **DENIED}

    row = {
        "contract_version": CONTRACT_VERSION,
        "assessment_digest": supplied,
        "campaign_record_digest": str(conflict_assessment.get("campaign_record_digest") or ""),
        "candidate_digest": str(conflict_assessment.get("candidate_digest") or ""),
        "disposition": disposition,
        "operator_reviewed": True,
        "execution_required": disposition not in {"defer", "discard_candidate"},
        "safe_to_apply_original_candidate": bool(not conflict_assessment.get("conflict_detected") and disposition == "preserve_current"),
        "candidate_requires_rebuild": disposition == "rebuild_candidate",
        "manual_reconciliation_required": disposition == "reconcile_manually",
        "candidate_discard_recommended": disposition == "discard_candidate",
        "content_free": True,
        "read_only": True,
        "action_executed": False,
        **DENIED,
    }
    row["disposition_digest"] = _d(row)
    return {"ok": True, "status": "reconciliation_disposition_prepared", "reconciliation": row, "action_executed": False, **DENIED}


def process_conflict_reconciliation_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {
        "show campaign conflicts",
        "inspect campaign conflicts",
        "show conflict reconciliation",
    }:
        return {"active": False}
    rec = dict((project_state or {}).get("conflict_reconciliation") or {})
    return {
        "active": True,
        "ok": bool(rec),
        "status": "conflict_reconciliation_found" if rec else "conflict_reconciliation_missing",
        "conflict_reconciliation": rec,
        "action_executed": False,
        **DENIED,
    }


__all__ = [
    "CONTRACT_VERSION",
    "DENIED",
    "assess_campaign_conflicts",
    "prepare_reconciliation_disposition",
    "process_conflict_reconciliation_control",
]
