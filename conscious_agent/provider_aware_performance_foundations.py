from __future__ import annotations

"""v1288.0-v1288.2 provider-aware performance foundations.

The policy is capability- and evidence-driven. Provider/model names are evidence
labels, never branches in product behavior. The module is pure and provider-free:
it does not contact a provider, change persisted settings, select a different
model, execute verification, or grant authority.
"""

from hashlib import sha256
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1288.2"
MILESTONE = "Provider-Aware Performance"

HEALTH_STATES = {"ready", "degraded", "unavailable", "misconfigured", "unknown"}
LATENCY_TIERS = {"low", "medium", "high", "unknown"}
SUPPORT_STATES = {"supported", "unsupported", "server_dependent", "unknown"}

AUTHORITY_FLAGS = {
    "provider_contact_authorized": False,
    "prompt_transmission_authorized": False,
    "automatic_provider_switch_authorized": False,
    "automatic_model_switch_authorized": False,
    "automatic_model_management_authorized": False,
    "configuration_mutation_authorized": False,
    "test_execution_authorized": False,
    "repair_authorized": False,
    "project_mutation_authorized": False,
    "source_application_authorized": False,
    "self_update_authorized": False,
    "rollback_authorized": False,
    "release_authorized": False,
    "standing_authority_granted": False,
}


def _digest(value: Mapping[str, Any]) -> str:
    return sha256(json.dumps(dict(value), sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _bounded_int(value: Any, low: int, high: int, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = fallback
    return max(low, min(high, parsed))


def _bounded_float(value: Any, low: float, high: float, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = fallback
    return max(low, min(high, parsed))


def build_provider_aware_performance_plan(
    *,
    configured_context_window: int,
    configured_max_tokens: int,
    configured_read_timeout_seconds: float,
    configured_retry_limit: int,
    streaming_requested: bool,
    streaming_support: str = "unknown",
    health_state: str = "unknown",
    latency_tier: str = "unknown",
    observed_context_window: int | None = None,
    task_kind: str = "conversation",
) -> dict[str, Any]:
    """Return a content-free performance plan from generic capabilities/evidence.

    Configured values remain hard ceilings. Observed evidence may make the plan
    more conservative, never enlarge the context, timeout, retries, or output
    budget beyond operator configuration.
    """
    configured_context = _bounded_int(configured_context_window, 512, 2_000_000, 8192)
    configured_output = _bounded_int(configured_max_tokens, 1, 131_072, 350)
    configured_timeout = _bounded_float(configured_read_timeout_seconds, 0.1, 3600.0, 120.0)
    configured_retries = _bounded_int(configured_retry_limit, 0, 5, 1)
    support = str(streaming_support or "unknown").lower()
    health = str(health_state or "unknown").lower()
    latency = str(latency_tier or "unknown").lower()
    if support not in SUPPORT_STATES:
        support = "unknown"
    if health not in HEALTH_STATES:
        health = "unknown"
    if latency not in LATENCY_TIERS:
        latency = "unknown"

    observed = None
    if observed_context_window is not None:
        observed = _bounded_int(observed_context_window, 512, 2_000_000, configured_context)
    effective_context = min(configured_context, observed) if observed is not None else configured_context

    # Keep enough room for protected instructions and the current turn. Output
    # caps scale structurally with context rather than with a named model.
    output_context_cap = max(64, effective_context // 8)
    effective_max_tokens = min(configured_output, output_context_cap)
    protected_reserve = min(max(256, effective_context // 16), 2048)
    input_budget = max(256, effective_context - effective_max_tokens - protected_reserve)

    if latency == "low":
        timeout_factor = 0.65
    elif latency == "medium":
        timeout_factor = 0.85
    else:
        timeout_factor = 1.0
    effective_timeout = min(configured_timeout, max(5.0, round(configured_timeout * timeout_factor, 3)))

    if streaming_requested or health in {"degraded", "unavailable", "misconfigured"} or latency == "high":
        effective_retries = 0
    else:
        effective_retries = min(configured_retries, 1)

    streaming_eligible = bool(streaming_requested and support != "unsupported" and health not in {"unavailable", "misconfigured"})
    generation_strategy = "bounded_streaming" if streaming_eligible else "bounded_non_streaming"
    if streaming_requested and support == "unsupported":
        transport_fallback = "same_provider_non_streaming_only_if_calling_surface_supports_it"
    elif health in {"unavailable", "misconfigured"}:
        transport_fallback = "operator_review_provider_or_configuration"
    elif health == "degraded":
        transport_fallback = "degrade_optional_context_before_provider_change"
    else:
        transport_fallback = "none"

    if health in {"unavailable", "misconfigured"}:
        verification_cadence = "provider_independent_checks_only_until_recovered"
    elif latency == "high":
        verification_cadence = "batch_model_dependent_checks_keep_all_mandatory_gates"
    elif latency == "medium":
        verification_cadence = "focused_checks_per_coherent_edit_group"
    else:
        verification_cadence = "focused_checks_per_change"

    result: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "milestone": MILESTONE,
        "task_kind": str(task_kind or "conversation")[:48],
        "configured_context_window": configured_context,
        "observed_context_window": observed,
        "effective_context_window": effective_context,
        "protected_context_reserve_tokens": protected_reserve,
        "input_budget_tokens": input_budget,
        "configured_max_tokens": configured_output,
        "effective_max_tokens": effective_max_tokens,
        "configured_read_timeout_seconds": configured_timeout,
        "effective_read_timeout_seconds": effective_timeout,
        "configured_retry_limit": configured_retries,
        "effective_retry_limit": effective_retries,
        "streaming_requested": bool(streaming_requested),
        "streaming_support": support,
        "streaming_eligible": streaming_eligible,
        "health_state": health,
        "latency_tier": latency,
        "generation_strategy": generation_strategy,
        "verification_cadence": verification_cadence,
        "transport_fallback": transport_fallback,
        "fallback_changes_provider": False,
        "fallback_changes_model": False,
        "mandatory_verification_may_be_skipped": False,
        "operator_configuration_is_ceiling": True,
        "provider_name_drives_behavior": False,
        "model_name_drives_behavior": False,
        "content_free": True,
        "read_only": True,
        **AUTHORITY_FLAGS,
    }
    result["plan_digest"] = _digest(result)
    return result


def public_provider_aware_performance_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "contract_version", "task_kind", "effective_context_window", "protected_context_reserve_tokens",
        "input_budget_tokens", "effective_max_tokens", "effective_read_timeout_seconds", "effective_retry_limit",
        "streaming_requested", "streaming_support", "streaming_eligible", "health_state", "latency_tier",
        "generation_strategy", "verification_cadence", "transport_fallback", "fallback_changes_provider",
        "fallback_changes_model", "mandatory_verification_may_be_skipped", "operator_configuration_is_ceiling",
        "provider_name_drives_behavior", "model_name_drives_behavior", "content_free", "read_only", "plan_digest",
    }
    return {key: plan.get(key) for key in sorted(allowed) if key in plan}
