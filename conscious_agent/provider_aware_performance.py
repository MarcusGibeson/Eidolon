from __future__ import annotations

"""v1288.3-v1288.5 integration with configured local-model runtime seams."""

from dataclasses import replace
from typing import Any, Mapping

from provider_aware_performance_foundations import (
    AUTHORITY_FLAGS,
    build_provider_aware_performance_plan,
    public_provider_aware_performance_plan,
)

CONTRACT_VERSION = "v1288.5"


def _streaming_support(capability_evidence: Mapping[str, Any] | None) -> str:
    evidence = dict(capability_evidence or {})
    streaming = evidence.get("streaming")
    if isinstance(streaming, Mapping):
        support = str(streaming.get("support") or "unknown").lower()
    else:
        support = str(evidence.get("streaming_support") or "unknown").lower()
    return support


def build_configured_provider_performance_plan(
    config: Any,
    *,
    streaming_requested: bool,
    capability_evidence: Mapping[str, Any] | None = None,
    readiness_evidence: Mapping[str, Any] | None = None,
    performance_evidence: Mapping[str, Any] | None = None,
    task_kind: str = "conversation",
) -> dict[str, Any]:
    readiness = dict(readiness_evidence or {})
    performance = dict(performance_evidence or {})
    generation = getattr(config, "generation")
    plan = build_provider_aware_performance_plan(
        configured_context_window=int(getattr(config, "context_size")),
        configured_max_tokens=int(getattr(generation, "max_tokens")),
        configured_read_timeout_seconds=float(getattr(config, "read_timeout_seconds")),
        configured_retry_limit=int(getattr(config, "retry_limit")),
        streaming_requested=streaming_requested,
        streaming_support=_streaming_support(capability_evidence),
        health_state=str(readiness.get("health_state") or readiness.get("status") or "unknown"),
        latency_tier=str(performance.get("latency_tier") or "unknown"),
        observed_context_window=performance.get("observed_context_window"),
        task_kind=task_kind,
    )
    return {**plan, "integration_contract_version": CONTRACT_VERSION}


def apply_provider_aware_performance_config(config: Any, plan: Mapping[str, Any]) -> Any:
    """Return one ephemeral config for this request; persisted settings are untouched."""
    generation = replace(getattr(config, "generation"), max_tokens=int(plan["effective_max_tokens"]))
    adapted = replace(
        config,
        context_size=int(plan["effective_context_window"]),
        read_timeout_seconds=float(plan["effective_read_timeout_seconds"]),
        retry_limit=int(plan["effective_retry_limit"]),
        generation=generation,
    )
    validated = getattr(adapted, "validated", None)
    return validated() if callable(validated) else adapted


def provider_aware_performance_prompt(plan: Mapping[str, Any]) -> str:
    public = public_provider_aware_performance_plan(plan)
    return (
        "Provider-aware performance: use the supplied bounded context/output budget and generation strategy. "
        f"strategy={public.get('generation_strategy')}; input_budget={public.get('input_budget_tokens')}; "
        f"output_budget={public.get('effective_max_tokens')}; verification={public.get('verification_cadence')}. "
        "Do not infer provider/model capability from its name, skip mandatory verification, switch providers/models, "
        "or treat a performance recommendation as execution or authorization."
    )


def provider_aware_performance_authority() -> dict[str, bool]:
    return dict(AUTHORITY_FLAGS)
