from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    _store_root: Any



def _runtime_test_path(pid: str, rev: int, runtime_root=None, *, _deps: SymbolDependencies) -> Path:
    return _deps._store_root(runtime_root) / 'browser_runtime_tests' / pid / f'revision-{int(rev)}.json'


def _runtime_operation_path(pid: str, rev: int, runtime_root=None, *, _deps: SymbolDependencies) -> Path:
    return _deps._store_root(runtime_root) / 'browser_runtime_operations' / pid / f'revision-{int(rev)}.json'
