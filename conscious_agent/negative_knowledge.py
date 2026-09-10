from __future__ import annotations

from typing import Any, Mapping
from outcome_learning import build_negative_knowledge as _implementation

VERSION = "1414.9"
TITLE = 'Negative Knowledge'
PHASE = 'learning_from_outcomes'
IMPLEMENTATION = 'outcome_learning' + "." + 'build_negative_knowledge'

def evaluate(*args: Any, **kwargs: Any):
    kwargs.setdefault("version", VERSION)
    return _implementation(*args, **kwargs)

def inspect(project_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state=dict(project_state or {})
    key='negative_knowledge'
    row=dict(state.get(key) or {})
    return {"active": True, "ok": bool(row), "status": "negative_knowledge_found" if row else "negative_knowledge_missing", "record": row, "action_executed": False, "source_mutation_authorized": False, "project_mutation_authorized": False, "release_authorized": False, "independent_authority_granted": False}

__all__=["VERSION","TITLE","PHASE","IMPLEMENTATION","evaluate","inspect"]
