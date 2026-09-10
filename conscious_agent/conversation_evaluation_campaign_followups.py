from __future__ import annotations

"""Explicit v1088.4 follow-up references for operator evaluation campaigns.

References are stored inside the existing private campaign record. Mutations
require explicit confirmation and the exact campaign revision. External tokens
remain private runtime data and public summaries expose only digests. No task,
work item, priority, provider request, approval, or release action is created.
"""

from datetime import datetime, timezone
from typing import Any, Mapping
import hashlib
import json
import re
import uuid

from conversation_daily_evaluation_protocol import ISSUE_DOMAINS
from conversation_evaluation_campaign import (
    EvaluationCampaignError,
    campaign_storage_lock,
    load_evaluation_campaign_private,
    _atomic_write,
    _campaign_path,
    _require_expected_revision,
)

EVALUATION_CAMPAIGN_FOLLOW_UP_SCHEMA_VERSION = "1"
FOLLOW_UP_REFERENCE_KINDS = (
    "evaluation",
    "reproduction_packet",
    "issue_domain",
    "external_work_item",
)
FOLLOW_UP_STATES = ("open", "resolved", "dismissed")
MAX_CAMPAIGN_FOLLOW_UPS = 64
MAX_EXTERNAL_REFERENCE_CHARS = 240
_FOLLOW_UP_ID_PATTERN = re.compile(r"^campaign_followup_[a-f0-9]{16}$")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _new_follow_up_id() -> str:
    return f"campaign_followup_{uuid.uuid4().hex[:16]}"


def _validate_follow_up_id(value: str) -> str:
    token = str(value or "").strip()
    if not _FOLLOW_UP_ID_PATTERN.fullmatch(token):
        raise EvaluationCampaignError("Invalid campaign follow-up identifier.")
    return token


def _normalize_reference(record: Mapping[str, Any], reference_kind: str, reference_value: str) -> dict[str, Any]:
    kind = str(reference_kind or "").strip().lower()
    if kind not in FOLLOW_UP_REFERENCE_KINDS:
        raise EvaluationCampaignError("Unsupported campaign follow-up reference kind.")
    token = str(reference_value or "").strip()
    if not token:
        raise EvaluationCampaignError("A follow-up reference value is required.")
    refs = [row for row in list(record.get("evaluation_refs") or ()) if isinstance(row, Mapping)]
    enrolled = {str(row.get("evaluation_id") or "") for row in refs}
    if kind in {"evaluation", "reproduction_packet"}:
        if token not in enrolled:
            raise EvaluationCampaignError("The referenced evaluation is not enrolled in this campaign.")
        return {"reference_kind": kind, "private_reference_value": token, "evaluation_id": token}
    if kind == "issue_domain":
        domain = token.lower()
        if domain not in ISSUE_DOMAINS or domain == "none":
            raise EvaluationCampaignError("The follow-up issue domain is unsupported.")
        return {"reference_kind": kind, "private_reference_value": domain, "issue_domain": domain}
    if len(token) > MAX_EXTERNAL_REFERENCE_CHARS:
        raise EvaluationCampaignError(
            f"External follow-up references are limited to {MAX_EXTERNAL_REFERENCE_CHARS} characters."
        )
    return {"reference_kind": kind, "private_reference_value": token}


def _public_row(row: Mapping[str, Any]) -> dict[str, Any]:
    private_value = str(row.get("private_reference_value") or "")
    kind = str(row.get("reference_kind") or "")
    public = {
        "follow_up_id": str(row.get("follow_up_id") or ""),
        "reference_kind": kind,
        "state": str(row.get("state") or "open"),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "resolved_at": str(row.get("resolved_at") or ""),
        "dismissed_at": str(row.get("dismissed_at") or ""),
        "reference_present": bool(private_value),
        "reference_digest": _digest(private_value) if private_value else "",
        "private_reference_returned": False,
    }
    if kind in {"evaluation", "reproduction_packet"}:
        public["evaluation_id"] = str(row.get("evaluation_id") or private_value)
    elif kind == "issue_domain":
        public["issue_domain"] = str(row.get("issue_domain") or private_value)
    return public


def _build_summary_from_record(record: Mapping[str, Any], *, duplicate_reference: bool = False) -> dict[str, Any]:
    rows = [row for row in list(record.get("follow_up_refs") or ()) if isinstance(row, Mapping)]
    public_rows = [_public_row(row) for row in rows]
    state_counts = {state: 0 for state in FOLLOW_UP_STATES}
    kind_counts = {kind: 0 for kind in FOLLOW_UP_REFERENCE_KINDS}
    for row in public_rows:
        state = str(row.get("state") or "open")
        kind = str(row.get("reference_kind") or "")
        if state in state_counts:
            state_counts[state] += 1
        if kind in kind_counts:
            kind_counts[kind] += 1
    stable = {
        "campaign_id": str(record.get("campaign_id") or ""),
        "campaign_revision": max(0, int(record.get("revision") or 0)),
        "campaign_state": str(record.get("state") or "planned"),
        "follow_up_count": len(public_rows),
        "maximum_follow_ups": MAX_CAMPAIGN_FOLLOW_UPS,
        "state_counts": state_counts,
        "reference_kind_counts": kind_counts,
        "follow_up_refs": public_rows,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_follow_ups",
        "schema_version": EVALUATION_CAMPAIGN_FOLLOW_UP_SCHEMA_VERSION,
        **stable,
        "follow_up_digest": _digest(stable),
        "duplicate_reference": bool(duplicate_reference),
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "private_reference_values_returned": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "priority_assigned": False,
        "autonomous_prioritization": False,
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


def build_evaluation_campaign_follow_ups(campaign_id: str) -> dict[str, Any]:
    return _build_summary_from_record(load_evaluation_campaign_private(campaign_id))


def add_evaluation_campaign_follow_up(
    campaign_id: str,
    *,
    reference_kind: str,
    reference_value: str,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to add a follow-up reference.")
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        if str(record.get("state") or "planned") == "aborted":
            raise EvaluationCampaignError("An aborted campaign cannot add follow-up references.")
        normalized = _normalize_reference(record, reference_kind, reference_value)
        rows = [row for row in list(record.get("follow_up_refs") or ()) if isinstance(row, Mapping)]
        digest = _digest(str(normalized.get("private_reference_value") or ""))
        for row in rows:
            if (
                str(row.get("reference_kind") or "") == str(normalized.get("reference_kind") or "")
                and _digest(str(row.get("private_reference_value") or "")) == digest
                and str(row.get("state") or "open") == "open"
            ):
                return _build_summary_from_record(record, duplicate_reference=True)
        if len(rows) >= MAX_CAMPAIGN_FOLLOW_UPS:
            raise EvaluationCampaignError(f"Campaigns may contain at most {MAX_CAMPAIGN_FOLLOW_UPS} follow-up references.")
        now = _now_utc()
        rows.append({
            "follow_up_id": _new_follow_up_id(),
            **normalized,
            "state": "open",
            "created_at": now,
            "updated_at": now,
            "resolved_at": "",
            "dismissed_at": "",
        })
        record["follow_up_refs"] = rows
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = now
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    return _build_summary_from_record(record)


def update_evaluation_campaign_follow_up_state(
    campaign_id: str,
    follow_up_id: str,
    *,
    state: str,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to update a follow-up reference.")
    token = _validate_follow_up_id(follow_up_id)
    state_token = str(state or "").strip().lower()
    if state_token not in {"resolved", "dismissed"}:
        raise EvaluationCampaignError("A follow-up may be explicitly resolved or dismissed.")
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        rows = [dict(row) for row in list(record.get("follow_up_refs") or ()) if isinstance(row, Mapping)]
        target = next((row for row in rows if str(row.get("follow_up_id") or "") == token), None)
        if target is None:
            raise EvaluationCampaignError("Campaign follow-up reference not found.")
        if str(target.get("state") or "open") != "open":
            raise EvaluationCampaignError("Only an open follow-up reference may change state.")
        now = _now_utc()
        target["state"] = state_token
        target["updated_at"] = now
        target[f"{state_token}_at"] = now
        record["follow_up_refs"] = rows
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = now
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    return _build_summary_from_record(record)


def remove_evaluation_campaign_follow_up(
    campaign_id: str,
    follow_up_id: str,
    *,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to remove a follow-up reference.")
    token = _validate_follow_up_id(follow_up_id)
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(campaign_id)
        _require_expected_revision(record, expected_revision)
        rows = [dict(row) for row in list(record.get("follow_up_refs") or ()) if isinstance(row, Mapping)]
        filtered = [row for row in rows if str(row.get("follow_up_id") or "") != token]
        if len(filtered) == len(rows):
            raise EvaluationCampaignError("Campaign follow-up reference not found.")
        now = _now_utc()
        record["follow_up_refs"] = filtered
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = now
        _atomic_write(_campaign_path(str(record.get("campaign_id") or "")), record)
    return _build_summary_from_record(record)


def campaign_follow_up_summary_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_reference_value", "campaign_label", "objective", "content", "text", "message",
        "messages", "user_message", "assistant_response", "transcript", "prompt", "note", "notes",
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
