from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from typing import Any

SELF_MAINTENANCE_GOVERNANCE_GATES_VERSION = RUNTIME_VERSION
GOVERNANCE_GATE_BOUNDARIES: dict[str, bool] = {
    "governance_gates_self_approve": False,
    "governance_gates_continue_automatically": False,
    "governance_gates_mutate_memory": False,
    "governance_gates_alter_identity": False,
    "governance_gates_alter_personality": False,
    "governance_gates_invoke_models": False,
    "governance_gates_execute_rollback": False,
    "governance_gates_publish_release": False,
    "governance_gates_schedule_hidden_work": False,
    "governance_gates_review_only": True,
}

FORBIDDEN_ACTIONS = [
    "self-approval",
    "automatic continuation",
    "memory mutation",
    "identity mutation",
    "personality mutation",
    "default local model invocation",
    "automatic rollback",
    "release publishing",
    "hidden work scheduling",
]

def summarize_governance_gates() -> dict[str, Any]:
    false_ok = all(value is False for key, value in GOVERNANCE_GATE_BOUNDARIES.items() if key.startswith("governance_gates_") and key != "governance_gates_review_only")
    return {
        "version": SELF_MAINTENANCE_GOVERNANCE_GATES_VERSION,
        "state": "governance_boundary_gate_extraction",
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "boundaries": dict(GOVERNANCE_GATE_BOUNDARIES),
        "review_only": True,
        "writes_files": False,
        "changes_behavior": False,
        "ok": false_ok and GOVERNANCE_GATE_BOUNDARIES.get("governance_gates_review_only") is True,
    }

def governance_gate_tokens() -> list[str]:
    return list(FORBIDDEN_ACTIONS)
