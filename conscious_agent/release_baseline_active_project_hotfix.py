from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from release_metadata import RUNTIME_VERSION, RUNTIME_MILESTONE, NEXT_RECOMMENDED_ARC
from source_project_metadata import load_source_project_metadata

MODULE_VERSION = "1078.7.1"
CHECK_ID = "release-baseline-active-project-hotfix-v1"


def _version_key(value: str) -> tuple[int, ...]:
    parts = str(value).strip().lstrip("v").split(".")
    if not parts or any(not part.isdigit() for part in parts):
        return ()
    return tuple(int(part) for part in parts)


def _is_compatible_runtime(value: str, minimum: str = MODULE_VERSION) -> bool:
    value_key = _version_key(value)
    minimum_key = _version_key(minimum)
    return bool(value_key and minimum_key) and value_key >= minimum_key


def _row(name: str, ok: bool, actual: Any = None) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "actual": actual}


def build_release_baseline_active_project_hotfix_report(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    rows: list[dict[str, Any]] = []

    from release_baseline_stabilization import _python_syntax_evidence
    py_files, syntax_errors, syntax_evidence = _python_syntax_evidence(root)
    rows.append(_row("full-python-syntax", not syntax_errors, {"failures": syntax_errors, **syntax_evidence}))

    projects = load_source_project_metadata(root)
    declared = str(projects.get("active_project") or "")
    current_project = projects.get("current_project") or {}
    project_names = [str(item.get("name") or "") for item in projects.get("projects", []) if isinstance(item, dict)]
    rows.append(_row("root-active-project-exact", bool(declared) and declared == current_project.get("name") and declared in project_names, {"declared": declared, "current": current_project.get("name"), "projects": project_names}))

    from project_manager import get_active_project, project_context_text
    resolved = get_active_project()
    resolved_name = str((resolved or {}).get("name") or "")
    rows.append(_row("project-manager-resolves", bool(resolved) and resolved_name == declared, resolved))
    context = project_context_text(limit_items=2)
    rows.append(_row("project-context-renders", "No active project is configured" not in context and resolved_name in context, context.splitlines()[:8]))

    from api_server import build_status_payload
    api_payload = build_status_payload()
    api_project = api_payload.get("active_project") or {}
    rows.append(_row("api-status-resolves-active-project", isinstance(api_project, dict) and api_project.get("name") == declared, api_project))

    from release_baseline_stabilization import build_release_baseline_stabilization_report
    predecessor = build_release_baseline_stabilization_report(root)
    rows.append(_row("v1078.7-baseline-gate-hardened", predecessor.get("ok") is True, [row for row in predecessor.get("rows", []) if not row.get("ok")]))

    from project_metadata_active_context_repair import build_metadata_integrity_board_smoke_gate
    metadata = build_metadata_integrity_board_smoke_gate(root)
    rows.append(_row("metadata-integrity-board-clean", metadata.get("ok") is True, [row for row in metadata.get("rows", []) if row.get("status") != "pass"]))

    smoke_text = (root / "tools/smoke_check.py").read_text(encoding="utf-8", errors="ignore")
    registry_text = (root / "tools/smoke_registry_check_rows.py").read_text(encoding="utf-8", errors="ignore")
    rows.append(_row("hotfix-smoke-registered", CHECK_ID in registry_text and "run_release_baseline_active_project_hotfix_check" in smoke_text, None))

    planner_blob = json.dumps({
        "next_steps": projects.get("next_steps"),
        "notes": projects.get("notes"),
        "current_project": {"next_steps": current_project.get("next_steps"), "notes": current_project.get("notes")},
    })
    rows.append(_row("planner-no-v1060-guidance", "v1060" not in planner_blob, planner_blob))
    rows.append(_row(
        "runtime-version-compatible",
        _is_compatible_runtime(RUNTIME_VERSION),
        {"runtime_version": RUNTIME_VERSION, "minimum_compatible_version": MODULE_VERSION},
    ))
    compatibility_cases = {
        MODULE_VERSION: True,
        "1078.8": True,
        "1079.0": True,
        "1078.7": False,
        "invalid": False,
    }
    compatibility_results = {version: _is_compatible_runtime(version) for version in compatibility_cases}
    rows.append(_row(
        "newer-runtime-compatibility-regression",
        compatibility_results == compatibility_cases,
        {"minimum_compatible_version": MODULE_VERSION, "cases": compatibility_results},
    ))
    rows.append(_row(
        "runtime-metadata-current",
        projects.get("current_milestone") == RUNTIME_MILESTONE
        and projects.get("next_recommended_arc") == NEXT_RECOMMENDED_ARC,
        {"runtime_version": RUNTIME_VERSION, "milestone": projects.get("current_milestone"), "next": projects.get("next_recommended_arc")},
    ))

    ok = all(row["ok"] for row in rows)
    return {
        "version": MODULE_VERSION,
        "check_id": CHECK_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "rows": rows,
        "python_file_count": len(py_files),
        "python_syntax_evidence": syntax_evidence,
        "release_authorized": False,
        "autonomy_expanded": False,
        "source_writes_performed_by_report": False,
        "operator_review_required": True,
    }
