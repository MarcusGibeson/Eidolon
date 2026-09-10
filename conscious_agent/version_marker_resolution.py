"""Static resolution for release metadata markers.

The release checks use this helper to recognize both historical literal markers and
active markers that import the authoritative values from ``release_metadata``.
It never imports or executes the inspected module.
"""
from __future__ import annotations

import ast
from typing import Iterable


def resolve_static_marker(
    text: str,
    marker: str,
    *,
    expected: str,
    accepted_release_symbols: Iterable[str],
) -> str | None:
    """Resolve a string marker without executing the source being inspected.

    Accepted forms include a literal assignment, a direct import alias from
    ``release_metadata``, or assignment chains that end at one of the accepted
    authoritative release symbols. Unknown expressions fail closed.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None

    release_imports: dict[str, str] = {}
    assignments: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "release_metadata":
            for alias in node.names:
                release_imports[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            assignments[node.targets[0].id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            assignments[node.target.id] = node.value

    accepted = set(accepted_release_symbols)

    def resolve_name(name: str, seen: set[str]) -> str | None:
        if name in seen:
            return None
        seen = {*seen, name}
        imported = release_imports.get(name)
        if imported in accepted:
            return expected
        expr = assignments.get(name)
        if expr is None:
            return None
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return expr.value
        if isinstance(expr, ast.Name):
            return resolve_name(expr.id, seen)
        return None

    return resolve_name(marker, set())


def marker_matches_runtime_version(text: str, marker: str, expected: str) -> bool:
    return resolve_static_marker(
        text,
        marker,
        expected=expected,
        accepted_release_symbols=("RUNTIME_VERSION",),
    ) == expected


def marker_matches_runtime_tag(text: str, marker: str, expected: str) -> bool:
    return resolve_static_marker(
        text,
        marker,
        expected=expected,
        accepted_release_symbols=("RUNTIME_VERSION_TAG",),
    ) == expected
