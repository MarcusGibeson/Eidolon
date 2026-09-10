from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    sha256: Any



def digest(value: Any, *, _deps: SymbolDependencies) -> str:
    return _deps.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')).hexdigest()


def valid_digest(value: Any, *, _deps: SymbolDependencies) -> bool:
    text = str(value or '').strip().lower()
    return len(text) == 64 and all((c in '0123456789abcdef' for c in text))
