from __future__ import annotations

from typing import Any, Mapping
from desktop_daily_use import native_desktop_shell_contract as _implementation

VERSION = "1441.9"
TITLE = 'Native Desktop Shell'
PHASE = 'desktop_product_daily_use'
IMPLEMENTATION = 'desktop_daily_use' + "." + 'native_desktop_shell_contract'

def evaluate(*args: Any, **kwargs: Any):
    kwargs.setdefault("version", VERSION)
    return _implementation(*args, **kwargs)

def inspect(project_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state=dict(project_state or {})
    key='native_desktop_shell'
    row=dict(state.get(key) or {})
    return {"active": True, "ok": bool(row), "status": "native_desktop_shell_found" if row else "native_desktop_shell_missing", "record": row, "action_executed": False, "source_mutation_authorized": False, "project_mutation_authorized": False, "release_authorized": False, "independent_authority_granted": False}

__all__=["VERSION","TITLE","PHASE","IMPLEMENTATION","evaluate","inspect"]
