from __future__ import annotations

from typing import Any, Mapping
from unified_companion_developer import ground_commands as _implementation

VERSION = "1432.9"
TITLE = 'Command Grounding'
PHASE = 'unified_conversation_action_companion'
IMPLEMENTATION = 'unified_companion_developer' + "." + 'ground_commands'

def evaluate(*args: Any, **kwargs: Any):
    kwargs.setdefault("version", VERSION)
    return _implementation(*args, **kwargs)

def inspect(project_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state=dict(project_state or {})
    key='command_grounding'
    row=dict(state.get(key) or {})
    return {"active": True, "ok": bool(row), "status": "command_grounding_found" if row else "command_grounding_missing", "record": row, "action_executed": False, "source_mutation_authorized": False, "project_mutation_authorized": False, "release_authorized": False, "independent_authority_granted": False}

__all__=["VERSION","TITLE","PHASE","IMPLEMENTATION","evaluate","inspect"]
