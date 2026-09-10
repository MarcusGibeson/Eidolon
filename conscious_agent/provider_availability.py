from __future__ import annotations

"""Redacted provider availability and recovery presentation.

This module classifies an existing bounded readiness report. It never contacts a
provider, changes settings, selects a provider/model, replays generation, or
persists private runtime content.
"""

from typing import Any

from offline_companion import LOCAL_SURFACES, canonical_copy, dependency_boundaries, manual_recovery_handoff

STATE_CHECKING = "checking"
STATE_READY = "ready"
STATE_RECOVERING = "recovering"
STATE_TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
STATE_MISCONFIGURED = "misconfigured"
STATE_DEGRADED = "degraded"
STATE_GENERATION_UNAVAILABLE = "generation_unavailable"

_RECOVERABLE_STATES = {
    STATE_TEMPORARILY_UNAVAILABLE,
    STATE_GENERATION_UNAVAILABLE,
    STATE_DEGRADED,
}

OFFLINE_CAPABILITIES = LOCAL_SURFACES


def _classes(report: dict[str, Any], *, service: str | None = None) -> set[str]:
    values: set[str] = set()
    for item in report.get("issues") or []:
        if not isinstance(item, dict):
            continue
        item_service = str(item.get("service") or "")
        if service is not None and item_service not in {"", service}:
            continue
        token = str(item.get("classification") or item.get("code") or "").strip()
        if token:
            values.add(token)
    return values


def provider_availability_state(report: dict[str, Any], *, checking: bool = False) -> str:
    if checking:
        return STATE_CHECKING
    generation_available = bool(report.get("generation_service_available"))
    generation_model_available = report.get("generation_model_available")
    embedding_available = bool(report.get("embedding_service_available"))
    embedding_model_available = report.get("embedding_model_available")
    generation_classes = _classes(report, service="generation")
    all_classes = _classes(report)

    if "configuration_error" in all_classes:
        return STATE_MISCONFIGURED
    if "missing_model" in generation_classes or generation_model_available is False:
        return STATE_GENERATION_UNAVAILABLE
    if generation_classes & {"connection_failure", "unavailable_service", "read_timeout"}:
        return STATE_TEMPORARILY_UNAVAILABLE
    if not generation_available:
        return STATE_TEMPORARILY_UNAVAILABLE
    if (
        not embedding_available
        or embedding_model_available is False
        or bool(_classes(report, service="embedding"))
        or str(report.get("status") or "") == "degraded"
    ):
        return STATE_DEGRADED
    if str(report.get("status") or "") == "ready":
        return STATE_READY
    return STATE_GENERATION_UNAVAILABLE


def build_provider_availability_experience(
    report: dict[str, Any],
    *,
    previous_state: str | None = None,
    checking: bool = False,
) -> dict[str, Any]:
    state = provider_availability_state(report, checking=checking)
    previous = str(previous_state or "").strip()
    recovered = state == STATE_READY and previous in _RECOVERABLE_STATES
    visible_state = STATE_RECOVERING if recovered else state
    generation_available = bool(report.get("generation_service_available")) and report.get("generation_model_available") is not False
    embedding_available = bool(report.get("embedding_service_available")) and report.get("embedding_model_available") is not False

    label, detail = canonical_copy(visible_state)
    retry_allowed = state in _RECOVERABLE_STATES
    settings_review_recommended = state in {STATE_MISCONFIGURED, STATE_GENERATION_UNAVAILABLE}
    return {
        "state": visible_state,
        "observed_state": state,
        "previous_state": previous or None,
        "recovered": recovered,
        "label": label,
        "detail": detail,
        "generation_available": generation_available,
        "embedding_available": embedding_available,
        "offline_capabilities": list(OFFLINE_CAPABILITIES),
        "dependency_boundaries": dependency_boundaries(
            generation_available=generation_available,
            embedding_available=embedding_available,
            configuration_valid=state != STATE_MISCONFIGURED,
        ),
        "manual_recovery_handoff": manual_recovery_handoff(
            visible_state, readiness_persisted=bool(report.get("evidence_receipt") or report.get("checked_at") or report.get("status"))
        ),
        "readiness_retry_allowed": retry_allowed,
        "readiness_retry_delay_seconds": 5 if retry_allowed else None,
        "settings_review_recommended": settings_review_recommended,
        "automatic_generation_retry": False,
        "automatic_provider_switch": False,
        "automatic_model_management": False,
        "settings_changed": False,
        "redacted": True,
    }
