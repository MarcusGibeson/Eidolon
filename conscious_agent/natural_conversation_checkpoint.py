from __future__ import annotations

"""Read-only v1102 natural-conversation checkpoint.

The checkpoint consolidates the completed v1102 conversation contracts into one
content-free status. It does not contact a provider, persist evidence, apply a
prompt-policy recommendation, mutate personality or memory, change a model, or
grant release/certification authority.
"""

from typing import Any, Mapping

from natural_conversation_quality_evaluation import native_conversation_scenarios
from personality_stability import build_personality_stability_snapshot
from provider_neutral_conversation_tuning import build_provider_neutral_tuning_plan
from release_metadata import WORKING_SOURCE_VERSION

NATURAL_CONVERSATION_CHECKPOINT_SCHEMA_VERSION = "1"
NATURAL_CONVERSATION_CONTRACT_VERSION = "v1102"


def _check(name: str, status: str, *, required: bool, summary: str, recovery: str = "") -> dict[str, Any]:
    normalized = status if status in {"ready", "pending", "degraded", "blocked"} else "degraded"
    return {
        "name": str(name)[:80],
        "status": normalized,
        "required": bool(required),
        "summary": str(summary)[:280],
        "recovery": str(recovery)[:180],
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _bool_false(mapping: Mapping[str, Any], *names: str) -> bool:
    return all(not bool(mapping.get(name)) for name in names)


def _native_evidence_status(report: Mapping[str, Any]) -> tuple[str, str]:
    status = str(report.get("status") or "pending").strip().lower()
    source_is_native = bool(report.get("native_provider_evidence"))
    if status == "pass" and source_is_native:
        return "ready", "Native configured-provider conversation evidence passed."
    if status in {"fail", "failed"} and source_is_native:
        return "blocked", "Native configured-provider conversation evidence contains a current quality failure."
    if status in {"partial", "warn", "warning"} and source_is_native:
        return "degraded", "Native configured-provider conversation evidence passed with unresolved warnings."
    if status in {"unavailable", "missing_model", "invalid_configuration"}:
        return "pending", "The configured provider was unavailable; no native quality conclusion is inferred."
    if status == "blocked" and bool(report.get("confirmation_required")):
        return "pending", "Native validation remains pending explicit operator confirmation."
    if not report:
        return "pending", "Native configured-provider conversation evidence has not been supplied."
    return "pending", f"Native conversation evidence is reported as {status or 'pending'} without a pass claim."


def _verification_status(evidence: Mapping[str, Any]) -> tuple[str, str]:
    if not evidence:
        return "pending", "Focused deterministic and regression totals are not attached to this runtime report."
    passed = max(0, int(evidence.get("passed") or 0))
    total = max(0, int(evidence.get("total") or 0))
    ok = bool(evidence.get("ok")) and total > 0 and passed == total
    if ok:
        return "ready", f"Attached deterministic evidence passed {passed}/{total}."
    if total > 0:
        return "blocked", f"Attached deterministic evidence passed {passed}/{total}; current failures remain."
    return "pending", "Attached deterministic evidence is incomplete."


def build_natural_conversation_checkpoint(
    *,
    native_validation: Mapping[str, Any] | None = None,
    focused_verification: Mapping[str, Any] | None = None,
    regression_verification: Mapping[str, Any] | None = None,
    stability_evidence: Mapping[str, Any] | None = None,
    tuning_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one bounded, content-free v1102 checkpoint report."""

    native = _mapping(native_validation)
    focused = _mapping(focused_verification)
    regressions = _mapping(regression_verification)
    supplied_stability = _mapping(stability_evidence)

    scenarios = native_conversation_scenarios()
    synthetic_stability = build_personality_stability_snapshot([]).public_summary()
    stability = supplied_stability or synthetic_stability
    quality = _mapping(native.get("quality_scorecard"))
    plan = _mapping(tuning_plan) or _mapping(native.get("provider_neutral_tuning_preview"))
    if not plan:
        plan = build_provider_neutral_tuning_plan(quality or None).public_summary()

    checks: list[dict[str, Any]] = [
        _check("identity_and_relationship_foundation", "ready", required=True, summary="Configured identity remains stable and relationship posture stays explicit, user-led, lane-aware, and non-inflating."),
        _check("greeting_repetition_and_topic_continuity", "ready", required=True, summary="Greetings, repeated openings, current-turn intent, deictic follow-ups, interruptions, and explicit topic shifts share one bounded conversation contract."),
        _check("corrections_preferences_and_response_shape", "ready", required=True, summary="Later corrections win, response preferences remain session-local, current explicit requests take precedence, and light turns stay protected from unnecessary expansion."),
        _check("affection_and_nickname_boundaries", "ready", required=True, summary="Warmth remains user-led and bounded; nickname use requires explicit current or retained consent and is suppressed in operator work."),
        _check("native_quality_evaluation_surface", "ready" if len(scenarios) == 12 else "blocked", required=True, summary=f"The current native validator exposes {len(scenarios)} bounded, content-free natural-conversation scenarios.", recovery="Restore the twelve-scenario v1102 quality contract." if len(scenarios) != 12 else ""),
    ]

    native_status, native_summary = _native_evidence_status(native)
    checks.append(_check("native_configured_provider_evidence", native_status, required=True, summary=native_summary, recovery="Run one explicitly confirmed bounded native conversation validation when the configured provider is intentionally available." if native_status != "ready" else ""))

    tuning_safe = _bool_false(plan, "automatic_application_allowed", "provider_specific_parameters_present", "provider_configuration_changed", "model_configuration_changed", "prompt_policy_changed", "writes_state", "mutates_personality", "contains_message_content", "contains_response_text", "contains_prompt_text")
    checks.append(_check("provider_neutral_tuning_boundary", "ready" if tuning_safe else "blocked", required=True, summary="Tuning remains provider-neutral, content-free, preview-only, and operator-controlled.", recovery="Reject the tuning plan and inspect any mutation or provider-specific field." if not tuning_safe else ""))

    drift = str(stability.get("drift_risk") or "bounded")
    long_guard = bool(stability.get("long_horizon_guard_active", True))
    if not long_guard or drift in {"identity_reset_risk", "relationship_inflation_risk"}:
        stability_status = "blocked"
    elif drift in {"operator_lane_bleed_risk", "repetition_or_tone_drift_risk"}:
        stability_status = "degraded"
    else:
        stability_status = "ready"
    checks.append(_check("long_conversation_personality_stability", stability_status, required=True, summary=f"The twelve-turn recent guard and bounded forty-eight-turn horizon report {drift}.", recovery="Review the content-free stability metrics before further tuning." if stability_status != "ready" else ""))

    focused_status, focused_summary = _verification_status(focused)
    regression_status, regression_summary = _verification_status(regressions)
    checks.append(_check("focused_deterministic_verification", focused_status, required=True, summary=focused_summary, recovery="Run the registered v1102 focused chain from an isolated source copy." if focused_status != "ready" else ""))
    checks.append(_check("conversation_regression_verification", regression_status, required=True, summary=regression_summary, recovery="Run the retained conversation/context regression sweep." if regression_status != "ready" else ""))

    authority_safe = _bool_false(native, "automatic_model_management", "provider_configuration_changed", "approval_granted", "release_authorized", "autonomous_action_performed") and _bool_false(plan, "automatic_application_allowed", "provider_configuration_changed", "model_configuration_changed", "prompt_policy_changed", "writes_state", "mutates_personality")
    checks.append(_check("operator_authority_boundary", "ready" if authority_safe else "blocked", required=True, summary="The checkpoint performs no automatic tuning, provider/model change, memory/personality mutation, approval, promotion, or certification.", recovery="Stop and reject any report that claims automatic authority." if not authority_safe else ""))

    required_blocked = [row for row in checks if row["required"] and row["status"] == "blocked"]
    degraded = [row for row in checks if row["status"] == "degraded"]
    pending = [row for row in checks if row["status"] == "pending"]
    native_ready = native_status == "ready"
    verification_ready = focused_status == "ready" and regression_status == "ready"

    if required_blocked:
        status = "blocked"
        headline = "Natural conversation is blocked by a current contract failure."
    elif degraded:
        status = "degraded"
        headline = "Natural conversation remains usable, but current quality evidence needs attention."
    elif native_ready and verification_ready:
        status = "ready_for_operator_review"
        headline = "Natural conversation contracts and supplied evidence are ready for operator review."
    elif native_ready:
        status = "ready_for_verification_review"
        headline = "Native conversation evidence passed; deterministic verification evidence remains to be attached."
    else:
        status = "ready_for_native_validation"
        headline = "Natural conversation contracts are coherent; native configured-provider evidence remains pending."

    return {
        "schema_version": NATURAL_CONVERSATION_CHECKPOINT_SCHEMA_VERSION,
        "contract_version": NATURAL_CONVERSATION_CONTRACT_VERSION,
        "working_source_version": str(WORKING_SOURCE_VERSION),
        "status": status,
        "ok": not bool(required_blocked),
        "headline": headline,
        "checks": checks,
        "current_product_defect_count": len(required_blocked) + len(degraded),
        "pending_evidence_count": len(pending),
        "native_provider_evidence_status": native_status,
        "native_provider_contacted": False,
        "provider_request_repeated": False,
        "automatic_tuning_applied": False,
        "provider_configuration_changed": False,
        "model_configuration_changed": False,
        "memory_written": False,
        "personality_mutated": False,
        "conversation_mutated": False,
        "approval_granted": False,
        "release_authorized": False,
        "automatic_promotion": False,
        "automatic_certification": False,
        "operator_authority_required": True,
        "content_free": True,
        "private_values_included": False,
    }


def checkpoint_contains_private_fields(value: Any) -> bool:
    """Conservative key scan for checkpoint/API and package verification."""
    forbidden = {"path", "root", "content", "draft", "message", "prompt", "response", "payload", "secret", "credential", "endpoint", "memory", "conversation_id", "session_id", "project_id", "model", "model_name", "provider_payload", "history", "transcript"}
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token == lowered or lowered.endswith("_" + token) for token in forbidden):
                return True
            if checkpoint_contains_private_fields(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(checkpoint_contains_private_fields(item) for item in value)
    return False
