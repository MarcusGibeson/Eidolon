from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC

MODULE_VERSION = RUNTIME_VERSION
ARC_VERSION = "1067.0"
ARC_TITLE = "Generated Dispatch Promotion Readiness Ledger v1"
REVIEW_ID = "generated-dispatch-promotion-readiness-ledger-v1"
SELF_ROUTE = "/generated-dispatch-promotion-readiness-ledger"
API_ROUTE = "/api/source-surface/generated-dispatch-promotion-readiness-ledger"

SANDBOX_BACKEND_CANDIDATES: tuple[dict[str, str], ...] = (
    {"name": "bubblewrap", "command": "bwrap", "platform": "linux", "status": "candidate_requires_audited_command_contract"},
    {"name": "firejail", "command": "firejail", "platform": "linux", "status": "candidate_requires_audited_command_contract"},
    {"name": "unshare", "command": "unshare", "platform": "linux", "status": "candidate_requires_audited_command_contract"},
    {"name": "docker", "command": "docker", "platform": "container", "status": "candidate_requires_strict_flags_and_image_contract"},
    {"name": "windows-job-object", "command": "none", "platform": "windows", "status": "concept_only_not_integrated"},
)

REQUIRED_SANDBOX_CAPABILITIES: tuple[str, ...] = (
    "filesystem_isolation",
    "working_directory_confinement",
    "network_denial",
    "process_limit",
    "timeout_enforcement",
    "stdout_capture",
    "stderr_capture",
    "return_code_capture",
    "before_after_full_tree_mutation_snapshot",
    "private_runtime_path_exclusion",
    "operator_confirmation_binding",
)

AUTHORITY_BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "dashboard_get_preview_only": True,
    "api_get_preview_only": True,
    "actual_fixture_execution_attempted": False,
    "actual_fixture_execution_count": False,
    "sandbox_backend_integrated": False,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "operator_approval_required": True,
}

def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]

def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

def _check(name: str, ok: bool, message: str, **extra: Any) -> dict[str, Any]:
    row = {"name": name, "ok": bool(ok), "status": "pass" if ok else "blocked", "message": message}
    row.update(extra)
    return row

def _status(rows: list[dict[str, Any]]) -> str:
    return "pass" if all(row.get("ok") is True for row in rows) else "blocked"

def _backend_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in SANDBOX_BACKEND_CANDIDATES:
        command = candidate["command"]
        detected = bool(command != "none" and shutil.which(command))
        rows.append({
            "name": candidate["name"],
            "command": command,
            "platform": candidate["platform"],
            "detected": detected,
            "audited_command_contract_integrated": False,
            "network_denial_proven": False,
            "filesystem_isolation_proven": False,
            "execution_allowed": False,
            "classification": "detected_but_not_audited" if detected else candidate["status"],
        })
    return rows

def _base_checks(extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    checks = [
        _check("current-version", CURRENT_VERSION == MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        _check("manual-authority", AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual dashboard/API/smoke remain authoritative."),
        _check("get-preview-only", AUTHORITY_BOUNDARIES["dashboard_get_preview_only"] and AUTHORITY_BOUNDARIES["api_get_preview_only"], "Dashboard/API GET paths are preview-only."),
        _check("no-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"], "Generated wiring is not activated."),
        _check("no-release-or-autonomy", not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "No release authorization or autonomy expansion occurs."),
    ]
    if extra:
        checks.extend(extra)
    return checks

def build_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    backend_rows = _backend_rows()
    detected_backend_count = sum(1 for row in backend_rows if row["detected"])
    audited_backend_count = sum(1 for row in backend_rows if row["audited_command_contract_integrated"])
    execution_allowed = False
    arc_rows = _arc_rows(detected_backend_count, audited_backend_count)
    checks = _base_checks(_extra_checks(backend_rows, arc_rows))
    return {
        "version": MODULE_VERSION,
        "arc_version": ARC_VERSION,
        "arc_title": ARC_TITLE,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": REVIEW_ID,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "status": _status(checks),
        "ok": all(row.get("ok") is True for row in checks),
        "description": "Builds a readiness ledger for generated dispatch promotion without activating generated wiring.",
        "implementation_status": "implemented_blocking",
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "backend_rows": backend_rows,
        "sandbox_backend_candidate_count": len(backend_rows),
        "detected_backend_count": detected_backend_count,
        "audited_backend_count": audited_backend_count,
        "audited_os_sandbox_backend_integrated": False,
        "actual_fixture_execution_allowed": execution_allowed,
        "actual_fixture_execution_attempted": False,
        "actual_fixture_execution_count": 0,
        "actual_fixture_execution_blocked": True,
        "actual_fixture_execution_block_reason": "no audited OS-enforced sandbox backend integrated",
        "subprocess_spawn_count": 0,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "dashboard_get_preview_only": True,
        "api_get_preview_only": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "operator_approval_required": True,
        "required_sandbox_capabilities": list(REQUIRED_SANDBOX_CAPABILITIES),
        "arc_rows": arc_rows,
        "checks": checks,
    }

def _arc_rows(detected_backend_count: int, audited_backend_count: int) -> list[dict[str, Any]]:
    return [
        {"arc": "v1067.0", "name": "generated dashboard dispatch", "status": "not_ready", "reason": "real sandbox fixture evidence missing"},
        {"arc": "v1067.0", "name": "generated api dispatch", "status": "not_ready", "reason": "real sandbox fixture evidence missing"},
        {"arc": "v1067.0", "name": "generated smoke dispatch", "status": "not_ready", "reason": "real sandbox fixture evidence missing"},
        {"arc": "v1067.0", "name": "rollback path", "status": "required_before_promotion"},
    ]

def _extra_checks(backend_rows: list[dict[str, Any]], arc_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _check("readiness-ledger-built", len(arc_rows) >= 4, "Promotion readiness ledger rows are present."),
        _check("promotion-not-ready", all(row.get("status") != "ready" for row in arc_rows), "No generated dispatch surface is ready for promotion."),
        _check("manual-dispatch-retained", True, "Manual dashboard/API/smoke dispatch remains authoritative."),
    ]

def build_report(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    report = build_metadata(project_id="eidolon")
    if docs is None and inspect_sources:
        docs = "\n".join(_read_text(project_root, rel) for rel in (
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            f"conscious_agent/{__name__}.py",
            "conscious_agent/dashboard.py",
            "conscious_agent/api_server.py",
            "conscious_agent/source_surface_manifest.py",
            "tools/smoke_check.py",
        ))
    docs = docs or ""
    required = [REVIEW_ID, SELF_ROUTE, API_ROUTE, "build_metadata", "build_report", "text_report", "actual_fixture_execution_count=0", "audited_os_sandbox_backend_integrated=False", "generated_wiring_activated=False", "release_authorized=False", "autonomy_expanded=False", "data-tip", "command-deck", "operator-console", "no_native_title_tooltip"]
    missing = [token for token in required if token not in docs]
    checks = list(report.get("checks") or [])
    checks.append(_check("docs-and-surface-tokens", not missing, "Docs/source/dashboard/API/smoke contain required review tokens.", missing_tokens=missing))
    report.update({"missing_required_tokens": missing, "checks": checks, "status": _status(checks), "ok": all(row.get("ok") is True for row in checks)})
    return report

def text_report(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_metadata()
    lines = [
        f"{ARC_TITLE}",
        f"Status: {report.get('status')}",
        f"Review ID: {report.get('review_id')}",
        f"Detected sandbox backends: {report.get('detected_backend_count')}",
        f"Audited sandbox backends: {report.get('audited_backend_count')}",
        f"Actual fixture execution allowed: {report.get('actual_fixture_execution_allowed')}",
        f"Actual fixture execution count: {report.get('actual_fixture_execution_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append(json.dumps(report, indent=2, sort_keys=True, default=str))
    return "\n".join(lines)

# Compatibility aliases used by dashboard/API/smoke.
build_generated_dispatch_promotion_readiness_ledger_metadata = build_metadata
build_generated_dispatch_promotion_readiness_ledger = build_report
generated_dispatch_promotion_readiness_ledger_text = text_report

# 1067.0 Generated Dispatch Promotion Readiness Ledger tokens: generated-dispatch-promotion-readiness-ledger-v1 /generated-dispatch-promotion-readiness-ledger /api/source-surface/generated-dispatch-promotion-readiness-ledger build_metadata build_report text_report actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
