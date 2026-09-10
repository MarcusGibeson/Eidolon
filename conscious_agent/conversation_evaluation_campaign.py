from __future__ import annotations

"""Private runtime storage for v1088.1 operator evaluation campaigns.

Campaign plans live beneath EIDOLON_DATA_DIR and contain only explicit operator
configuration plus opaque evaluation references. Public summaries redact the
private label and objective. Mutations require confirmation, optimistic
revisions, and a cross-process directory lock. No campaign action creates a
daily evaluation, calls a provider, replays a request, or grants release power.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable, Iterator, Mapping
import uuid

from paths import DATA_DIR
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic
from conversation_daily_evaluation_protocol import EVALUATION_SIGNALS
from conversation_evaluation_campaign_protocol import (
    CAMPAIGN_FOCUS_AREAS,
    CAMPAIGN_STATES,
    MAX_CAMPAIGN_DURATION_DAYS,
    MAX_CAMPAIGN_EVALUATIONS,
    MAX_CAMPAIGN_FOCUS_AREAS,
    MAX_CAMPAIGN_LABEL_CHARS,
    MAX_CAMPAIGN_OBJECTIVE_CHARS,
    MAX_CAMPAIGN_REQUIRED_SIGNALS,
    MIN_CAMPAIGN_DURATION_DAYS,
    MIN_CAMPAIGN_EVALUATIONS,
    build_evaluation_campaign_protocol,
)

EVALUATION_CAMPAIGN_SCHEMA_VERSION = "1"
EVALUATION_CAMPAIGNS_DIR = DATA_DIR / "conversation_evaluation_campaigns"
_CAMPAIGN_ID_PATTERN = re.compile(r"^eval_campaign_[0-9]{8}T[0-9]{6}_[a-f0-9]{12}$")
_STORAGE_LOCK = threading.RLock()
_LOCK_TIMEOUT_SECONDS = 8.0
_STALE_LOCK_SECONDS = 120.0


class EvaluationCampaignError(ValueError):
    pass


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _new_campaign_id() -> str:
    return f"eval_campaign_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:12]}"


def _validate_campaign_id(campaign_id: str) -> str:
    token = str(campaign_id or "").strip()
    if not _CAMPAIGN_ID_PATTERN.fullmatch(token):
        raise EvaluationCampaignError("Invalid evaluation campaign identifier.")
    return token


def _campaign_path(campaign_id: str) -> Path:
    return EVALUATION_CAMPAIGNS_DIR / f"{_validate_campaign_id(campaign_id)}.json"


def _global_lock_path() -> Path:
    return EVALUATION_CAMPAIGNS_DIR / ".campaigns.lock"


def _load_json(path: Path) -> dict[str, Any] | None:
    return load_json_file(path, None, expected_type=dict)


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    write_json_atomic(path, dict(value), expected_type=dict, sort_keys=True)


@contextmanager
def _campaigns_lock() -> Iterator[None]:
    lock_path = _global_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, f"{os.getpid()}\n".encode("ascii", errors="ignore"))
            os.fsync(descriptor)
        except FileExistsError:
            try:
                age = max(0.0, time.time() - lock_path.stat().st_mtime)
            except OSError:
                age = 0.0
            if age >= _STALE_LOCK_SECONDS:
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise EvaluationCampaignError(
                    "Evaluation campaigns are being updated by another process. Reload before trying again."
                )
            time.sleep(0.02)
    try:
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            lock_path.unlink()
        except OSError:
            pass


@contextmanager
def campaign_storage_lock() -> Iterator[None]:
    with _STORAGE_LOCK:
        with _campaigns_lock():
            yield


def _bounded_text(value: str, maximum: int, label: str) -> str:
    token = str(value or "").strip()
    if len(token) > maximum:
        raise EvaluationCampaignError(f"{label} exceeds the {maximum}-character limit.")
    return token


def _bounded_integer(value: Any, minimum: int, maximum: int, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise EvaluationCampaignError(f"{label} must be an integer.") from error
    if number < minimum or number > maximum:
        raise EvaluationCampaignError(f"{label} must be between {minimum} and {maximum}.")
    return number


def _normalize_focus_areas(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        raise EvaluationCampaignError("Campaign focus areas must be a list.")
    normalized: list[str] = []
    for raw in value:
        token = str(raw or "").strip().lower()
        if token not in CAMPAIGN_FOCUS_AREAS:
            raise EvaluationCampaignError(f"Unsupported campaign focus area: {token or 'empty'}.")
        if token not in normalized:
            normalized.append(token)
    if not normalized:
        raise EvaluationCampaignError("At least one campaign focus area is required.")
    return normalized[:MAX_CAMPAIGN_FOCUS_AREAS]


def _normalize_required_signals(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set)):
        raise EvaluationCampaignError("Required campaign signals must be a list.")
    normalized: list[str] = []
    for raw in value:
        token = str(raw or "").strip().lower()
        if token not in EVALUATION_SIGNALS:
            raise EvaluationCampaignError(f"Unsupported campaign signal: {token or 'empty'}.")
        if token not in normalized:
            normalized.append(token)
    if len(normalized) > MAX_CAMPAIGN_REQUIRED_SIGNALS:
        raise EvaluationCampaignError(
            f"Campaigns may require at most {MAX_CAMPAIGN_REQUIRED_SIGNALS} evaluation signals."
        )
    return normalized


def _normalize_plan(
    *,
    campaign_label: str,
    objective: str,
    focus_areas: Any,
    target_evaluation_count: Any,
    minimum_completed_evaluations: Any,
    planned_duration_days: Any,
    required_signals: Any,
) -> dict[str, Any]:
    target = _bounded_integer(
        target_evaluation_count,
        MIN_CAMPAIGN_EVALUATIONS,
        MAX_CAMPAIGN_EVALUATIONS,
        "Target evaluation count",
    )
    minimum_completed = _bounded_integer(
        minimum_completed_evaluations,
        MIN_CAMPAIGN_EVALUATIONS,
        target,
        "Minimum completed evaluations",
    )
    duration = _bounded_integer(
        planned_duration_days,
        MIN_CAMPAIGN_DURATION_DAYS,
        MAX_CAMPAIGN_DURATION_DAYS,
        "Planned campaign duration",
    )
    return {
        "campaign_label": _bounded_text(campaign_label, MAX_CAMPAIGN_LABEL_CHARS, "Campaign label"),
        "objective": _bounded_text(objective, MAX_CAMPAIGN_OBJECTIVE_CHARS, "Campaign objective"),
        "focus_areas": _normalize_focus_areas(focus_areas),
        "target_evaluation_count": target,
        "minimum_completed_evaluations": minimum_completed,
        "planned_duration_days": duration,
        "required_signals": _normalize_required_signals(required_signals),
    }


def load_evaluation_campaign_private(campaign_id: str) -> dict[str, Any]:
    token = _validate_campaign_id(campaign_id)
    value = _load_json(_campaign_path(token))
    if not value or value.get("type") != "desktop_alpha_operator_evaluation_campaign":
        raise EvaluationCampaignError("Evaluation campaign not found.")
    return value


def iter_evaluation_campaign_private() -> Iterator[dict[str, Any]]:
    if not EVALUATION_CAMPAIGNS_DIR.exists():
        return
    for path in sorted(EVALUATION_CAMPAIGNS_DIR.glob("eval_campaign_*.json")):
        value = _load_json(path)
        if value and value.get("type") == "desktop_alpha_operator_evaluation_campaign":
            yield value


def campaign_public_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    plan = value.get("plan") if isinstance(value.get("plan"), Mapping) else {}
    refs = [row for row in list(value.get("evaluation_refs") or ()) if isinstance(row, Mapping)]
    public_refs = [
        {
            "evaluation_id": str(row.get("evaluation_id") or ""),
            "session_id": str(row.get("session_id") or ""),
            "enrolled_at": str(row.get("enrolled_at") or ""),
            "evaluation_state_at_enrollment": str(row.get("evaluation_state_at_enrollment") or "unknown"),
            "evaluation_revision_at_enrollment": max(0, int(row.get("evaluation_revision_at_enrollment") or 0)),
            "summary_digest": str(row.get("summary_digest") or ""),
        }
        for row in refs
    ]
    campaign_label = str(plan.get("campaign_label") or "")
    objective = str(plan.get("objective") or "")
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_summary",
        "schema_version": EVALUATION_CAMPAIGN_SCHEMA_VERSION,
        "campaign_id": str(value.get("campaign_id") or ""),
        "state": str(value.get("state") or "planned"),
        "revision": max(0, int(value.get("revision") or 0)),
        "created_at": str(value.get("created_at") or ""),
        "updated_at": str(value.get("updated_at") or ""),
        "activated_at": str(value.get("activated_at") or ""),
        "completed_at": str(value.get("completed_at") or ""),
        "aborted_at": str(value.get("aborted_at") or ""),
        "campaign_label_present": bool(campaign_label),
        "campaign_label_digest": _digest(campaign_label) if campaign_label else "",
        "campaign_objective_present": bool(objective),
        "campaign_objective_digest": _digest(objective) if objective else "",
        "focus_areas": [str(item) for item in list(plan.get("focus_areas") or ()) if str(item) in CAMPAIGN_FOCUS_AREAS],
        "target_evaluation_count": max(0, int(plan.get("target_evaluation_count") or 0)),
        "minimum_completed_evaluations": max(0, int(plan.get("minimum_completed_evaluations") or 0)),
        "planned_duration_days": max(0, int(plan.get("planned_duration_days") or 0)),
        "required_signals": [str(item) for item in list(plan.get("required_signals") or ()) if str(item) in EVALUATION_SIGNALS],
        "evaluation_count": len(public_refs),
        "maximum_evaluations": MAX_CAMPAIGN_EVALUATIONS,
        "evaluation_refs": public_refs,
        "evaluation_refs_digest": _digest(public_refs),
        "private_campaign_label_returned": False,
        "private_objective_returned": False,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "automatic_campaign_launch": False,
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
        "runtime_state_written": True,
        "source_tree_written": False,
        "content_free": True,
        "redacted": True,
    }


def create_evaluation_campaign(
    *,
    campaign_label: str,
    objective: str,
    focus_areas: Any,
    target_evaluation_count: Any,
    minimum_completed_evaluations: Any,
    planned_duration_days: Any,
    required_signals: Any = None,
    operator_confirmed: bool,
    campaign_id: str = "",
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to create a campaign.")
    protocol = build_evaluation_campaign_protocol()
    if protocol.get("protocol_status") != "ready":
        raise EvaluationCampaignError("The daily-evaluation checkpoint requires review before campaign creation.")
    plan = _normalize_plan(
        campaign_label=campaign_label,
        objective=objective,
        focus_areas=focus_areas,
        target_evaluation_count=target_evaluation_count,
        minimum_completed_evaluations=minimum_completed_evaluations,
        planned_duration_days=planned_duration_days,
        required_signals=required_signals,
    )
    token = _validate_campaign_id(campaign_id) if campaign_id else _new_campaign_id()
    now = _now_utc()
    record = {
        "type": "desktop_alpha_operator_evaluation_campaign",
        "schema_version": EVALUATION_CAMPAIGN_SCHEMA_VERSION,
        "campaign_id": token,
        "state": "planned",
        "revision": 1,
        "created_at": now,
        "updated_at": now,
        "activated_at": "",
        "completed_at": "",
        "aborted_at": "",
        "daily_evaluation_contract_digest": str(protocol.get("daily_evaluation_contract_digest") or ""),
        "campaign_contract_digest": str(protocol.get("campaign_contract_digest") or ""),
        "plan": plan,
        "evaluation_refs": [],
        "operator_confirmed": True,
        "provider_invoked": False,
        "release_certified": False,
        "promotion_performed": False,
    }
    with campaign_storage_lock():
        path = _campaign_path(token)
        if path.exists():
            raise EvaluationCampaignError("Evaluation campaign already exists.")
        _atomic_write(path, record)
    return campaign_public_summary(record)


def load_evaluation_campaign(campaign_id: str, *, include_private_plan: bool = False) -> dict[str, Any]:
    record = load_evaluation_campaign_private(campaign_id)
    summary = campaign_public_summary(record)
    if include_private_plan:
        plan = record.get("plan") if isinstance(record.get("plan"), Mapping) else {}
        summary["private_campaign_label"] = str(plan.get("campaign_label") or "")
        summary["private_objective"] = str(plan.get("objective") or "")
        summary["private_campaign_label_returned"] = True
        summary["private_objective_returned"] = True
        summary["content_free"] = False
        summary["redacted"] = False
    return summary


def _require_expected_revision(record: Mapping[str, Any], expected_revision: int | None) -> None:
    if expected_revision is None:
        raise EvaluationCampaignError("An expected campaign revision is required.")
    current = max(0, int(record.get("revision") or 0))
    if int(expected_revision) != current:
        raise EvaluationCampaignError("Campaign revision is stale. Reload before trying again.")


def mutate_evaluation_campaign(
    campaign_id: str,
    *,
    expected_revision: int | None,
    operator_confirmed: bool,
    mutator: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    if not operator_confirmed:
        raise EvaluationCampaignError("Explicit operator confirmation is required to update a campaign.")
    token = _validate_campaign_id(campaign_id)
    with campaign_storage_lock():
        record = load_evaluation_campaign_private(token)
        _require_expected_revision(record, expected_revision)
        mutator(record)
        record["revision"] = max(0, int(record.get("revision") or 0)) + 1
        record["updated_at"] = _now_utc()
        _atomic_write(_campaign_path(token), record)
    return campaign_public_summary(record)


def update_evaluation_campaign_plan(
    campaign_id: str,
    *,
    campaign_label: str,
    objective: str,
    focus_areas: Any,
    target_evaluation_count: Any,
    minimum_completed_evaluations: Any,
    planned_duration_days: Any,
    required_signals: Any = None,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    plan = _normalize_plan(
        campaign_label=campaign_label,
        objective=objective,
        focus_areas=focus_areas,
        target_evaluation_count=target_evaluation_count,
        minimum_completed_evaluations=minimum_completed_evaluations,
        planned_duration_days=planned_duration_days,
        required_signals=required_signals,
    )

    def apply(record: dict[str, Any]) -> None:
        if str(record.get("state") or "planned") != "planned":
            raise EvaluationCampaignError("Only a planned campaign may change its plan.")
        enrolled = len([row for row in list(record.get("evaluation_refs") or ()) if isinstance(row, Mapping)])
        if enrolled > int(plan["target_evaluation_count"]):
            raise EvaluationCampaignError("The target count cannot be lower than current enrollment.")
        record["plan"] = plan

    return mutate_evaluation_campaign(
        campaign_id,
        expected_revision=expected_revision,
        operator_confirmed=operator_confirmed,
        mutator=apply,
    )


def activate_evaluation_campaign(
    campaign_id: str,
    *,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    def apply(record: dict[str, Any]) -> None:
        if str(record.get("state") or "planned") != "planned":
            raise EvaluationCampaignError("Only a planned campaign may be activated.")
        record["state"] = "active"
        record["activated_at"] = _now_utc()

    return mutate_evaluation_campaign(
        campaign_id,
        expected_revision=expected_revision,
        operator_confirmed=operator_confirmed,
        mutator=apply,
    )


def abort_evaluation_campaign(
    campaign_id: str,
    *,
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    def apply(record: dict[str, Any]) -> None:
        state = str(record.get("state") or "planned")
        if state not in {"planned", "active"}:
            raise EvaluationCampaignError("Only a planned or active campaign may be aborted.")
        record["state"] = "aborted"
        record["aborted_at"] = _now_utc()

    return mutate_evaluation_campaign(
        campaign_id,
        expected_revision=expected_revision,
        operator_confirmed=operator_confirmed,
        mutator=apply,
    )


def evaluation_campaign_summary_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_campaign_label", "private_objective", "campaign_label", "objective",
        "content", "text", "message", "messages", "user_message", "assistant_response",
        "transcript", "prompt", "note", "notes", "temporary_instruction", "pinned_context",
        "queued_operator_intent", "provider_payload", "credentials", "vectors", "embedding",
        "receipt", "receipts", "hidden_reasoning", "chain_of_thought",
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
