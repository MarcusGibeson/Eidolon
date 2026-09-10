from __future__ import annotations

from typing import Any, Mapping
from desktop_daily_use import provider_setup_assessment as _implementation

VERSION = "1445.9"
TITLE = 'Provider Setup'
PHASE = 'desktop_product_daily_use'
IMPLEMENTATION = 'desktop_daily_use' + "." + 'provider_setup_assessment'

def evaluate(*args: Any, **kwargs: Any):
    kwargs.setdefault("version", VERSION)
    return _implementation(*args, **kwargs)

def inspect(project_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state=dict(project_state or {})
    key='provider_setup'
    row=dict(state.get(key) or {})
    return {"active": True, "ok": bool(row), "status": "provider_setup_found" if row else "provider_setup_missing", "record": row, "action_executed": False, "source_mutation_authorized": False, "project_mutation_authorized": False, "release_authorized": False, "independent_authority_granted": False}

__all__=["VERSION","TITLE","PHASE","IMPLEMENTATION","evaluate","inspect"]
