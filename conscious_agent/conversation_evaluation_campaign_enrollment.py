from __future__ import annotations

"""v1088.2 explicit evaluation enrollment and campaign progress evidence.

Existing daily evaluations may be enrolled only through an explicit confirmed
mutation with an optimistic campaign revision. Enrollment creates no evaluation,
sends no provider request, and executes no retry/replay/resend. Public progress
uses only redacted daily-evaluation summaries and bounded labels/counts/digests.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_daily_evaluation import DailyEvaluationError, load_daily_evaluation
from conversation_daily_evaluation_protocol import EVALUATION_SIGNALS
from conversation_evaluation_campaign import (
    EvaluationCampaignError,
    _atomic_write,
    _campaign_path,
    _digest,
    _now_utc,
    _require_expected_revision,
    campaign_public_summary,
    campaign_storage_lock,
    iter_evaluation_campaign_private,
    load_evaluation_campaign_private,
)
from conversation_evaluation_campaign_protocol import MAX_CAMPAIGN_EVALUATIONS
from conversation_evaluation_outcomes import OUTCOME_CLASSES

EVALUATION_CAMPAIGN_ENROLLMENT_SCHEMA_VERSION = "1"


def _summary_digest(summary: Mapping[str, Any]) -> str:
    bounded = {
        "evaluation_id": str(summary.get("evaluation_id") or ""),
        "session_id": str(summary.get("session_id") or ""),
        "state": str(summary.get("state") or "unknown"),
        "revision": max(0, int(summary.get("revision") or 0)),
        "observation_count": max(0, int(summary.get("observation_count") or 0)),
        "outcome": str((summary.get("outcome") or {}).get("outcome") or "unclassified")
        if isinstance(summary.get("outcome"), Mapping)
        else "unclassified",
        "evidence_digest": str(summary.get("observation_evidence_digest") or ""),
    }
    return hashlib.sha256(
        json.dumps(bounded, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _load_daily_summary(evaluation_id: str) -> dict[str, Any]:
    try:
        return load_daily_evaluation(evaluation_id)
    except DailyEvaluationError as error:
        raise EvaluationCampaignError("Daily evaluation not found for campaign enrollment.") from error


def _evaluation_signals(summary: Mapping[str, Any]) -> set[str]:
    signals: set[str] = set()
    for row in list(summary.get("observations") or ()):
        if not isinstance(row, Mapping):
            continue
        for raw in list(row.get("signals") or ()):
            token = str(raw or "")
            if token in EVALUATION_SIGNALS:
                signals.add(token)
    return signals


def _build_progress_from_record(record: Mapping[str, Any]) -> dict[str, Any]:
    plan = record.get("plan") if isinstance(record.get("plan"), Mapping) else {}
    refs = [row for row in list(record.get("evaluation_refs") or ()) if isinstance(row, Mapping)]
    states = {"active": 0, "completed": 0, "aborted": 0, "missing": 0}
    outcomes = {name: 0 for name in OUTCOME_CLASSES}
    outcomes["unclassified"] = 0
    observed_signals: set[str] = set()
    current_rows: list[dict[str, Any]] = []
    for ref in refs:
        evaluation_id = str(ref.get("evaluation_id") or "")
        try:
            summary = load_daily_evaluation(evaluation_id)
        except DailyEvaluationError:
            states["missing"] += 1
            current_rows.append({
                "evaluation_id": evaluation_id,
                "session_id": str(ref.get("session_id") or ""),
                "state": "missing",
                "revision": 0,
                "observation_count": 0,
                "outcome": "unclassified",
                "summary_digest": str(ref.get("summary_digest") or ""),
            })
            outcomes["unclassified"] += 1
            continue
        state = str(summary.get("state") or "active")
        states[state if state in states else "active"] += 1
        outcome_record = summary.get("outcome") if isinstance(summary.get("outcome"), Mapping) else {}
        outcome = str(outcome_record.get("outcome") or outcome_record.get("outcome_code") or "unclassified")
        outcomes[outcome if outcome in outcomes else "unclassified"] += 1
        observed_signals.update(_evaluation_signals(summary))
        current_rows.append({
            "evaluation_id": evaluation_id,
            "session_id": str(summary.get("session_id") or ref.get("session_id") or ""),
            "state": state,
            "revision": max(0, int(summary.get("revision") or 0)),
            "observation_count": max(0, int(summary.get("observation_count") or 0)),
            "outcome": outcome,
            "summary_digest": _summary_digest(summary),
        })
    required_signals = [str(item) for item in list(plan.get("required_signals") or ()) if str(item) in EVALUATION_SIGNALS]
    covered_required = [signal for signal in required_signals if signal in observed_signals]
    missing_required = [signal for signal in required_signals if signal not in observed_signals]
    minimum_completed = max(1, int(plan.get("minimum_completed_evaluations") or 1))
    target_count = max(1, int(plan.get("target_evaluation_count") or 1))
    completion_ready = states["completed"] >= minimum_completed and not missing_required
    progress_contract = {
        "campaign_id": str(record.get("campaign_id") or ""),
        "campaign_revision": max(0, int(record.get("revision") or 0)),
        "campaign_state": str(record.get("state") or "planned"),
        "enrollment_count": len(refs),
        "state_counts": states,
        "outcome_counts": outcomes,
        "target_evaluation_count": target_count,
        "minimum_completed_evaluations": minimum_completed,
        "required_signals": required_signals,
        "covered_required_signals": covered_required,
        "missing_required_signals": missing_required,
        "completion_ready": completion_ready,
        "current_evaluations": current_rows,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_progress",
        "schema_version": EVALUATION_CAMPAIGN_ENROLLMENT_SCHEMA_VERSION,
        **progress_contract,
        "target_reached": states["completed"] >= target_count,
        "minimum_completed_reached": states["completed"] >= minimum_completed,
        "required_signal_coverage_complete": not missing_required,
        "observed_signals": sorted(observed_signals),
        "progress_digest": _digest(progress_contract),
        "operator_completion_required": True,
        "automatic_campaign_completion": False,
        "automatic_evaluation_creation": False,
        "automatic_evaluation_enrollment": False,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "generation_invoked": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "autonomous_scoring": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_certified": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def build_evaluation_campaign_progress(campaign_id: str) -> dict[str, Any]:
    return _build_progress_from_record(load_evaluation_campaign_private(campaign_id))


def _ensure_not_enrolled_elsewhere(campaign_id: str, evaluation_id: str) -> None:
    for other in iter_evaluation_campaign_private():
        if str(other.get("campaign_id") or "") == campaign_id:
            continue
        if str(other.get("state") or "planned") == "aborted":
            continue
        for row in list(other.get("evaluation_refs") or ()):
            if isinstance(row, Mapping) and str(row.get("evaluation_id") or "") == evaluation_id:
                raise EvaluationCampaignError("This daily evaluation is already enrolled in another open campaign.")


def enroll_daily_evaluation(
    campaign_id: str,
    evaluation_id: str,
    *,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to enroll an evaluation.")
    summary = _load_daily_summary(evaluation_id)
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        if str(record.get("state") or "planned") not in {"planned", "active"}:
            raise EvaluationCampaignError("Only a planned or active campaign may enroll evaluations.")
        refs = [row for row in list(record.get("evaluation_refs") or ()) if isinstance(row, Mapping)]
        for row in refs:
            if str(row.get("evaluation_id") or "") == str(summary.get("evaluation_id") or ""):
                payload = campaign_public_summary(record)
                payload["duplicate_enrollment"] = True
                payload["progress"] = _build_progress_from_record(record)
                return payload
        plan = record.get("plan") if isinstance(record.get("plan"), Mapping) else {}
        target = max(1, int(plan.get("target_evaluation_count") or 1))
        if len(refs) >= min(MAX_CAMPAIGN_EVALUATIONS, target):
            raise EvaluationCampaignError("The campaign target enrollment count has been reached.")
        token = str(summary.get("evaluation_id") or "")
        _ensure_not_enrolled_elsewhere(str(record.get("campaign_id") or ""), token)
        refs.append({
            "evaluation_id": token,
            "session_id": str(summary.get("session_id") or ""),
            "enrolled_at": _now_utc(),
            "evaluation_state_at_enrollment": str(summary.get("state") or "active"),
            "evaluation_revision_at_enrollment": max(0, int(summary.get("revision") or 0)),
            "summary_digest": _summary_digest(summary),
        })
        record["evaluation_refs"] = refs
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = _now_utc()
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    payload = campaign_public_summary(record)
    payload["duplicate_enrollment"] = False
    payload["progress"] = _build_progress_from_record(record)
    return payload


def unenroll_daily_evaluation(
    campaign_id: str,
    evaluation_id: str,
    *,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to remove an evaluation.")
    token = str(evaluation_id or "").strip()
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        if str(record.get("state") or "planned") not in {"planned", "active"}:
            raise EvaluationCampaignError("Only a planned or active campaign may remove evaluations.")
        refs = [row for row in list(record.get("evaluation_refs") or ()) if isinstance(row, Mapping)]
        filtered = [row for row in refs if str(row.get("evaluation_id") or "") != token]
        if len(filtered) == len(refs):
            raise EvaluationCampaignError("The daily evaluation is not enrolled in this campaign.")
        record["evaluation_refs"] = filtered
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = _now_utc()
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    payload = campaign_public_summary(record)
    payload["progress"] = _build_progress_from_record(record)
    return payload


def complete_evaluation_campaign(
    campaign_id: str,
    *,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to complete a campaign.")
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        if str(record.get("state") or "planned") != "active":
            raise EvaluationCampaignError("Only an active campaign may be completed.")
        progress = _build_progress_from_record(record)
        if not progress.get("completion_ready"):
            raise EvaluationCampaignError(
                "Campaign completion requirements are not met: review completed evaluations and required signals."
            )
        record["state"] = "completed"
        record["completed_at"] = _now_utc()
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = _now_utc()
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    payload = campaign_public_summary(record)
    payload["progress"] = _build_progress_from_record(record)
    return payload


def evaluation_campaign_progress_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "campaign_label", "objective", "content", "text", "message", "messages",
        "user_message", "assistant_response", "transcript", "prompt", "note", "notes",
        "temporary_instruction", "pinned_context", "queued_operator_intent", "provider_payload",
        "credentials", "vectors", "embedding", "receipt", "receipts", "hidden_reasoning",
        "chain_of_thought",
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
