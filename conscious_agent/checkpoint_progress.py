from __future__ import annotations

import ast
from pathlib import Path
from typing import Any
from checkpoint_progress_progress_helpers import (
    SymbolDependencies as _CheckpointProgressProgressHelpersSymbolDependencies,
    retained_checkpoint_progress as _retained_checkpoint_progress_implementation,
    successor_progress as _successor_progress_implementation,
)



def _version_key(value: str) -> tuple[int, ...]:
    parts = value.strip().lstrip("v").split(".")
    return tuple(int(part) for part in parts)


def _working_source_version(root: Path) -> str:
    metadata_path = root / "conscious_agent" / "release_metadata.py"
    tree = ast.parse(metadata_path.read_text(encoding="utf-8"), filename=str(metadata_path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "WORKING_SOURCE_VERSION" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise ValueError("WORKING_SOURCE_VERSION is missing from release metadata")


def _build_checkpoint_progress_progress_helpers_dependencies() -> _CheckpointProgressProgressHelpersSymbolDependencies:
    return _CheckpointProgressProgressHelpersSymbolDependencies(
        _version_key=_version_key,
        _working_source_version=_working_source_version,
    )

def successor_progress(root_dir: str | Path, *, successor_version: str, successor_surface: str) -> dict[str, Any]:
    return _successor_progress_implementation(root_dir, successor_version=successor_version, successor_surface=successor_surface, _deps=_build_checkpoint_progress_progress_helpers_dependencies())



def retained_checkpoint_progress(root_dir: str | Path, *, checkpoint_version: str, successor_version: str, successor_surface: str) -> dict[str, Any]:
    return _retained_checkpoint_progress_implementation(root_dir, checkpoint_version=checkpoint_version, successor_version=successor_version, successor_surface=successor_surface, _deps=_build_checkpoint_progress_progress_helpers_dependencies())

