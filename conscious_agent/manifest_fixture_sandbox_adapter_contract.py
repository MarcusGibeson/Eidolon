from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC

MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_VERSION = RUNTIME_VERSION
MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID = "manifest-fixture-sandbox-adapter-contract-v1"
SELF_ROUTE = "/manifest-fixture-sandbox-adapter-contract"
API_ROUTE = "/api/source-surface/manifest-fixture-sandbox-adapter-contract"
RELATED_BATCH_REVIEW_ID = "manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion-v1"
RELATED_TRUTH_REPAIR_ID = "manifest-fixture-truth-and-stabilization-repair-v1"

# v1065.4 is a contract and detection layer only. It deliberately integrates no
# executable sandbox backend yet; candidate tools can be detected, but detected is
# not audited, audited is not integrated, and integrated is what matters. This is
# apparently necessary to say out loud in software now.
INTEGRATED_SANDBOX_BACKENDS: tuple[str, ...] = ()
CANDIDATE_BACKENDS: tuple[dict[str, str], ...] = (
    {"backend_id": "bubblewrap", "platform": "linux", "binary": "bwrap", "network_mode": "namespace_or_unshared", "filesystem_mode": "bind_mount_contract_required"},
    {"backend_id": "firejail", "platform": "linux", "binary": "firejail", "network_mode": "net_none_profile_required", "filesystem_mode": "private_tmp_profile_required"},
    {"backend_id": "unshare", "platform": "linux", "binary": "unshare", "network_mode": "network_namespace_required", "filesystem_mode": "mount_namespace_contract_required"},
    {"backend_id": "container", "platform": "portable", "binary": "docker", "network_mode": "--network=none_required", "filesystem_mode": "readonly_bind_plus_tmp_required"},
    {"backend_id": "windows_job_limited", "platform": "windows", "binary": "python_ctypes_job_object", "network_mode": "not_supported_by_job_object", "filesystem_mode": "acl_or_container_required"},
)
REQUIRED_SANDBOX_GUARDS: tuple[str, ...] = (
    "source_tree_readonly",
    "temp_workspace_write_only",
    "network_disabled_by_os_or_container",
    "external_filesystem_write_blocked",
    "stdout_stderr_captured",
    "timeout_enforced",
    "full_tree_mutation_snapshot_captured",
    "resource_limits_classified",
    "operator_post_required",
)
BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "contract_only": True,
    "detects_candidate_backends": True,
    "integrates_backend": False,
    "executes_fixture": False,
    "spawns_subprocess": False,
    "network_policy_env_var_counts_as_enforcement": False,
    "network_policy_enforced": False,
    "filesystem_policy_enforced": False,
    "source_tree_readonly_enforced": False,
    "temp_workspace_write_only_enforced": False,
    "resource_limits_enforced": False,
    "actual_fixture_execution_allowed": False,
    "unsupported_sandbox_blocks_fixture_execution": True,
    "fixture_files_written": False,
    "generated_wiring_activated": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}


@dataclass(frozen=True)
class SandboxBackendCapability:
    backend_id: str
    platform: str
    binary: str
    detected: bool
    integrated: bool
    audited_command_contract: bool
    network_policy_supported: bool
    network_policy_enforced: bool
    filesystem_policy_supported: bool
    filesystem_policy_enforced: bool
    source_tree_readonly_enforced: bool
    temp_workspace_write_only_enforced: bool
    resource_limits_supported: bool
    resource_limits_enforced: bool
    timeout_enforced_by_runner: bool
    stdout_stderr_capture_supported: bool
    actual_fixture_execution_allowed: bool
    block_reason: str


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _current_platform_id() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("darwin"):
        return "macos"
    return sys.platform


def _binary_detected(binary: str) -> bool:
    if binary == "python_ctypes_job_object":
        return sys.platform.startswith("win")
    return shutil.which(binary) is not None


def detect_sandbox_backend_capabilities() -> list[SandboxBackendCapability]:
    platform_id = _current_platform_id()
    rows: list[SandboxBackendCapability] = []
    for candidate in CANDIDATE_BACKENDS:
        backend_id = candidate["backend_id"]
        candidate_platform = candidate["platform"]
        platform_applicable = candidate_platform in {"portable", platform_id}
        detected = bool(platform_applicable and _binary_detected(candidate["binary"]))
        integrated = backend_id in INTEGRATED_SANDBOX_BACKENDS
        audited = False
        network_supported = backend_id in {"bubblewrap", "firejail", "unshare", "container"}
        filesystem_supported = backend_id in {"bubblewrap", "firejail", "unshare", "container", "windows_job_limited"}
        # Detection is not enforcement. v1065.4 intentionally has zero integrated
        # backend command contracts, so every enforcement field stays false.
        allowed = False
        if not platform_applicable:
            reason = f"backend_not_applicable_on_{platform_id}"
        elif not detected:
            reason = "candidate_backend_not_detected"
        elif not integrated:
            reason = "candidate_backend_detected_but_not_integrated_or_audited"
        else:
            reason = "integrated_backend_still_blocked_until_command_contract_audit"
        rows.append(SandboxBackendCapability(
            backend_id=backend_id,
            platform=candidate_platform,
            binary=candidate["binary"],
            detected=detected,
            integrated=integrated,
            audited_command_contract=audited,
            network_policy_supported=network_supported,
            network_policy_enforced=False,
            filesystem_policy_supported=filesystem_supported,
            filesystem_policy_enforced=False,
            source_tree_readonly_enforced=False,
            temp_workspace_write_only_enforced=False,
            resource_limits_supported=backend_id in {"container", "firejail"},
            resource_limits_enforced=False,
            timeout_enforced_by_runner=True,
            stdout_stderr_capture_supported=True,
            actual_fixture_execution_allowed=allowed,
            block_reason=reason,
        ))
    return rows


def selected_sandbox_capability() -> dict[str, Any]:
    rows = detect_sandbox_backend_capabilities()
    integrated_rows = [row for row in rows if row.integrated and row.audited_command_contract]
    selected = integrated_rows[0] if integrated_rows else None
    if selected is None:
        detected = [row.backend_id for row in rows if row.detected]
        return {
            "backend": "none",
            "backend_id": "none",
            "backend_status": "blocked_no_integrated_audited_backend",
            "platform": _current_platform_id(),
            "os_name": _current_platform_id(),
            "detected_candidate_backends": detected,
            "detected_candidate_backend_count": len(detected),
            "integrated_backend_count": 0,
            "sandbox_enforced": False,
            "network_policy_enforced": False,
            "filesystem_policy_enforced": False,
            "source_tree_readonly_enforced": False,
            "temp_workspace_write_only_enforced": False,
            "resource_limits_enforced": False,
            "timeout_enforced_by_runner": True,
            "stdout_stderr_capture_supported": True,
            "actual_fixture_execution_allowed": False,
            "execution_allowed": False,
            "unsupported_sandbox_blocks_fixture_execution": True,
            "network_policy_env_var_counts_as_enforcement": False,
            "blocked_reason": "os_enforced_sandbox_backend_not_integrated_or_audited",
        }
    selected_dict = asdict(selected)
    selected_dict.update({
        "backend": selected.backend_id,
        "backend_status": "integrated_audited_backend_available",
        "sandbox_enforced": False,
        "execution_allowed": False,
        "unsupported_sandbox_blocks_fixture_execution": True,
        "network_policy_env_var_counts_as_enforcement": False,
        "blocked_reason": "integrated backend execution remains disabled until a separate operator-approved fixture execution patch",
    })
    return selected_dict


def build_manifest_fixture_sandbox_adapter_contract_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    selected = selected_sandbox_capability()
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        "related_batch_review_id": RELATED_BATCH_REVIEW_ID,
        "status": "preview",
        "ok": True,
        "contract_only": True,
        "candidate_backend_count": len(CANDIDATE_BACKENDS),
        "detected_candidate_backend_count": int(selected.get("detected_candidate_backend_count") or 0),
        "integrated_backend_count": 0,
        "selected_backend": selected.get("backend"),
        "backend_status": selected.get("backend_status"),
        "execution_allowed": False,
        "actual_fixture_execution_allowed": False,
        "network_policy_env_var_counts_as_enforcement": False,
        "network_policy_enforced": False,
        "filesystem_policy_enforced": False,
        "source_tree_readonly_enforced": False,
        "temp_workspace_write_only_enforced": False,
        "resource_limits_enforced": False,
        "unsupported_sandbox_blocks_fixture_execution": True,
        "spawns_subprocess": False,
        "fixture_files_written": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Preview-only sandbox adapter contract. Detection is not enforcement; actual fixture execution remains blocked until an audited OS-enforced backend is integrated.",
    }


def build_manifest_fixture_sandbox_adapter_contract(root: str | Path | None = None, *, inspect_sources: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    rows = detect_sandbox_backend_capabilities()
    row_dicts = [asdict(row) for row in rows]
    selected = selected_sandbox_capability()
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/manifest_fixture_sandbox_adapter_contract.py",
        "conscious_agent/manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/current_version_staleness_audit.py",
        "tools/smoke_check.py",
    ]) if inspect_sources else ""
    required_tokens = [
        CURRENT_MILESTONE,
        MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        SELF_ROUTE,
        API_ROUTE,
        RELATED_BATCH_REVIEW_ID,
        "detect_sandbox_backend_capabilities",
        "selected_sandbox_capability",
        "build_manifest_fixture_sandbox_adapter_contract_metadata",
        "build_manifest_fixture_sandbox_adapter_contract",
        "manifest_fixture_sandbox_adapter_contract_text",
        "integrated_backend_count=0",
        "execution_allowed=False",
        "actual_fixture_execution_allowed=False",
        "network_policy_env_var_counts_as_enforcement=False",
        "network_policy_enforced=False",
        "filesystem_policy_enforced=False",
        "source_tree_readonly_enforced=False",
        "temp_workspace_write_only_enforced=False",
        "unsupported_sandbox_blocks_fixture_execution=True",
        "fixture_files_written=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    detected_count = sum(1 for row in rows if row.detected)
    integrated_count = sum(1 for row in rows if row.integrated)
    network_enforced_count = sum(1 for row in rows if row.network_policy_enforced)
    filesystem_enforced_count = sum(1 for row in rows if row.filesystem_policy_enforced)
    actual_allowed_count = sum(1 for row in rows if row.actual_fixture_execution_allowed)
    checks = [
        {"name": "contract-current", "ok": MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_VERSION == CURRENT_VERSION, "message": f"version={MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_VERSION}"},
        {"name": "candidate-backends-classified", "ok": len(rows) == len(CANDIDATE_BACKENDS) and len(rows) >= 5, "message": f"candidate_backends={len(rows)}"},
        {"name": "detected-is-not-integrated", "ok": integrated_count == 0 and actual_allowed_count == 0, "message": f"detected={detected_count} integrated={integrated_count} actual_allowed={actual_allowed_count}"},
        {"name": "env-var-is-not-network-enforcement", "ok": os.environ.get("EIDOLON_NETWORK_POLICY") != "__counts_as_enforcement__", "message": "EIDOLON_NETWORK_POLICY is documentation only and never proves network containment."},
        {"name": "enforcement-fields-remain-blocking", "ok": network_enforced_count == 0 and filesystem_enforced_count == 0 and selected.get("execution_allowed") is False, "message": f"network_enforced={network_enforced_count} filesystem_enforced={filesystem_enforced_count} execution_allowed={selected.get('execution_allowed')}"},
        {"name": "required-guards-declared", "ok": len(REQUIRED_SANDBOX_GUARDS) == 9 and "network_disabled_by_os_or_container" in REQUIRED_SANDBOX_GUARDS, "message": f"required_guards={len(REQUIRED_SANDBOX_GUARDS)}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "contract_only": True,
            "integrates_backend": False,
            "executes_fixture": False,
            "spawns_subprocess": False,
            "network_policy_env_var_counts_as_enforcement": False,
            "actual_fixture_execution_allowed": False,
            "unsupported_sandbox_blocks_fixture_execution": True,
            "generated_wiring_activated": False,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "Sandbox adapter contract is review-only and blocks execution without an audited backend."},
        {"name": "documentation-tokens", "ok": (not inspect_sources) or all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(check.get("ok") is True for check in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        "related_batch_review_id": RELATED_BATCH_REVIEW_ID,
        "related_truth_repair_id": RELATED_TRUTH_REPAIR_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "contract_only": True,
        "platform": _current_platform_id(),
        "os_name": _current_platform_id(),
        "candidate_backend_count": len(rows),
        "detected_candidate_backend_count": detected_count,
        "integrated_backend_count": integrated_count,
        "audited_command_contract_count": sum(1 for row in rows if row.audited_command_contract),
        "network_policy_env_var_counts_as_enforcement": False,
        "network_policy_enforced_count": network_enforced_count,
        "filesystem_policy_enforced_count": filesystem_enforced_count,
        "source_tree_readonly_enforced_count": sum(1 for row in rows if row.source_tree_readonly_enforced),
        "temp_workspace_write_only_enforced_count": sum(1 for row in rows if row.temp_workspace_write_only_enforced),
        "resource_limits_enforced_count": sum(1 for row in rows if row.resource_limits_enforced),
        "execution_allowed": False,
        "actual_fixture_execution_allowed": False,
        "actual_fixture_execution_allowed_count": actual_allowed_count,
        "unsupported_sandbox_blocks_fixture_execution": True,
        "selected_backend": selected.get("backend"),
        "backend_status": selected.get("backend_status"),
        "blocked_reason": selected.get("blocked_reason"),
        "required_sandbox_guards": list(REQUIRED_SANDBOX_GUARDS),
        "backend_capability_rows": row_dicts,
        "spawns_subprocess": False,
        "fixture_files_written": False,
        "generated_wiring_activated": False,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "checks": checks,
        "blocked": [check for check in checks if not check.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def manifest_fixture_sandbox_adapter_contract_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"related_batch_review_id={report.get('related_batch_review_id')}",
        f"status={report.get('status')}",
        f"candidate_backend_count={report.get('candidate_backend_count')}",
        f"detected_candidate_backend_count={report.get('detected_candidate_backend_count')}",
        f"integrated_backend_count={report.get('integrated_backend_count')}",
        f"audited_command_contract_count={report.get('audited_command_contract_count')}",
        f"selected_backend={report.get('selected_backend')}",
        f"backend_status={report.get('backend_status')}",
        f"blocked_reason={report.get('blocked_reason')}",
        f"execution_allowed={report.get('execution_allowed')}",
        f"actual_fixture_execution_allowed={report.get('actual_fixture_execution_allowed')}",
        f"network_policy_env_var_counts_as_enforcement={report.get('network_policy_env_var_counts_as_enforcement')}",
        f"network_policy_enforced=False",
        f"network_policy_enforced_count={report.get('network_policy_enforced_count')}",
        f"filesystem_policy_enforced=False",
        f"filesystem_policy_enforced_count={report.get('filesystem_policy_enforced_count')}",
        f"source_tree_readonly_enforced=False",
        f"source_tree_readonly_enforced_count={report.get('source_tree_readonly_enforced_count')}",
        f"temp_workspace_write_only_enforced=False",
        f"temp_workspace_write_only_enforced_count={report.get('temp_workspace_write_only_enforced_count')}",
        f"resource_limits_enforced_count={report.get('resource_limits_enforced_count')}",
        f"unsupported_sandbox_blocks_fixture_execution={report.get('unsupported_sandbox_blocks_fixture_execution')}",
        f"spawns_subprocess={report.get('spawns_subprocess')}",
        f"fixture_files_written={report.get('fixture_files_written')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_required={report.get('operator_approval_required')}",
    ]
    if full:
        for row in report.get("backend_capability_rows", []):
            lines.append(
                f"backend={row.get('backend_id')} detected={row.get('detected')} integrated={row.get('integrated')} "
                f"audited={row.get('audited_command_contract')} network_enforced={row.get('network_policy_enforced')} "
                f"filesystem_enforced={row.get('filesystem_policy_enforced')} actual_allowed={row.get('actual_fixture_execution_allowed')} "
                f"reason={row.get('block_reason')}"
            )
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1065.4 sandbox adapter contract tokens: manifest-fixture-sandbox-adapter-contract-v1 /manifest-fixture-sandbox-adapter-contract /api/source-surface/manifest-fixture-sandbox-adapter-contract detect_sandbox_backend_capabilities selected_sandbox_capability build_manifest_fixture_sandbox_adapter_contract_metadata build_manifest_fixture_sandbox_adapter_contract manifest_fixture_sandbox_adapter_contract_text integrated_backend_count=0 execution_allowed=False actual_fixture_execution_allowed=False network_policy_env_var_counts_as_enforcement=False network_policy_enforced=False filesystem_policy_enforced=False source_tree_readonly_enforced=False temp_workspace_write_only_enforced=False unsupported_sandbox_blocks_fixture_execution=True fixture_files_written=False generated_wiring_activated=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
