from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any

from verification_evidence import ENV_EVIDENCE_FILE, evidence_stage_report, load_evidence_bundle

from release_metadata import RUNTIME_VERSION, RUNTIME_MILESTONE, NEXT_RECOMMENDED_ARC as RUNTIME_NEXT_ARC
from source_project_metadata import load_source_project_metadata

MODULE_VERSION = "1078.7"
CHECK_ID = "release-baseline-stabilization-v1"
MILESTONE = "v1078.7 Release Baseline Stabilization"
NEXT_ARC = "v1078.8 Registry, Navigation, and Smoke Consolidation"



_PYTHON_SYNTAX_EVIDENCE_CACHE: dict[str, tuple[list[Path], list[str], dict[str, Any]]] = {}


def _python_syntax_evidence(root: Path) -> tuple[list[Path], list[str], dict[str, Any]]:
    """Reuse the attested outer compile stage when available.

    Standalone historical smoke checks still parse every Python file. During an
    authoritative release graph, the HMAC-attested compile report already
    proves the exact source snapshot compiled once without source mutation, so
    repeating the same AST scan in multiple historical checks adds time but no
    coverage.
    """
    evidence_path = os.environ.get(ENV_EVIDENCE_FILE, "")
    cache_key = f"{root.resolve()}::{evidence_path}"
    cached = _PYTHON_SYNTAX_EVIDENCE_CACHE.get(cache_key)
    if cached is not None:
        paths, failures, metadata = cached
        return list(paths), list(failures), dict(metadata)

    py_files = sorted((root / "conscious_agent").rglob("*.py")) + sorted((root / "tools").rglob("*.py"))
    bundle, validation = load_evidence_bundle(evidence_path, expected_root=root, expected_purpose="release")
    compile_report = evidence_stage_report(bundle, "python-compile")
    if (
        validation.get("valid") is True
        and isinstance(compile_report, dict)
        and compile_report.get("ok") is True
        and compile_report.get("status") == "pass"
        and compile_report.get("source_tree_mutation_count") == 0
        and compile_report.get("source_tree_bytecode_written") is False
        and compile_report.get("compile_execution_count") == 1
    ):
        result = (py_files, [], {
            "mode": "attested_outer_python_compile",
            "evidence_valid": True,
            "compile_execution_count": 1,
        })
    else:
        failures: list[str] = []
        for path in py_files:
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError) as exc:
                failures.append(f"{path.relative_to(root)}: {exc}")
        result = (py_files, failures, {
            "mode": "standalone_full_ast_parse",
            "evidence_valid": bool(validation.get("valid")),
            "compile_execution_count": 0,
        })
    _PYTHON_SYNTAX_EVIDENCE_CACHE[cache_key] = (list(result[0]), list(result[1]), dict(result[2]))
    return list(result[0]), list(result[1]), dict(result[2])

def _row(name: str, ok: bool, actual: Any = None) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "actual": actual}


def build_release_baseline_stabilization_report(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    rows: list[dict[str, Any]] = []

    py_files, syntax_errors, syntax_evidence = _python_syntax_evidence(root)
    rows.append(_row("full-python-syntax", not syntax_errors, {"failures": syntax_errors, **syntax_evidence}))

    from smoke_registry_check_rows import SMOKE_REGISTRY_CHECK_ROW_SPECS
    smoke_names = {row.name for row in SMOKE_REGISTRY_CHECK_ROW_SPECS}
    rows.append(_row("v1078.6-smoke-registered", "runtime-compile-and-live-version-truth-repair-v1" in smoke_names, sorted(smoke_names)[-5:]))
    rows.append(_row("v1078.7-smoke-registered", CHECK_ID in smoke_names, sorted(smoke_names)[-5:]))

    from dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_v1 import build_report
    predecessor = build_report(root, expected_version=RUNTIME_VERSION, run_http=False)
    rows.append(_row("v1078.5-historical-gate-compatible", predecessor.get("ok") is True, predecessor.get("rows")))

    projects = load_source_project_metadata(root)
    from project_manager import get_active_project, project_context_text
    from api_server import build_status_payload
    active_project = get_active_project()
    declared_active = str(projects.get("active_project") or "")
    active_name = str((active_project or {}).get("name") or "")
    rows.append(_row("active-project-resolves", bool(active_project) and active_name == declared_active, {"declared": declared_active, "resolved": active_name}))
    context_text = project_context_text(limit_items=2)
    rows.append(_row("active-project-context-renders", "No active project is configured" not in context_text and active_name in context_text, context_text.splitlines()[:6]))
    status_payload = build_status_payload()
    api_active = status_payload.get("active_project") or {}
    rows.append(_row("api-status-active-project", isinstance(api_active, dict) and api_active.get("name") == active_name and bool(active_name), api_active))
    def collect_active_fields(value: Any, key: str) -> list[Any]:
        found: list[Any] = []
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                if child_key == key:
                    found.append(child_value)
                if child_key not in {"release_notes", "history", "notes"}:
                    found.extend(collect_active_fields(child_value, key))
        elif isinstance(value, list):
            for item in value:
                found.extend(collect_active_fields(item, key))
        return found
    active_next_steps = collect_active_fields(projects, "next_steps")
    active_milestones = collect_active_fields(projects, "current_milestone") + collect_active_fields(projects, "name")
    active_next_arcs = collect_active_fields(projects, "next_recommended_arc")
    rows.append(_row("planner-no-v1060-next-step", all("v1060.0 Manifest-Generated Dispatch Fixture Harness Isolation v1" not in json.dumps(value) for value in active_next_steps), active_next_steps))
    rows.append(_row("planner-current-milestone", any(RUNTIME_MILESTONE == value for value in active_milestones), active_milestones))
    rows.append(_row("planner-next-arc", bool(active_next_arcs) and all(value == RUNTIME_NEXT_ARC for value in active_next_arcs), active_next_arcs))

    smoke_text = (root / "tools/smoke_check.py").read_text(encoding="utf-8", errors="ignore")
    rows.append(_row("timeouts-isolated-by-default", 'EIDOLON_SMOKE_IN_PROCESS' in smoke_text and 'EIDOLON_SMOKE_ISOLATED' not in smoke_text, None))

    from runtime_compile_and_live_version_truth_repair import build_runtime_compile_and_live_version_truth_repair_report
    repair = build_runtime_compile_and_live_version_truth_repair_report(root)
    safety_rows = [row for row in repair.get("rows", []) if row.get("name") == "safety-boundary-inspected"]
    rows.append(_row("safety-claim-inspected", bool(safety_rows) and safety_rows[0].get("ok") is True, safety_rows))

    active_versions = {
        "api": __import__("api_server").API_VERSION,
        "dashboard": __import__("dashboard").DASHBOARD_VERSION,
        "stable_loop_audit": __import__("stable_loop_audit").AUDIT_VERSION,
        "stable_loop_guardrails": __import__("stable_loop_guardrails").STABLE_LOOP_GUARDRAIL_VERSION,
    }
    rows.append(_row("active-runtime-versions-current", all(value == RUNTIME_VERSION for value in active_versions.values()), {"runtime": RUNTIME_VERSION, **active_versions}))

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
    }
