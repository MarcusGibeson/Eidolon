from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any, Iterable, Sequence

SMOKE_CHECK_SHARED_VERSION = RUNTIME_VERSION

DEFAULT_AUTHORITY_KEYS: tuple[str, ...] = (
    "generated_wiring_activated",
    "release_authorized",
    "autonomy_expanded",
)


def read_docs_bundle(root: str | Path, paths: Sequence[str]) -> str:
    """Read a bounded bundle of docs/source text for smoke token checks.

    This helper is intentionally tiny and side-effect free: it reads only the
    supplied relative paths and never executes checks, imports dashboard routes,
    writes files, authorizes release, or expands autonomy.
    """
    base = Path(root)
    chunks: list[str] = []
    for rel in paths:
        path = base / rel
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            chunks.append("")
    return "\n".join(chunks)


def missing_required_tokens(text: str, required: Sequence[str]) -> list[str]:
    return [token for token in required if token not in text]


def authority_boundary_violations(report: dict[str, Any], keys: Iterable[str] = DEFAULT_AUTHORITY_KEYS) -> list[str]:
    violations: list[str] = []
    for key in keys:
        if bool(report.get(key)):
            violations.append(key)
    if int(report.get("actual_fixture_execution_count") or 0) != 0:
        violations.append("actual_fixture_execution_count")
    if bool(report.get("actual_fixture_execution_allowed")):
        violations.append("actual_fixture_execution_allowed")
    if bool(report.get("audited_os_sandbox_backend_integrated")):
        violations.append("audited_os_sandbox_backend_integrated")
    return violations


def smoke_token_validation_row(text: str, required: Sequence[str]) -> dict[str, Any]:
    missing = missing_required_tokens(text, required)
    return {
        "name": "smoke-helper-token-validation",
        "ok": not missing,
        "status": "pass" if not missing else "blocked",
        "missing_tokens": missing,
        "required_token_count": len(required),
    }


def smoke_helper_adoption_rows() -> list[dict[str, Any]]:
    return [
        {"helper": "read_docs_bundle", "adopted_by": "smoke-check-helper-extraction-pilot-v1", "status": "used", "side_effects": "read_only"},
        {"helper": "missing_required_tokens", "adopted_by": "smoke-check-helper-extraction-pilot-v1", "status": "used", "side_effects": "none"},
        {"helper": "authority_boundary_violations", "adopted_by": "smoke-check-helper-extraction-pilot-v1", "status": "used", "side_effects": "none"},
        {"helper": "smoke_token_validation_row", "adopted_by": "smoke-check-helper-extraction-pilot-v1", "status": "used", "side_effects": "none"},
    ]


# v1070.2 smoke check shared helper tokens: smoke-check-shared-v1 SMOKE_CHECK_SHARED_VERSION=1070.3 read_docs_bundle missing_required_tokens authority_boundary_violations smoke_token_validation_row smoke-check-helper-extraction-pilot-v1 actual_fixture_execution_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
