from __future__ import annotations

from release_metadata import RUNTIME_VERSION
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SANDBOX_BACKEND_ADAPTER_VERSION = RUNTIME_VERSION
SANDBOX_BACKEND_ADAPTER_ID = "sandbox-backend-adapter-skeleton-v1"
ADAPTER_STATUS = "skeleton_contract_only"

BACKEND_CANDIDATES: tuple[dict[str, str], ...] = (
    {"name": "bubblewrap", "command": "bwrap", "platform": "linux", "contract_status": "candidate_requires_audited_command_contract"},
    {"name": "firejail", "command": "firejail", "platform": "linux", "contract_status": "candidate_requires_audited_command_contract"},
    {"name": "unshare", "command": "unshare", "platform": "linux", "contract_status": "candidate_requires_audited_command_contract"},
    {"name": "docker", "command": "docker", "platform": "container", "contract_status": "candidate_requires_strict_flags_and_image_contract"},
    {"name": "windows-job-object", "command": "none", "platform": "windows", "contract_status": "concept_only_not_integrated"},
)

REQUIRED_COMMAND_CONTRACT: tuple[str, ...] = (
    "filesystem_isolation",
    "write_confinement",
    "network_denial",
    "working_directory_confinement",
    "process_limit",
    "timeout_enforcement",
    "stdout_capture",
    "stderr_capture",
    "return_code_capture",
    "before_after_full_tree_mutation_snapshot",
    "private_runtime_path_exclusion",
    "operator_confirmation_binding",
)

DENIED_OPERATIONS: tuple[str, ...] = (
    "fixture_subprocess_execution_without_audited_backend",
    "generated_dashboard_dispatch_promotion",
    "generated_api_dispatch_promotion",
    "generated_smoke_registry_promotion",
    "release_authorization",
    "autonomy_expansion",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def detect_backend_rows(candidates: Iterable[dict[str, str]] = BACKEND_CANDIDATES) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        command = candidate.get("command") or "none"
        detected = bool(command != "none" and shutil.which(command))
        rows.append({
            "name": candidate.get("name", "unknown"),
            "command": command,
            "platform": candidate.get("platform", "unknown"),
            "detected": detected,
            "adapter_status": ADAPTER_STATUS,
            "audited_command_contract_integrated": False,
            "filesystem_isolation_proven": False,
            "network_denial_proven": False,
            "write_confinement_proven": False,
            "process_limit_proven": False,
            "timeout_enforcement_proven": False,
            "execution_allowed": False,
            "classification": "detected_but_not_audited" if detected else candidate.get("contract_status", "not_detected"),
        })
    return rows


def build_sandbox_backend_adapter_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    backend_rows = detect_backend_rows()
    detected_backend_count = sum(1 for row in backend_rows if row.get("detected"))
    audited_backend_count = sum(1 for row in backend_rows if row.get("audited_command_contract_integrated"))
    return {
        "version": SANDBOX_BACKEND_ADAPTER_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "adapter_id": SANDBOX_BACKEND_ADAPTER_ID,
        "adapter_status": ADAPTER_STATUS,
        "implementation_status": "implemented_contract_only",
        "backend_rows": backend_rows,
        "backend_candidate_count": len(backend_rows),
        "detected_backend_count": detected_backend_count,
        "audited_backend_count": audited_backend_count,
        "required_command_contract": list(REQUIRED_COMMAND_CONTRACT),
        "denied_operations": list(DENIED_OPERATIONS),
        "sandbox_backend_adapter_integrated": False,
        "audited_os_sandbox_backend_integrated": False,
        "actual_fixture_execution_allowed": False,
        "actual_fixture_execution_attempted": False,
        "actual_fixture_execution_count": 0,
        "subprocess_spawn_count": 0,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
    }


def build_sandbox_backend_adapter_report(project_id: str = "eidolon") -> dict[str, Any]:
    report = build_sandbox_backend_adapter_metadata(project_id=project_id)
    report["status"] = "pass"
    report["ok"] = True
    report["checks"] = [
        {"name": "adapter-skeleton-only", "ok": True, "status": "pass", "message": "The sandbox backend adapter is a command-contract skeleton only."},
        {"name": "execution-blocked", "ok": True, "status": "pass", "message": "Fixture execution remains blocked until an audited OS-enforced backend is integrated."},
        {"name": "manual-authority", "ok": True, "status": "pass", "message": "Manual dashboard/API/smoke dispatch remain authoritative."},
    ]
    return report


def sandbox_backend_adapter_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_sandbox_backend_adapter_report()
    lines = [
        "Sandbox Backend Adapter Skeleton v1",
        f"Status: {report.get('status')}",
        f"Adapter status: {report.get('adapter_status')}",
        f"Detected backends: {report.get('detected_backend_count')}",
        f"Audited backends: {report.get('audited_backend_count')}",
        f"Execution allowed: {report.get('actual_fixture_execution_allowed')}",
        f"Actual fixture execution count: {report.get('actual_fixture_execution_count')}",
    ]
    if full:
        lines.append(json.dumps(report, indent=2, sort_keys=True, default=str))
    return "\n".join(lines)

# v1070.1 sandbox backend adapter skeleton tokens: sandbox-backend-adapter-skeleton-v1 SANDBOX_BACKEND_ADAPTER_VERSION=1070.1 adapter_status=skeleton_contract_only audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False actual_fixture_execution_allowed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.4 sandbox backend adapter metadata token: SANDBOX_BACKEND_ADAPTER_VERSION=1075.4 sandbox_backend_adapter_integrated=False actual_fixture_execution_allowed=False subprocess_spawn_count=0 release_authorized=False autonomy_expanded=False
