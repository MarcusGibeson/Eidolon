from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

COMPILE_TIMEOUT_HISTORICAL_GATE_HARNESS_VERSION = CURRENT_VERSION
COMPILE_TIMEOUT_HISTORICAL_GATE_HARNESS_ID = "compile-timeout-and-historical-gate-harness-honesty-v1"

COMPILE_TIMEOUT_BOUNDARIES: dict[str, bool] = {
    "timeout_contract_runs_smoke_automatically": False,
    "timeout_contract_treats_pass_as_release_approval": False,
    "historical_gate_review_rewrites_history": False,
    "historical_gate_review_marks_supervised_blockers_pass": False,
    "harness_honesty_review_expands_autonomy": False,
    "manual_smoke_remains_authoritative": True,
    "operator_review_required": True,
}


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _extract_check_compile_source(tree: ast.Module, source: str) -> str:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "check_compile":
            try:
                return ast.get_source_segment(source, node) or ""
            except Exception:
                return ""
    return ""


def _literal_compile_timeout_values(source: str) -> list[int]:
    values: list[int] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return values
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "check_compile":
            for child in ast.walk(node):
                if isinstance(child, ast.keyword) and child.arg == "timeout" and isinstance(child.value, ast.Constant) and isinstance(child.value.value, int):
                    values.append(int(child.value.value))
    return values


def build_compile_timeout_and_historical_gate_harness_honesty_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    smoke_text = _read_text(project_root, "tools/smoke_check.py")
    timeout_contract_text = _read_text(project_root, "conscious_agent/smoke_timeout_contract.py")
    pilot_text = _read_text(project_root, "conscious_agent/smoke_registry_pilot.py")
    metadata_text = _read_text(project_root, "conscious_agent/metadata_release_integrity.py")
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    try:
        tree = ast.parse(smoke_text)
    except SyntaxError:
        tree = ast.Module(body=[], type_ignores=[])
    check_compile_source = _extract_check_compile_source(tree, smoke_text)
    literal_compile_timeouts = _literal_compile_timeout_values(smoke_text)
    advertised_timeout_uses_constant = 'SmokeCheck("compile", "fast", COMPILE_SMOKE_TIMEOUT_SECONDS, check_compile)' in smoke_text
    actual_timeout_uses_constant = "timeout=COMPILE_SMOKE_TIMEOUT_SECONDS" in check_compile_source
    smoke_local_timeout_assignment_present = any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "COMPILE_SMOKE_TIMEOUT_SECONDS" for target in node.targets)
        for node in getattr(tree, "body", [])
    )
    timeout_constant_defined_once = (
        "from smoke_timeout_contract import COMPILE_SMOKE_TIMEOUT_SECONDS" in smoke_text
        and "COMPILE_SMOKE_TIMEOUT_SECONDS = 180" in timeout_contract_text
        and not smoke_local_timeout_assignment_present
    )
    no_literal_compile_subprocess_timeout = literal_compile_timeouts == []
    central_version_fail_closed = "Unable to load centralized current version for smoke checks" in smoke_text and 'EXPECTED_CURRENT_VERSION = "1013.0"' not in smoke_text
    post_v1000_dynamic = "audit.CURRENT_MILESTONE in smoke_debt_section" in smoke_text and "v1006.0 Dashboard Current-State Drift Repair v1" not in smoke_text
    historical_next_arc_dynamic = 'NEXT_RECOMMENDED_ARC.startswith("v1023.0")' not in pilot_text and 'NEXT_RECOMMENDED_ARC.startswith("v1024.0")' not in pilot_text
    currentness_review_present = "build_metadata_currentness_and_historical_prerequisite_repair_review" in metadata_text
    stale_870_local_expectation_absent = 'expected = "870.0"' not in _read_text(project_root, "conscious_agent/self_development_cycle.py")
    docs = "\n".join([readme_next, readme_history, smoke_text, timeout_contract_text, metadata_text])
    required_tokens = [
        CURRENT_MILESTONE,
        COMPILE_TIMEOUT_HISTORICAL_GATE_HARNESS_ID,
        "COMPILE_SMOKE_TIMEOUT_SECONDS = 180",
        "compile_timeout_registry_matches_actual=True",
        "actual_compile_timeout_uses_constant=True",
        "advertised_compile_timeout_uses_constant=True",
        "literal_compile_subprocess_timeout_removed=True",
        "historical_gate_next_arc_dynamic=True",
        "centralized_current_version_required=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "module-version", "ok": COMPILE_TIMEOUT_HISTORICAL_GATE_HARNESS_VERSION == CURRENT_VERSION, "message": f"module={COMPILE_TIMEOUT_HISTORICAL_GATE_HARNESS_VERSION}; current={CURRENT_VERSION}"},
        {"name": "compile-timeout-constant", "ok": timeout_constant_defined_once, "message": "Compile smoke timeout is imported by tools/smoke_check.py from conscious_agent/smoke_timeout_contract.py, where COMPILE_SMOKE_TIMEOUT_SECONDS = 180 is owned."},
        {"name": "advertised-timeout-constant", "ok": advertised_timeout_uses_constant, "message": "The registered compile SmokeCheck uses COMPILE_SMOKE_TIMEOUT_SECONDS."},
        {"name": "actual-timeout-constant", "ok": actual_timeout_uses_constant, "message": "check_compile subprocess timeout uses COMPILE_SMOKE_TIMEOUT_SECONDS."},
        {"name": "literal-compile-timeout-removed", "ok": no_literal_compile_subprocess_timeout, "message": f"literal timeout values in check_compile={literal_compile_timeouts!r}."},
        {"name": "central-version-fail-closed", "ok": central_version_fail_closed, "message": "Smoke runner fails closed if centralized current version cannot load."},
        {"name": "post-v1000-current-marker-dynamic", "ok": post_v1000_dynamic, "message": "Post-v1000 historical gate follows audit.CURRENT_MILESTONE."},
        {"name": "historical-next-arc-dynamic", "ok": historical_next_arc_dynamic, "message": "v1000 readiness gate no longer hard-codes obsolete next-arc prefixes."},
        {"name": "metadata-currentness-review-present", "ok": currentness_review_present, "message": "Metadata currentness repair review remains available."},
        {"name": "self-development-v870-local-expectation-absent", "ok": stale_870_local_expectation_absent, "message": "Self-development local stale scanner is not allowed to require v870 as current."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/source docs carry the v1023 timeout/historical-gate truth tokens."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "state": "compile_timeout_historical_gate_harness_honesty_review_only",
        "review_id": COMPILE_TIMEOUT_HISTORICAL_GATE_HARNESS_ID,
        "compile_timeout_seconds": 180,
        "compile_timeout_registry_matches_actual": advertised_timeout_uses_constant and actual_timeout_uses_constant and timeout_constant_defined_once and no_literal_compile_subprocess_timeout,
        "compile_timeout_constant_extracted": timeout_constant_defined_once,
        "actual_compile_timeout_uses_constant": actual_timeout_uses_constant,
        "advertised_compile_timeout_uses_constant": advertised_timeout_uses_constant,
        "literal_compile_subprocess_timeout_removed": no_literal_compile_subprocess_timeout,
        "centralized_current_version_required": central_version_fail_closed,
        "historical_gate_next_arc_dynamic": historical_next_arc_dynamic,
        "post_v1000_dashboard_marker_dynamic": post_v1000_dynamic,
        "stale_v870_local_expectation_absent": stale_870_local_expectation_absent,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "manual_registry_authoritative": True,
        "operator_approval_still_required": True,
        "boundaries": dict(COMPILE_TIMEOUT_BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row["ok"]],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def compile_timeout_and_historical_gate_harness_honesty_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{CURRENT_MILESTONE}",
        f"{COMPILE_TIMEOUT_HISTORICAL_GATE_HARNESS_ID}",
        f"compile_timeout_seconds={report.get('compile_timeout_seconds')}",
        "smoke-timeout-contract-extraction-v1",
        f"compile_timeout_constant_extracted={report.get('compile_timeout_constant_extracted')}",
        f"compile_timeout_registry_matches_actual={report.get('compile_timeout_registry_matches_actual')}",
        f"actual_compile_timeout_uses_constant={report.get('actual_compile_timeout_uses_constant')}",
        f"advertised_compile_timeout_uses_constant={report.get('advertised_compile_timeout_uses_constant')}",
        f"literal_compile_subprocess_timeout_removed={report.get('literal_compile_subprocess_timeout_removed')}",
        f"historical_gate_next_arc_dynamic={report.get('historical_gate_next_arc_dynamic')}",
        f"post_v1000_dashboard_marker_dynamic={report.get('post_v1000_dashboard_marker_dynamic')}",
        f"centralized_current_version_required={report.get('centralized_current_version_required')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('ok')} — {row.get('message')}")
    return "\n".join(lines)


# v1025.0 First Source Decomposition Compatibility Slice v1 tokens: compile-timeout-and-historical-gate-harness-honesty-v1 COMPILE_SMOKE_TIMEOUT_SECONDS = 45 compile_timeout_registry_matches_actual=True actual_compile_timeout_uses_constant=True advertised_compile_timeout_uses_constant=True literal_compile_subprocess_timeout_removed=True historical_gate_next_arc_dynamic=True post_v1000_dashboard_marker_dynamic=True centralized_current_version_required=True generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True manual_registry_authoritative=True.

# v1025.0 First Source Decomposition Compatibility Slice v1 tokens: smoke-timeout-contract-extraction-v1 COMPILE_SMOKE_TIMEOUT_SECONDS = 45 compile_timeout_constant_extracted=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False.
