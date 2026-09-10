from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    _version_key: Any
    _working_source_version: Any



def successor_progress(root_dir: str | Path, *, successor_version: str, successor_surface: str, _deps: SymbolDependencies) -> dict[str, Any]:
    root = Path(root_dir)
    working_version = _deps._working_source_version(root)
    expected_started = _deps._version_key(working_version) >= _deps._version_key(successor_version)
    started = (root / successor_surface).is_file()
    return {'working_source_version': working_version, 'successor_version': successor_version, 'successor_surface': successor_surface, 'expected_started': expected_started, 'started': started, 'coherent': started == expected_started}


def retained_checkpoint_progress(root_dir: str | Path, *, checkpoint_version: str, successor_version: str, successor_surface: str, _deps: SymbolDependencies) -> dict[str, Any]:
    progress = successor_progress(root_dir, successor_version=successor_version, successor_surface=successor_surface, _deps=_deps)
    progress['checkpoint_version'] = checkpoint_version
    progress['checkpoint_retained'] = _deps._version_key(progress['working_source_version']) >= _deps._version_key(checkpoint_version)
    progress['coherent'] = progress['checkpoint_retained'] and progress['coherent']
    return progress
