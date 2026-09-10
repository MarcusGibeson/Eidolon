from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    Mapping: Any
    _atomic_json: Any
    _digest: Any



def _operation_valid(record: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> bool:
    supplied = str(record.get('operation_digest') or '')
    return bool(supplied and supplied == _deps._digest({k: v for k, v in record.items() if k != 'operation_digest'}))


def _write_operation(path: Path, payload: dict[str, Any], *, _deps: SymbolDependencies) -> dict[str, Any]:
    payload = dict(payload)
    payload['operation_digest'] = _deps._digest(payload)
    _deps._atomic_json(path, payload)
    return payload
