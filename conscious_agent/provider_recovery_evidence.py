from __future__ import annotations

"""Bounded persisted evidence for provider availability and conversation resume.

Only the latest redacted readiness fact and transition timestamps are retained.
The record contains no provider payloads, prompts, responses, credentials, raw
command output, model inventory, endpoints, provider/model names, or private
conversation content. Writing happens only from explicit POST readiness paths;
GET/render helpers are read-only.
"""

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from offline_companion import CANONICAL_STATE_COPY, canonical_copy
from paths import DATA_DIR

RECOVERY_EVIDENCE_SCHEMA_VERSION = "1"
PROVIDER_RECOVERY_DIR = DATA_DIR / "provider_recovery"
LATEST_PROVIDER_RECOVERY_FILE = PROVIDER_RECOVERY_DIR / "latest_readiness.json"

_ALLOWED_TRIGGERS = {"manual_check", "visibility_recovery", "api_post"}
_ALLOWED_STATES = set(CANONICAL_STATE_COPY)
_RECOVERABLE_STATES = {"temporarily_unavailable", "generation_unavailable", "degraded", "misconfigured"}
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")
_LOCK = threading.RLock()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _bounded_timestamp(value: Any) -> str:
    token = str(value or "").strip()
    if not token or len(token) > 32 or not _TIMESTAMP.fullmatch(token):
        return ""
    try:
        datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return token


def _digest(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if _HEX_DIGEST.fullmatch(token) else ""


def _state(value: Any, fallback: str = "generation_unavailable") -> str:
    token = str(value or "").strip().lower()
    return token if token in _ALLOWED_STATES else fallback


def _load_raw() -> dict[str, Any] | None:
    try:
        value = json.loads(LATEST_PROVIDER_RECOVERY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _public_record(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("type") != "provider_recovery_evidence":
        return None
    checked_at = _bounded_timestamp(value.get("checked_at"))
    if not checked_at:
        return None
    state = _state(value.get("state"))
    observed_state = _state(value.get("observed_state"), state)
    previous_state = str(value.get("previous_state") or "").strip().lower()
    if previous_state not in _ALLOWED_STATES:
        previous_state = ""
    settings_scope = str(value.get("settings_scope") or "").strip().lower()
    if settings_scope not in {"configured", "unsaved_editor", "invalid_configuration"}:
        settings_scope = "invalid_configuration"
    trigger = str(value.get("trigger") or "api_post").strip().lower()
    if trigger not in _ALLOWED_TRIGGERS:
        trigger = "api_post"
    configured_values_match = bool(value.get("configured_values_match"))
    recovery_proven = bool(value.get("recovery_proven")) and configured_values_match and state in {"ready", "recovering"}
    return {
        "type": "provider_recovery_evidence",
        "schema_version": RECOVERY_EVIDENCE_SCHEMA_VERSION,
        "checked_at": checked_at,
        "state": state,
        "observed_state": observed_state,
        "previous_state": previous_state or None,
        "generation_available": bool(value.get("generation_available")),
        "embedding_available": bool(value.get("embedding_available")),
        "configured_values_match": configured_values_match,
        "settings_scope": settings_scope,
        "configuration_digest": _digest(value.get("configuration_digest")) or None,
        "trigger": trigger,
        "recovered": bool(value.get("recovered")) and recovery_proven,
        "recovery_proven": recovery_proven,
        "recovered_at": _bounded_timestamp(value.get("recovered_at")) or None,
        "last_ready_at": _bounded_timestamp(value.get("last_ready_at")) or None,
        "last_unavailable_at": _bounded_timestamp(value.get("last_unavailable_at")) or None,
        "readiness_persisted": True,
        "automatic_generation_replay": False,
        "automatic_resend": False,
        "settings_changed": False,
        "provider_or_model_selected": False,
        "redacted": True,
        "contains_provider_payloads": False,
        "contains_prompts_or_responses": False,
        "contains_credentials": False,
        "contains_raw_command_output": False,
        "contains_model_inventory": False,
        "contains_conversation_content": False,
    }


def load_provider_recovery_evidence() -> dict[str, Any] | None:
    """Read the latest valid redacted evidence without contacting a provider."""
    with _LOCK:
        return _public_record(_load_raw())


def build_provider_recovery_evidence(
    report: Mapping[str, Any],
    *,
    configured_configuration_digest: str | None,
    trigger: str = "api_post",
    previous: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one content-free latest-state record from a completed readiness report."""
    availability = report.get("availability") if isinstance(report.get("availability"), Mapping) else {}
    receipt = report.get("evidence_receipt") if isinstance(report.get("evidence_receipt"), Mapping) else {}
    checked_at = _bounded_timestamp(receipt.get("timestamp")) or _now_utc()
    state = _state(availability.get("state") or report.get("readiness_state"))
    observed_state = _state(availability.get("observed_state"), state)
    prior = _public_record(previous) if isinstance(previous, Mapping) else None
    prior_state = str((prior or {}).get("observed_state") or (prior or {}).get("state") or "")
    report_digest = _digest(report.get("configuration_digest") or receipt.get("configuration_digest"))
    configured_digest = _digest(configured_configuration_digest)
    configured_values_match = bool(report_digest and configured_digest and report_digest == configured_digest)
    settings_scope = "configured" if configured_values_match else ("unsaved_editor" if report_digest else "invalid_configuration")
    verified_receipt = bool(receipt and receipt.get("receipt_type") == "provider_readiness" and receipt.get("timestamp"))
    prior_recoverable = prior_state in _RECOVERABLE_STATES
    recovery_proven = bool(configured_values_match and verified_receipt and observed_state == "ready")
    recovered = bool(recovery_proven and prior_recoverable)
    last_ready_at = checked_at if recovery_proven else str((prior or {}).get("last_ready_at") or "")
    unavailable_now = observed_state in _RECOVERABLE_STATES
    last_unavailable_at = checked_at if configured_values_match and unavailable_now else str((prior or {}).get("last_unavailable_at") or "")
    recovered_at = checked_at if recovered else str((prior or {}).get("recovered_at") or "")
    normalized_trigger = str(trigger or "api_post").strip().lower()
    if normalized_trigger not in _ALLOWED_TRIGGERS:
        normalized_trigger = "api_post"
    record = {
        "type": "provider_recovery_evidence",
        "schema_version": RECOVERY_EVIDENCE_SCHEMA_VERSION,
        "checked_at": checked_at,
        "state": "recovering" if recovered else observed_state,
        "observed_state": observed_state,
        "previous_state": prior_state or None,
        "generation_available": bool(availability.get("generation_available")),
        "embedding_available": bool(availability.get("embedding_available")),
        "configured_values_match": configured_values_match,
        "settings_scope": settings_scope,
        "configuration_digest": report_digest or None,
        "trigger": normalized_trigger,
        "recovered": recovered,
        "recovery_proven": recovery_proven,
        "recovered_at": recovered_at or None,
        "last_ready_at": last_ready_at or None,
        "last_unavailable_at": last_unavailable_at or None,
        "readiness_persisted": True,
        "automatic_generation_replay": False,
        "automatic_resend": False,
        "settings_changed": False,
        "provider_or_model_selected": False,
        "redacted": True,
        "contains_provider_payloads": False,
        "contains_prompts_or_responses": False,
        "contains_credentials": False,
        "contains_raw_command_output": False,
        "contains_model_inventory": False,
        "contains_conversation_content": False,
    }
    return _public_record(record) or record


def persist_provider_recovery_evidence(
    report: Mapping[str, Any],
    *,
    configured_configuration_digest: str | None,
    trigger: str = "api_post",
) -> dict[str, Any]:
    """Atomically persist one latest redacted record; no conversation file is touched."""
    with _LOCK:
        previous = _load_raw()
        record = build_provider_recovery_evidence(
            report,
            configured_configuration_digest=configured_configuration_digest,
            trigger=trigger,
            previous=previous,
        )
        PROVIDER_RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
        temporary = LATEST_PROVIDER_RECOVERY_FILE.with_name(f".{LATEST_PROVIDER_RECOVERY_FILE.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
            temporary.replace(LATEST_PROVIDER_RECOVERY_FILE)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return dict(record)


def provider_resume_cue(evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return one canonical resume cue suitable for chat, overview, and attention surfaces."""
    record = _public_record(evidence) if isinstance(evidence, Mapping) else load_provider_recovery_evidence()
    if not record:
        return {
            "visible": False,
            "state": "unknown",
            "label": "Provider readiness has not been checked",
            "detail": "Run a bounded configured-provider readiness check before treating generation as recovered.",
            "checked_at": None,
            "can_resume_composition": False,
            "automatic_generation_replay": False,
            "automatic_resend": False,
            "redacted": True,
        }
    state = str(record.get("state") or "generation_unavailable")
    label, canonical_detail = canonical_copy(state)
    configured = record.get("settings_scope") == "configured"
    recovery_proven = bool(record.get("recovery_proven"))
    if not configured:
        detail = "The readiness result used unsaved or invalid editor values, so it does not prove the configured conversation provider recovered."
    elif recovery_proven:
        detail = "Verified configured-provider readiness is persisted. Your draft remains intact; continue composing explicitly and no earlier request will be replayed."
    else:
        detail = canonical_detail
    return {
        "visible": True,
        "state": state,
        "observed_state": record.get("observed_state"),
        "label": label,
        "detail": detail,
        "checked_at": record.get("checked_at"),
        "recovered_at": record.get("recovered_at"),
        "last_ready_at": record.get("last_ready_at"),
        "last_unavailable_at": record.get("last_unavailable_at"),
        "settings_scope": record.get("settings_scope"),
        "generation_available": bool(record.get("generation_available")),
        "embedding_available": bool(record.get("embedding_available")),
        "can_resume_composition": recovery_proven,
        "recovery_proven": recovery_proven,
        "readiness_persisted": True,
        "automatic_generation_replay": False,
        "automatic_resend": False,
        "new_acceptance_identity_created": False,
        "redacted": True,
    }
