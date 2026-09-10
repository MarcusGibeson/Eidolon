from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    hashlib: Any



def _digest(value: object, *, _deps: SymbolDependencies) -> str:
    return _deps.hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')).hexdigest()


def _hex_digest(value: object, *, _deps: SymbolDependencies) -> bool:
    token = str(value or '')
    return len(token) == 64 and all((ch in '0123456789abcdef' for ch in token))
