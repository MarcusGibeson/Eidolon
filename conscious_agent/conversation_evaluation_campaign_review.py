from __future__ import annotations

"""v1088.6 explicit operator campaign review workflow.

Review state and dispositions are stored inside the existing private campaign
record. Mutations require explicit confirmation, the exact optimistic revision,
and the established cross-process campaign lock. Public evidence contains only
bounded finding identifiers, dispositions, counts, states, and note digests.
No review action creates a task, assigns priority, calls a provider, or grants
release authority.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_daily_evaluation_protocol import EVALUATION_SIGNALS
from conversation_evaluation_campaign import (
    EvaluationCampaignError,
    _atomic_write,
    _campaign_path,
    _digest,
    _now_utc,
    _require_expected_revision,
    campaign_storage_lock,
    load_evaluation_campaign_private,
)
from conversation_evaluation_campaign_issues import build_evaluation_campaign_issue_aggregation
from conversation_evaluation_campaign_enrollment import build_evaluation_campaign_progress
from conversation_evaluation_outcomes import ISSUE_DOMAINS

EVALUATION_CAMPAIGN_REVIEW_SCHEMA_VERSION = "1"
CAMPAIGN_REVIEW_STATES = ("not_started", "in_review", "completed")
CAMPAIGN_REVIEW_DISPOSITIONS = ("acknowledged", "follow_up_required", "deferred", "dismissed")
CAMPAIGN_REVIEW_FINDING_KINDS = ("campaign_summary", "issue_domain", "required_signal")
MAX_CAMPAIGN_REVIEW_DISPOSITIONS = 48
MAX_CAMPAIGN_REVIEW_NOTE_CHARS = 2000


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _review_record(record: Mapping[str, Any]) -> dict[str, Any]:
    value = record.get("review") if isinstance(record.get("review"), Mapping) else {}
    rows = [dict(row) for row in list(value.get("dispositions") or ()) if isinstance(row, Mapping)]
    return {
        "state": str(value.get("state") or "not_started"),
        "started_at": str(value.get("started_at") or ""),
        "completed_at": str(value.get("completed_at") or ""),
        "reopened_at": str(value.get("reopened_at") or ""),
        "dispositions": rows,
    }


def _normalize_finding(record: Mapping[str, Any], finding_kind: str, finding_value: str) -> tuple[str, str]:
    kind = str(finding_kind or "").strip().lower()
    value = str(finding_value or "").strip().lower()
    if kind not in CAMPAIGN_REVIEW_FINDING_KINDS:
        raise EvaluationCampaignError("Unsupported campaign review finding kind.")
    if kind == "campaign_summary":
        if value not in {"", "overall"}:
            raise EvaluationCampaignError("Campaign summary review uses the fixed overall finding.")
        return kind, "overall"
    if kind == "issue_domain":
        if value not in ISSUE_DOMAINS or value == "none":
            raise EvaluationCampaignError("Unsupported campaign review issue domain.")
        return kind, value
    plan = record.get("plan") if isinstance(record.get("plan"), Mapping) else {}
    required = {str(item) for item in list(plan.get("required_signals") or ()) if str(item) in EVALUATION_SIGNALS}
    if value not in required:
        raise EvaluationCampaignError("The review signal is not required by this campaign.")
    return kind, value


def _normalize_disposition(disposition: str) -> str:
    token = str(disposition or "").strip().lower()
    if token not in CAMPAIGN_REVIEW_DISPOSITIONS:
        raise EvaluationCampaignError("Unsupported campaign review disposition.")
    return token


def _normalize_note(note: str) -> str:
    token = str(note or "").strip()
    if len(token) > MAX_CAMPAIGN_REVIEW_NOTE_CHARS:
        raise EvaluationCampaignError(
            f"Campaign review notes are limited to {MAX_CAMPAIGN_REVIEW_NOTE_CHARS} characters."
        )
    return token


def _finding_key(kind: str, value: str) -> str:
    return f"{kind}:{value}"


def _required_finding_rows(campaign_id: str) -> list[dict[str, str]]:
    issues = build_evaluation_campaign_issue_aggregation(campaign_id)
    progress = build_evaluation_campaign_progress(campaign_id)
    rows: list[dict[str, str]] = [{"finding_kind": "campaign_summary", "finding_value": "overall"}]
    domain_counts = issues.get("issue_domain_counts") if isinstance(issues.get("issue_domain_counts"), Mapping) else {}
    for domain in sorted(ISSUE_DOMAINS):
        if domain != "none" and int(domain_counts.get(domain) or 0) > 0:
            rows.append({"finding_kind": "issue_domain", "finding_value": domain})
    for signal in sorted(str(item) for item in list(progress.get("missing_required_signals") or ())):
        if signal in EVALUATION_SIGNALS:
            rows.append({"finding_kind": "required_signal", "finding_value": signal})
    return rows


def _public_disposition(row: Mapping[str, Any]) -> dict[str, Any]:
    note = str(row.get("private_note") or "")
    return {
        "finding_kind": str(row.get("finding_kind") or ""),
        "finding_value": str(row.get("finding_value") or ""),
        "disposition": str(row.get("disposition") or ""),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "private_note_present": bool(note),
        "private_note_digest": _digest(note) if note else "",
        "private_note_returned": False,
    }


def _build_review_summary(record: Mapping[str, Any], *, duplicate_disposition: bool = False) -> dict[str, Any]:
    review = _review_record(record)
    public_rows = [_public_disposition(row) for row in review["dispositions"]]
    required_rows = _required_finding_rows(str(record.get("campaign_id") or ""))
    disposed_keys = {
        _finding_key(str(row.get("finding_kind") or ""), str(row.get("finding_value") or ""))
        for row in public_rows
    }
    required_keys = {
        _finding_key(str(row.get("finding_kind") or ""), str(row.get("finding_value") or ""))
        for row in required_rows
    }
    missing = [row for row in required_rows if _finding_key(row["finding_kind"], row["finding_value"]) not in disposed_keys]
    counts = {value: 0 for value in CAMPAIGN_REVIEW_DISPOSITIONS}
    for row in public_rows:
        token = str(row.get("disposition") or "")
        if token in counts:
            counts[token] += 1
    stable = {
        "campaign_id": str(record.get("campaign_id") or ""),
        "campaign_revision": max(0, int(record.get("revision") or 0)),
        "campaign_state": str(record.get("state") or "planned"),
        "review_state": review["state"],
        "review_started_at": review["started_at"],
        "review_completed_at": review["completed_at"],
        "review_reopened_at": review["reopened_at"],
        "required_findings": required_rows,
        "required_finding_count": len(required_rows),
        "disposition_count": len(public_rows),
        "maximum_dispositions": MAX_CAMPAIGN_REVIEW_DISPOSITIONS,
        "disposition_counts": counts,
        "dispositions": public_rows,
        "missing_findings": missing,
        "missing_finding_count": len(missing),
        "review_completion_ready": review["state"] == "in_review" and not missing,
        "required_findings_digest": _stable_digest(required_rows),
    }
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_review",
        "schema_version": EVALUATION_CAMPAIGN_REVIEW_SCHEMA_VERSION,
        **stable,
        "review_digest": _stable_digest(stable),
        "duplicate_disposition": bool(duplicate_disposition),
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "private_notes_returned": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "priority_assigned": False,
        "autonomous_prioritization": False,
        "release_recommendation_produced": False,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "generation_invoked": False,
        "automatic_replay": False,
        "automatic_resend": False,
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


def build_evaluation_campaign_review(campaign_id: str) -> dict[str, Any]:
    return _build_review_summary(load_evaluation_campaign_private(campaign_id))


def start_evaluation_campaign_review(
    campaign_id: str, *, expected_revision: int | None, operator_confirmed: bool
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to start campaign review.")
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        if str(record.get("state") or "planned") == "aborted":
            raise EvaluationCampaignError("An aborted campaign cannot enter review.")
        review = _review_record(record)
        if review["state"] != "not_started":
            raise EvaluationCampaignError("Campaign review has already started.")
        now = _now_utc()
        review["state"] = "in_review"
        review["started_at"] = now
        record["review"] = review
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = now
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    return _build_review_summary(record)


def set_evaluation_campaign_review_disposition(
    campaign_id: str,
    *,
    finding_kind: str,
    finding_value: str,
    disposition: str,
    note: str = "",
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to set a review disposition.")
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        review = _review_record(record)
        if review["state"] != "in_review":
            raise EvaluationCampaignError("Campaign review must be in progress before recording dispositions.")
        kind, value = _normalize_finding(record, finding_kind, finding_value)
        disposition_token = _normalize_disposition(disposition)
        private_note = _normalize_note(note)
        rows = review["dispositions"]
        target = next(
            (
                row
                for row in rows
                if str(row.get("finding_kind") or "") == kind
                and str(row.get("finding_value") or "") == value
            ),
            None,
        )
        if target is not None:
            if (
                str(target.get("disposition") or "") == disposition_token
                and str(target.get("private_note") or "") == private_note
            ):
                return _build_review_summary(record, duplicate_disposition=True)
        elif len(rows) >= MAX_CAMPAIGN_REVIEW_DISPOSITIONS:
            raise EvaluationCampaignError(
                f"Campaign review is limited to {MAX_CAMPAIGN_REVIEW_DISPOSITIONS} dispositions."
            )
        now = _now_utc()
        if target is None:
            target = {
                "finding_kind": kind,
                "finding_value": value,
                "created_at": now,
            }
            rows.append(target)
        target["disposition"] = disposition_token
        target["private_note"] = private_note
        target["updated_at"] = now
        review["dispositions"] = rows
        record["review"] = review
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = now
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    return _build_review_summary(record)


def remove_evaluation_campaign_review_disposition(
    campaign_id: str,
    *,
    finding_kind: str,
    finding_value: str,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to remove a review disposition.")
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        review = _review_record(record)
        if review["state"] != "in_review":
            raise EvaluationCampaignError("Only an in-progress campaign review may remove dispositions.")
        kind, value = _normalize_finding(record, finding_kind, finding_value)
        rows = [
            row
            for row in review["dispositions"]
            if not (
                str(row.get("finding_kind") or "") == kind
                and str(row.get("finding_value") or "") == value
            )
        ]
        if len(rows) == len(review["dispositions"]):
            raise EvaluationCampaignError("Campaign review disposition not found.")
        now = _now_utc()
        review["dispositions"] = rows
        record["review"] = review
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = now
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    return _build_review_summary(record)


def complete_evaluation_campaign_review(
    campaign_id: str, *, expected_revision: int | None, operator_confirmed: bool
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to complete campaign review.")
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        summary = _build_review_summary(record)
        if summary["review_state"] != "in_review":
            raise EvaluationCampaignError("Only an in-progress campaign review may be completed.")
        if not summary["review_completion_ready"]:
            raise EvaluationCampaignError("All required campaign findings need an explicit disposition before review completion.")
        review = _review_record(record)
        now = _now_utc()
        review["state"] = "completed"
        review["completed_at"] = now
        record["review"] = review
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = now
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    return _build_review_summary(record)


def reopen_evaluation_campaign_review(
    campaign_id: str, *, expected_revision: int | None, operator_confirmed: bool
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to reopen campaign review.")
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        review = _review_record(record)
        if review["state"] != "completed":
            raise EvaluationCampaignError("Only a completed campaign review may be reopened.")
        now = _now_utc()
        review["state"] = "in_review"
        review["completed_at"] = ""
        review["reopened_at"] = now
        record["review"] = review
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = now
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    return _build_review_summary(record)


def campaign_review_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_note", "campaign_label", "objective", "private_reference_value", "content", "text",
        "message", "messages", "user_message", "assistant_response", "transcript", "prompt", "note",
        "notes", "temporary_instruction", "pinned_context", "queued_operator_intent", "provider_payload",
        "credentials", "vectors", "embedding", "receipt", "receipts", "hidden_reasoning", "chain_of_thought",
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
