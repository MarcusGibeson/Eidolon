from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    CONTRACT_VERSION: Any
    Iterable: Any
    Mapping: Any
    append_memory_records: Any
    recover_memory_append_journal: Any



def append_memory_journal(memory_file: str | Path, records: _deps.Iterable[_deps.Mapping[str, Any]], *, _deps: SymbolDependencies) -> dict[str, Any]:
    report = _deps.append_memory_records(memory_file, records)
    return {'contract_version': _deps.CONTRACT_VERSION, **report, 'canonical_json_array_preserved': True, 'full_history_rewrite': False, 'authority_granted': False}


def recover_append_journal(memory_file: str | Path, *, _deps: SymbolDependencies) -> dict[str, Any]:
    return {'contract_version': _deps.CONTRACT_VERSION, **_deps.recover_memory_append_journal(memory_file), 'authority_granted': False}
