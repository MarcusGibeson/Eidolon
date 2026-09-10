from __future__ import annotations

from typing import Any, Mapping
from initiative_backlog_scheduler import explain_selection as _implementation

VERSION = "1409.9"
TITLE = 'Initiative Explanation'
PHASE = 'initiative_backlog_scheduling'
IMPLEMENTATION = 'initiative_backlog_scheduler' + "." + 'explain_selection'

def evaluate(*args: Any, **kwargs: Any):
    kwargs.setdefault("version", VERSION)
    return _implementation(*args, **kwargs)

def inspect(project_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state=dict(project_state or {})
    key='initiative_explanation'
    row=dict(state.get(key) or {})
    return {"active": True, "ok": bool(row), "status": "initiative_explanation_found" if row else "initiative_explanation_missing", "record": row, "action_executed": False, "source_mutation_authorized": False, "project_mutation_authorized": False, "release_authorized": False, "independent_authority_granted": False}

__all__=["VERSION","TITLE","PHASE","IMPLEMENTATION","evaluate","inspect"]
