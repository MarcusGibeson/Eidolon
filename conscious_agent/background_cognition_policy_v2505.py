from __future__ import annotations

"""v2505.0 bounded admission policy for message-independent cognition.

The policy is deliberately narrower than foreground cognition. It may admit
registered cognitive operations while the operator is absent, but it cannot
create external authority, contact a provider, send communication, execute a
tool, mutate source, or apply cognitive candidates.
"""

from copy import deepcopy
from typing import Any, Mapping

CONTRACT_VERSION = "v2505.0"

BACKGROUND_SAFE_OPERATIONS = frozenset({
    "RECALL_MEMORY",
    "CONTINUE_THOUGHT",
    "RECONSIDER_BELIEF",
    "REVIEW_GOAL",
    "PLAN",
    "REPLAN",
    "INTEGRATE_EXPERIENCE",
    "REVIEW_SELF_MODEL",
    "RESOLVE_CONFLICT",
    "REFLECT",
})


def evaluate_background_cognition_admission(
    *,
    operation: str,
    foreground_busy: bool = False,
    quiet_hours: bool = False,
    operator_paused: bool = False,
    sleeping: bool = False,
    resource_pressure: str = "normal",
    open_background_cycles: int = 0,
    cycles_in_window: int = 0,
    max_cycles_per_window: int = 4,
) -> dict[str, Any]:
    op = str(operation or "").strip().upper()
    pressure = str(resource_pressure or "normal").strip().lower()
    if pressure not in {"idle", "normal", "elevated", "critical"}:
        raise ValueError("invalid resource_pressure")
    reasons: list[str] = []
    if op == "REST":
        reasons.append("deliberate_inactivity")
    elif op not in BACKGROUND_SAFE_OPERATIONS:
        reasons.append("operation_not_background_safe")
    if foreground_busy:
        reasons.append("foreground_busy")
    if quiet_hours:
        reasons.append("quiet_hours")
    if operator_paused:
        reasons.append("operator_paused")
    if sleeping:
        reasons.append("sleeping")
    if pressure in {"elevated", "critical"}:
        reasons.append("resource_pressure")
    if int(open_background_cycles or 0) > 0:
        reasons.append("background_cycle_already_open")
    if int(cycles_in_window or 0) >= max(1, int(max_cycles_per_window or 1)):
        reasons.append("background_cycle_budget_exhausted")
    admitted = not reasons
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "operation": op,
        "admitted": admitted,
        "suppression_reasons": reasons,
        "authority_boundary": {
            "can_contact_provider": False,
            "can_browse": False,
            "can_send_message": False,
            "can_execute_tool": False,
            "can_modify_source": False,
            "can_authorize_action": False,
            "can_apply_candidate": False,
            "operator_authority_unchanged": True,
        },
    }


def build_background_cognition_policy() -> dict[str, Any]:
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "safe_operations": sorted(BACKGROUND_SAFE_OPERATIONS),
        "default_max_cycles_per_hour": 4,
        "default_max_open_cycles": 1,
        "default_minimum_interval_seconds": 60,
        "authority_boundary": deepcopy(evaluate_background_cognition_admission(operation="REST")["authority_boundary"]),
    }


__all__ = [
    "CONTRACT_VERSION",
    "BACKGROUND_SAFE_OPERATIONS",
    "evaluate_background_cognition_admission",
    "build_background_cognition_policy",
]
