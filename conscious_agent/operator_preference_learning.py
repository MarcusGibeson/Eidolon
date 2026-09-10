from __future__ import annotations

from typing import Any, Mapping
from outcome_learning import learn_operator_preferences as _implementation

VERSION = "1417.9"
TITLE = 'Operator Preference Learning'
PHASE = 'learning_from_outcomes'
IMPLEMENTATION = 'outcome_learning' + "." + 'learn_operator_preferences'

def evaluate(*args: Any, **kwargs: Any):
    kwargs.setdefault("version", VERSION)
    return _implementation(*args, **kwargs)

def inspect(project_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state=dict(project_state or {})
    key='operator_preference_learning'
    row=dict(state.get(key) or {})
    return {"active": True, "ok": bool(row), "status": "operator_preference_learning_found" if row else "operator_preference_learning_missing", "record": row, "action_executed": False, "source_mutation_authorized": False, "project_mutation_authorized": False, "release_authorized": False, "independent_authority_granted": False}

__all__=["VERSION","TITLE","PHASE","IMPLEMENTATION","evaluate","inspect"]
