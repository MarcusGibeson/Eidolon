from __future__ import annotations

"""v1288.6-v1288.8 reliability checks for provider-aware performance plans."""

from typing import Any, Iterable, Mapping

from provider_aware_performance_foundations import AUTHORITY_FLAGS

CONTRACT_VERSION = "v1288.8"


def assess_provider_aware_performance_reliability(plans: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in plans]
    violations: list[str] = []
    for index, row in enumerate(rows):
        prefix = f"plan_{index}"
        if int(row.get("effective_context_window") or 0) > int(row.get("configured_context_window") or 0):
            violations.append(prefix + ":context_expanded")
        if int(row.get("effective_max_tokens") or 0) > int(row.get("configured_max_tokens") or 0):
            violations.append(prefix + ":output_expanded")
        if float(row.get("effective_read_timeout_seconds") or 0) > float(row.get("configured_read_timeout_seconds") or 0):
            violations.append(prefix + ":timeout_expanded")
        if int(row.get("effective_retry_limit") or 0) > int(row.get("configured_retry_limit") or 0):
            violations.append(prefix + ":retry_expanded")
        if row.get("mandatory_verification_may_be_skipped") is not False:
            violations.append(prefix + ":verification_weakened")
        if row.get("fallback_changes_provider") is not False or row.get("fallback_changes_model") is not False:
            violations.append(prefix + ":hidden_fallback_switch")
        if row.get("provider_name_drives_behavior") is not False or row.get("model_name_drives_behavior") is not False:
            violations.append(prefix + ":name_specific_behavior")
        if any(bool(row.get(key)) for key in AUTHORITY_FLAGS):
            violations.append(prefix + ":authority_expansion")
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not violations,
        "plan_count": len(rows),
        "violations": violations,
        "violation_count": len(violations),
        "operator_configuration_ceiling_preserved": not any("expanded" in item for item in violations),
        "mandatory_verification_preserved": not any("verification_weakened" in item for item in violations),
        "provider_model_switching_absent": not any("fallback_switch" in item for item in violations),
        "name_specific_product_behavior_absent": not any("name_specific" in item for item in violations),
        "authority_preserved": not any("authority_expansion" in item for item in violations),
        "content_free": True,
        "read_only": True,
        **AUTHORITY_FLAGS,
    }
