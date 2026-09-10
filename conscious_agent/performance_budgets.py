from __future__ import annotations

"""Hardware-tolerant runtime performance budgets for v1253.6."""

from copy import deepcopy
from typing import Any, Mapping

CONTRACT_VERSION = "v1253.6"
RUNTIME_REPAIR_VERSION = "v1253.9.2"

DEFAULT_BUDGETS: dict[str, dict[str, Any]] = {
    "warm_pre_provider_ms": {"median_max": 125.0, "p95_max": 500.0, "hardware_sensitive": True},
    "contention_warm_pre_provider_ms": {"median_max": 250.0, "p95_max": 750.0, "hardware_sensitive": True},
    "social_prompt_tokens": {"value_max": 2400.0, "hardware_sensitive": False},
    "ordinary_prompt_tokens": {"value_max": 2700.0, "hardware_sensitive": False},
    "trusted_action_ack_build_ms": {"median_max": 5.0, "p95_max": 15.0, "hardware_sensitive": False},
    "memory_index_read_ms": {"median_max": 50.0, "p95_max": 100.0, "hardware_sensitive": False},
    "session_index_read_ms": {"median_max": 50.0, "p95_max": 100.0, "hardware_sensitive": False},
    "action_index_read_ms": {"median_max": 50.0, "p95_max": 100.0, "hardware_sensitive": False},
    "dashboard_fast_status_ms": {"median_max": 25.0, "p95_max": 75.0, "hardware_sensitive": False},
    "terminal_cold_start_seconds": {"median_target": 3.0, "median_max": 5.5, "p95_max": 7.5, "hardware_sensitive": True},
    "conversation_runtime_import_seconds": {"median_target": 3.0, "median_max": 5.0, "p95_max": 7.0, "hardware_sensitive": True},
    "terminal_cold_start_established_runtime_seconds": {"median_target": 3.0, "median_max": 5.5, "p95_max": 7.5, "hardware_sensitive": True},
    "terminal_cold_start_fresh_data_seconds": {"median_target": 3.5, "median_max": 6.5, "p95_max": 8.5, "hardware_sensitive": True},
    "conversation_runtime_process_start_seconds": {"median_target": 3.0, "median_max": 5.0, "p95_max": 7.0, "hardware_sensitive": True},
    "conversation_runtime_incremental_import_seconds": {"median_target": 1.0, "median_max": 3.0, "p95_max": 4.0, "hardware_sensitive": True},
    "first_message_pre_provider_ms": {"median_max": 900.0, "p95_max": 1500.0, "hardware_sensitive": True},
    "first_message_next_input_ready_ms": {"median_max": 1500.0, "p95_max": 2500.0, "hardware_sensitive": True},
}


def performance_budgets() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "budgets": deepcopy(DEFAULT_BUDGETS),
        "policy": {
            "use_median_and_p95": True,
            "hardware_sensitive_metrics_allow_relative_baseline": True,
            "single_outlier_never_grants_or_revokes_release_authority": True,
            "benchmark_receipts_content_free": True,
        },
        "provider_contact_authorized": False,
        "project_mutation_authorized": False,
        "release_authorized": False,
        "independent_authority_granted": False,
    }


def evaluate_budget(name: str, measurement: Mapping[str, Any], *, baseline: Mapping[str, Any] | None = None) -> dict[str, Any]:
    spec = DEFAULT_BUDGETS.get(str(name))
    if spec is None:
        return {"ok": False, "metric": name, "reason": "unknown_budget", "content_free": True}
    checks: dict[str, bool] = {}
    for key in ("value_max", "median_max", "p95_max"):
        if key not in spec:
            continue
        field = key[:-4] if key.endswith("_max") else key
        value = measurement.get(field)
        checks[key] = isinstance(value, (int, float)) and float(value) <= float(spec[key])
    targets: dict[str, bool] = {}
    for key in ("value_target", "median_target", "p95_target"):
        if key not in spec:
            continue
        field = key[:-7] if key.endswith("_target") else key
        value = measurement.get(field)
        targets[key] = isinstance(value, (int, float)) and float(value) <= float(spec[key])
    relative = None
    if bool(spec.get("hardware_sensitive")) and baseline:
        current = measurement.get("median")
        prior = baseline.get("median")
        if isinstance(current, (int, float)) and isinstance(prior, (int, float)) and float(prior) > 0:
            ratio = float(current) / float(prior)
            relative = {"ratio": round(ratio, 4), "within_25_percent": ratio <= 1.25}
    return {
        "ok": all(checks.values()) if checks else False,
        "metric": str(name),
        "checks": checks,
        "relative": relative,
        "targets": targets,
        "target_met": all(targets.values()) if targets else None,
        "hardware_sensitive": bool(spec.get("hardware_sensitive")),
        "content_free": True,
        "authority_granted": False,
    }


__all__ = ["CONTRACT_VERSION", "DEFAULT_BUDGETS", "performance_budgets", "evaluate_budget"]
