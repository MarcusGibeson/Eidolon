from __future__ import annotations

"""v2504.1 governed registry of bounded cognitive operations."""

from copy import deepcopy
from typing import Any, Mapping

CONTRACT_VERSION = "v2504.1"

_OPERATION_ROWS = (
    {"operation": "REST", "cost": 0.02, "cooldown_cycles": 0, "mutations": (), "requires": (), "communicative": False},
    {"operation": "RECALL_MEMORY", "cost": 0.15, "cooldown_cycles": 0, "mutations": (), "requires": ("demand_or_subject",), "communicative": False},
    {"operation": "CONTINUE_THOUGHT", "cost": 0.22, "cooldown_cycles": 0, "mutations": ("runtime_continuity",), "requires": ("unfinished_thought",), "communicative": False},
    {"operation": "RECONSIDER_BELIEF", "cost": 0.32, "cooldown_cycles": 1, "mutations": ("candidate_belief_update",), "requires": ("belief_conflict",), "communicative": False},
    {"operation": "REVIEW_GOAL", "cost": 0.28, "cooldown_cycles": 1, "mutations": ("candidate_goal_update",), "requires": ("active_goal_or_plan",), "communicative": False},
    {"operation": "PLAN", "cost": 0.36, "cooldown_cycles": 1, "mutations": ("candidate_plan_update",), "requires": ("planning_need",), "communicative": False},
    {"operation": "REPLAN", "cost": 0.40, "cooldown_cycles": 1, "mutations": ("candidate_plan_update",), "requires": ("blocked_or_conflicted_plan",), "communicative": False},
    {"operation": "INTEGRATE_EXPERIENCE", "cost": 0.24, "cooldown_cycles": 1, "mutations": ("candidate_memory_update",), "requires": ("new_experience",), "communicative": False},
    {"operation": "REVIEW_SELF_MODEL", "cost": 0.30, "cooldown_cycles": 2, "mutations": ("candidate_self_model_update",), "requires": ("self_model_evidence",), "communicative": False},
    {"operation": "RESOLVE_CONFLICT", "cost": 0.38, "cooldown_cycles": 1, "mutations": ("candidate_resolution",), "requires": ("cognitive_conflict",), "communicative": False},
    {"operation": "REFLECT", "cost": 0.26, "cooldown_cycles": 1, "mutations": ("runtime_continuity", "candidate_reflection"), "requires": ("salient_subject",), "communicative": False},
)

OPERATIONS = {row["operation"]: row for row in _OPERATION_ROWS}


def build_cognitive_operation_registry() -> dict[str, Any]:
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "operations": [deepcopy(row) for row in _OPERATION_ROWS],
        "operation_count": len(_OPERATION_ROWS),
        "default_operation": "REST",
        "authority_boundary": {
            "operation_can_authorize_action": False,
            "operation_can_execute_action": False,
            "operation_can_contact_provider": False,
            "operation_can_send_message": False,
            "operator_authority_unchanged": True,
        },
    }


def get_cognitive_operation(name: str) -> dict[str, Any]:
    key = str(name or "").strip().upper()
    if key not in OPERATIONS:
        raise ValueError("unknown cognitive operation")
    return deepcopy(OPERATIONS[key])


def verify_cognitive_operation_registry(value: Mapping[str, Any] | None = None) -> bool:
    registry = dict(value or build_cognitive_operation_registry())
    names = [row.get("operation") for row in registry.get("operations", []) if isinstance(row, Mapping)]
    return bool(
        registry.get("ok")
        and registry.get("default_operation") == "REST"
        and len(names) == len(set(names)) == len(_OPERATION_ROWS)
        and "REST" in names
        and all(0 <= float(row.get("cost", -1)) <= 1 for row in registry.get("operations", []))
        and not (registry.get("authority_boundary") or {}).get("operation_can_execute_action")
    )
