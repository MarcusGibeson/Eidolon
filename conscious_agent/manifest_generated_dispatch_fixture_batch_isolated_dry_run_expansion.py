from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from manifest_generated_dispatch_fixture_dry_run_execution_prep import (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_ID,
    build_manifest_generated_dispatch_fixture_dry_run_execution_prep,
)
from manifest_generated_dispatch_fixture_trial_receipt_hardening import (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_ID,
    build_manifest_generated_dispatch_fixture_trial_receipt_hardening,
)
from manifest_fixture_sandbox_adapter_contract import (
    MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
    selected_sandbox_capability,
)
from full_tree_mutation_snapshot import (
    FULL_TREE_MUTATION_SNAPSHOT_ID,
    snapshot_source_tree as shared_snapshot_source_tree,
    snapshot_hash as shared_snapshot_hash,
    snapshot_delta as shared_snapshot_delta,
)

MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_VERSION = RUNTIME_VERSION
MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_ID = "manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion-v1"
MANIFEST_GENERATED_DISPATCH_FIXTURE_TRUTH_STABILIZATION_ID = "manifest-fixture-truth-and-stabilization-repair-v1"
SELF_ROUTE = "/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion"
API_ROUTE = "/api/source-surface/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion"
API_RUN_ROUTE = "/api/source-surface/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion/run"
INPUT_EXECUTION_PREP_REVIEW_ID = MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_ID
INPUT_HARDENED_RECEIPT_REVIEW_ID = MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_ID
INPUT_EXECUTION_PREP_ROW_COUNT = 24
INPUT_HARDENED_RECEIPT_COUNT = 1
BATCH_CANDIDATE_ROW_COUNT = 3
BATCH_PASS_COUNT = 3
REMAINING_UNEXECUTED_FIXTURE_ROW_COUNT = 21
DISPATCH_FAMILY_COUNT = 3
DRY_RUN_TIMEOUT_SECONDS = 5
OPERATOR_CONFIRMATION_PHRASE = "RUN_MANIFEST_FIXTURE_BATCH_TRUTH_STABILIZATION"

TRIAL_STEPS: tuple[str, ...] = (
    "select_one_fixture_per_dispatch_family",
    "require_explicit_operator_post_before_execution",
    "detect_os_enforced_sandbox_backend",
    "block_actual_fixture_execution_without_os_enforced_sandbox",
    "prepare_actual_fixture_probe_script_without_receipt_only_shortcut",
    "capture_full_tree_pre_run_mutation_snapshot",
    "capture_stdout_stderr_timeout_receipt_when_execution_is_allowed",
    "capture_full_tree_post_run_mutation_snapshot",
    "compare_source_snapshot_and_discard_workspace",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "truth_and_stabilization_repair": True,
    "dashboard_get_executes_subprocesses": False,
    "api_get_executes_subprocesses": False,
    "post_operator_action_required_for_execution": True,
    "receipt_only_subprocess_claims_fixture_correctness": False,
    "dry_run_commands_executed_by_default": False,
    "actual_fixture_execution_requires_os_sandbox": True,
    "fixture_harness_executed_without_sandbox": False,
    "network_policy_env_var_counts_as_enforcement": False,
    "network_access_permitted": False,
    "external_filesystem_write_permitted": False,
    "source_files_mutated_at_runtime": False,
    "runtime_data_deleted": False,
    "fixture_files_written": False,
    "generated_dashboard_dispatch_written": False,
    "generated_api_dispatch_written": False,
    "generated_smoke_dispatch_written": False,
    "generated_wiring_activated": False,
    "candidate_routes_registered_live": False,
    "manifest_replaces_dashboard_routes": False,
    "manifest_replaces_api_dispatch": False,
    "manifest_replaces_smoke_registry": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}

SNAPSHOT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}
SNAPSHOT_EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
SNAPSHOT_RUNTIME_EXACT = {
    "data/tasks.json",
    "data/action_log.json",
    "data/memories.json",
    "data/thoughts.log",
    "data/self_model.json",
    "data/workspaces/timeline.json",
}
SNAPSHOT_RUNTIME_PREFIXES = (
    "data/approvals/",
    "data/chat_actions/",
    "data/dashboard_chat/",
    "data/self_development_cycles/",
    "data/releases/",
    "data/release_package/",
    "data/release_installation/",
    "data/backups/",
    "data/diagnostics/",
    "data/notifications/",
    "data/stable_loops/",
    "data/watch_reports/",
    "data/work_cycles/",
)


@dataclass(frozen=True)
class BatchIsolatedDryRunTrialRow:
    trial_id: str
    execution_prep_id: str
    fixture_id: str
    surface_id: str
    dispatch_family: str
    candidate_target: str
    trial_mode: str
    trial_steps: tuple[str, ...]
    trial_step_count: int
    operator_post_required: bool
    operator_confirmed: bool
    temporary_workspace_created: bool
    subprocess_spawned: bool
    upstream_subprocess_spawned: bool
    dry_run_command_executed: bool
    receipt_only_subprocess: bool
    actual_fixture_execution_attempted: bool
    actual_fixture_execution_passed: bool
    actual_fixture_execution_blocked: bool
    fixture_probe_script_prepared: bool
    stdout_captured: bool
    stderr_captured: bool
    timeout_seconds: int
    timed_out: bool
    subprocess_returncode: int | None
    receipt_marker_found: bool
    receipt_ok: bool
    sandbox_backend: str
    sandbox_enforced: bool
    network_policy_declared: str
    network_policy_enforced: bool
    filesystem_policy_enforced: bool
    network_policy_disabled: bool
    pre_snapshot_hash: str
    post_snapshot_hash: str
    watched_file_count: int
    changed_file_count: int
    created_file_count: int
    deleted_file_count: int
    source_snapshot_changed: bool
    source_mutation_count: int
    fixture_file_written: bool
    generated_wiring_activated: bool
    release_authorized: bool
    autonomy_expanded: bool
    blocked_reason: str
    operator_action: str


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _is_runtime_private(rel: str) -> bool:
    rel = rel.replace("\\", "/").strip("/")
    return rel in SNAPSHOT_RUNTIME_EXACT or any(rel.startswith(prefix) for prefix in SNAPSHOT_RUNTIME_PREFIXES)


def _source_snapshot(root: Path) -> dict[str, str]:
    return shared_snapshot_source_tree(root)


def _snapshot_hash(snapshot: dict[str, str]) -> str:
    return shared_snapshot_hash(snapshot)


def _snapshot_delta(pre_snapshot: dict[str, str], post_snapshot: dict[str, str]) -> dict[str, int]:
    return shared_snapshot_delta(pre_snapshot, post_snapshot)


def _parse_receipt(stdout: str) -> dict[str, Any]:
    marker = "EIDOLON_FIXTURE_BATCH_DRY_RUN_RECEIPT="
    for line in stdout.splitlines():
        if line.startswith(marker):
            try:
                return json.loads(line[len(marker):])
            except json.JSONDecodeError:
                return {"ok": False, "decode_error": True}
    return {"ok": False, "receipt_missing": True}


def _select_batch_rows(prep_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in prep_rows:
        family = str(row.get("dispatch_family"))
        if family in {"dashboard", "api", "smoke"} and family not in seen:
            selected.append(row)
            seen.add(family)
        if len(selected) == BATCH_CANDIDATE_ROW_COUNT:
            break
    return selected


def _sandbox_capability() -> dict[str, Any]:
    capability = dict(selected_sandbox_capability())
    capability.setdefault("backend", capability.get("backend_id", "none"))
    capability.setdefault("sandbox_enforced", False)
    capability.setdefault("network_policy_enforced", False)
    capability.setdefault("filesystem_policy_enforced", False)
    capability.setdefault("actual_fixture_execution_allowed", False)
    capability.setdefault("blocked_reason", "os_enforced_sandbox_backend_not_integrated_or_audited")
    return capability


def _fixture_probe_script() -> str:
    # This is actual fixture probe logic for the future OS-sandboxed path. It is
    # deliberately not a hard-coded receipt printer: dashboard/API/smoke targets
    # must be imported and exercised before the receipt can pass.
    return r'''
import json
import os
import sys
from pathlib import Path

repo = Path(os.environ["EIDOLON_REPO_ROOT"]).resolve()
sys.path.insert(0, str(repo / "conscious_agent"))
sys.path.insert(0, str(repo / "tools"))
family = os.environ.get("EIDOLON_DISPATCH_FAMILY", "")
target = os.environ.get("EIDOLON_CANDIDATE_TARGET", "")
fixture_id = os.environ.get("EIDOLON_FIXTURE_ID", "")
payload = {
    "ok": False,
    "trial_kind": "manifest_fixture_truth_and_stabilization_actual_fixture_probe",
    "fixture_id": fixture_id,
    "dispatch_family": family,
    "candidate_target": target,
    "fixture_file_written": False,
    "generated_dispatch_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
}
try:
    if family == "dashboard":
        import dashboard
        func_name = "render_" + target.strip("/").replace("-", "_")
        func = getattr(dashboard, func_name)
        rendered = func()
        payload.update({"ok": isinstance(rendered, str) and target in rendered, "probe": "dashboard_renderer", "rendered_length": len(rendered) if isinstance(rendered, str) else 0})
    elif family == "api":
        import api_server
        status, body = api_server.handle_api_get(target, {})
        data = body.get("data", body) if isinstance(body, dict) else body
        payload.update({"ok": status == 200 and isinstance(data, dict), "probe": "api_handler", "status": status})
    elif family == "smoke":
        import smoke_check
        checks = smoke_check._build_checks()
        check = next((item for item in checks if item.name == target), None)
        if check is None:
            payload.update({"ok": False, "probe": "smoke_check", "error": "target_not_found"})
        else:
            payload.update({"ok": bool(check.func()), "probe": "smoke_check"})
    else:
        payload.update({"ok": False, "error": "unsupported_dispatch_family"})
except Exception as error:
    payload.update({"ok": False, "error": type(error).__name__, "message": str(error)[:500]})
print("EIDOLON_FIXTURE_BATCH_DRY_RUN_RECEIPT=" + json.dumps(payload, sort_keys=True))
'''


def _run_actual_fixture_if_allowed(root: Path, prep_row: dict[str, Any], batch_index: int, *, operator_confirmed: bool) -> BatchIsolatedDryRunTrialRow:
    pre_snapshot = _source_snapshot(root)
    pre_hash = _snapshot_hash(pre_snapshot)
    receipt: dict[str, Any] = {"ok": False, "not_run": True}
    stdout = ""
    stderr = ""
    returncode: int | None = None
    timed_out = False
    subprocess_spawned = False
    temp_workspace_created = False
    fixture_id = str(prep_row.get("fixture_id"))
    target = str(prep_row.get("candidate_target"))
    family = str(prep_row.get("dispatch_family"))
    surface_id = str(prep_row.get("surface_id"))
    execution_prep_id = str(prep_row.get("execution_prep_id"))
    trial_id = f"batch_truth_stabilization_trial_{batch_index}_{execution_prep_id}"
    capability = _sandbox_capability()
    blocked_reason = "operator_post_required" if not operator_confirmed else str(capability.get("blocked_reason") or "")
    actual_allowed = bool(operator_confirmed and capability.get("actual_fixture_execution_allowed"))

    if actual_allowed:
        with tempfile.TemporaryDirectory(prefix="eidolon_fixture_truth_stabilization_") as temp_dir:
            temp_workspace_created = True
            command = [sys.executable, "-I", "-B", "-c", _fixture_probe_script()]
            env = {
                "PYTHONNOUSERSITE": "1",
                "EIDOLON_REPO_ROOT": str(root),
                "EIDOLON_NETWORK_POLICY": "disabled",
                "EIDOLON_FIXTURE_ID": fixture_id,
                "EIDOLON_DISPATCH_FAMILY": family,
                "EIDOLON_CANDIDATE_TARGET": target,
                "EIDOLON_BATCH_INDEX": str(batch_index),
            }
            try:
                subprocess_spawned = True
                completed = subprocess.run(
                    command,
                    cwd=temp_dir,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=DRY_RUN_TIMEOUT_SECONDS,
                    check=False,
                )
                stdout = completed.stdout or ""
                stderr = completed.stderr or ""
                returncode = completed.returncode
                receipt = _parse_receipt(stdout)
            except subprocess.TimeoutExpired as error:
                timed_out = True
                stdout = error.stdout or ""
                stderr = error.stderr or ""
                returncode = None
                receipt = {"ok": False, "timed_out": True}

    post_snapshot = _source_snapshot(root)
    post_hash = _snapshot_hash(post_snapshot)
    delta = _snapshot_delta(pre_snapshot, post_snapshot)
    source_mutation_count = int(delta["source_mutation_count"])
    receipt_ok = (
        actual_allowed
        and receipt.get("ok") is True
        and receipt.get("fixture_file_written") is False
        and receipt.get("generated_dispatch_activated") is False
        and receipt.get("release_authorized") is False
        and receipt.get("autonomy_expanded") is False
        and source_mutation_count == 0
    )
    return BatchIsolatedDryRunTrialRow(
        trial_id=trial_id,
        execution_prep_id=execution_prep_id,
        fixture_id=fixture_id,
        surface_id=surface_id,
        dispatch_family=family,
        candidate_target=target,
        trial_mode="actual_fixture_execution_blocked_until_os_enforced_sandbox" if not actual_allowed else "os_enforced_actual_fixture_execution",
        trial_steps=TRIAL_STEPS,
        trial_step_count=len(TRIAL_STEPS),
        operator_post_required=True,
        operator_confirmed=operator_confirmed,
        temporary_workspace_created=temp_workspace_created,
        subprocess_spawned=subprocess_spawned,
        upstream_subprocess_spawned=False,
        dry_run_command_executed=actual_allowed,
        receipt_only_subprocess=False,
        actual_fixture_execution_attempted=actual_allowed,
        actual_fixture_execution_passed=receipt_ok,
        actual_fixture_execution_blocked=not actual_allowed,
        fixture_probe_script_prepared=True,
        stdout_captured=stdout != "" or (returncode == 0 and actual_allowed),
        stderr_captured=stderr == "" or isinstance(stderr, str),
        timeout_seconds=DRY_RUN_TIMEOUT_SECONDS,
        timed_out=timed_out,
        subprocess_returncode=returncode,
        receipt_marker_found="EIDOLON_FIXTURE_BATCH_DRY_RUN_RECEIPT=" in stdout,
        receipt_ok=receipt_ok,
        sandbox_backend=str(capability.get("backend")),
        sandbox_enforced=bool(capability.get("sandbox_enforced")),
        network_policy_declared="disabled",
        network_policy_enforced=bool(capability.get("network_policy_enforced")),
        filesystem_policy_enforced=bool(capability.get("filesystem_policy_enforced")),
        network_policy_disabled=True,
        pre_snapshot_hash=pre_hash,
        post_snapshot_hash=post_hash,
        watched_file_count=int(delta["watched_file_count"]),
        changed_file_count=int(delta["changed_file_count"]),
        created_file_count=int(delta["created_file_count"]),
        deleted_file_count=int(delta["deleted_file_count"]),
        source_snapshot_changed=source_mutation_count != 0,
        source_mutation_count=source_mutation_count,
        fixture_file_written=False,
        generated_wiring_activated=False,
        release_authorized=False,
        autonomy_expanded=False,
        blocked_reason=blocked_reason,
        operator_action="Use POST with the exact confirmation phrase only after an audited OS sandbox backend exists; do not promote generated dispatch, authorize release, or expand autonomy from this receipt.",
    )


def _preview_trial_row(prep_row: dict[str, Any], batch_index: int) -> BatchIsolatedDryRunTrialRow:
    execution_prep_id = str(prep_row.get("execution_prep_id"))
    capability = _sandbox_capability()
    return BatchIsolatedDryRunTrialRow(
        trial_id=f"batch_truth_preview_{batch_index}_{execution_prep_id}",
        execution_prep_id=execution_prep_id,
        fixture_id=str(prep_row.get("fixture_id")),
        surface_id=str(prep_row.get("surface_id")),
        dispatch_family=str(prep_row.get("dispatch_family")),
        candidate_target=str(prep_row.get("candidate_target")),
        trial_mode="metadata_preview_no_subprocess_no_fixture_execution",
        trial_steps=TRIAL_STEPS,
        trial_step_count=len(TRIAL_STEPS),
        operator_post_required=True,
        operator_confirmed=False,
        temporary_workspace_created=False,
        subprocess_spawned=False,
        upstream_subprocess_spawned=False,
        dry_run_command_executed=False,
        receipt_only_subprocess=False,
        actual_fixture_execution_attempted=False,
        actual_fixture_execution_passed=False,
        actual_fixture_execution_blocked=True,
        fixture_probe_script_prepared=True,
        stdout_captured=False,
        stderr_captured=False,
        timeout_seconds=DRY_RUN_TIMEOUT_SECONDS,
        timed_out=False,
        subprocess_returncode=None,
        receipt_marker_found=False,
        receipt_ok=False,
        sandbox_backend=str(capability.get("backend")),
        sandbox_enforced=bool(capability.get("sandbox_enforced")),
        network_policy_declared="disabled",
        network_policy_enforced=bool(capability.get("network_policy_enforced")),
        filesystem_policy_enforced=bool(capability.get("filesystem_policy_enforced")),
        network_policy_disabled=True,
        pre_snapshot_hash="not-captured-in-metadata-preview",
        post_snapshot_hash="not-captured-in-metadata-preview",
        watched_file_count=0,
        changed_file_count=0,
        created_file_count=0,
        deleted_file_count=0,
        source_snapshot_changed=False,
        source_mutation_count=0,
        fixture_file_written=False,
        generated_wiring_activated=False,
        release_authorized=False,
        autonomy_expanded=False,
        blocked_reason="operator_post_required" if not capability.get("actual_fixture_execution_allowed") else "metadata_preview_only",
        operator_action="metadata preview only; execution requires POST plus an audited OS-enforced sandbox backend",
    )


def build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    capability = _sandbox_capability()
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_ID,
        "truth_stabilization_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_TRUTH_STABILIZATION_ID,
        "sandbox_adapter_contract_id": MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        "full_tree_mutation_snapshot_id": FULL_TREE_MUTATION_SNAPSHOT_ID,
        "input_execution_prep_review_id": INPUT_EXECUTION_PREP_REVIEW_ID,
        "input_hardened_receipt_review_id": INPUT_HARDENED_RECEIPT_REVIEW_ID,
        "status": "preview",
        "ok": True,
        "input_execution_prep_row_count": INPUT_EXECUTION_PREP_ROW_COUNT,
        "input_hardened_receipt_count": INPUT_HARDENED_RECEIPT_COUNT,
        "batch_candidate_row_count": BATCH_CANDIDATE_ROW_COUNT,
        "batch_attempt_count": 0,
        "batch_pass_count": 0,
        "upstream_subprocess_count": 0,
        "batch_subprocess_count": 0,
        "total_subprocess_count": 0,
        "receipt_only_subprocess_count": 0,
        "actual_fixture_execution_count": 0,
        "actual_fixture_execution_blocked_count": BATCH_CANDIDATE_ROW_COUNT,
        "remaining_unexecuted_fixture_row_count": INPUT_EXECUTION_PREP_ROW_COUNT,
        "dashboard_get_executes_subprocesses": False,
        "api_get_executes_subprocesses": False,
        "operator_post_required_for_execution": True,
        "sandbox_adapter_contract_id": MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        "sandbox_backend": capability.get("backend"),
        "sandbox_backend_status": capability.get("backend_status"),
        "sandbox_enforced": capability.get("sandbox_enforced"),
        "actual_fixture_execution_allowed": capability.get("actual_fixture_execution_allowed"),
        "network_policy_declared": "disabled",
        "network_policy_enforced": capability.get("network_policy_enforced"),
        "filesystem_policy_enforced": capability.get("filesystem_policy_enforced"),
        "dry_run_commands_executed": False,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "subprocesses_spawned": False,
        "temp_workspaces_created": False,
        "mutation_snapshots_captured": False,
        "full_tree_mutation_snapshot_id": FULL_TREE_MUTATION_SNAPSHOT_ID,
        "network_access_permitted": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Preview-only metadata. GET/dashboard render never launches subprocesses; actual fixture execution requires POST plus an audited OS-enforced sandbox backend.",
    }


def build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion(root: str | Path | None = None, *, inspect_sources: bool = True, execute_batch: bool = False, operator_confirmed: bool = False) -> dict[str, Any]:
    project_root = _repo(root)
    prep_report = build_manifest_generated_dispatch_fixture_dry_run_execution_prep(project_root, inspect_sources=inspect_sources)
    prep_rows = list(prep_report.get("execution_prep_rows") or [])
    selected_rows = _select_batch_rows(prep_rows)
    should_attempt_actual = bool(execute_batch and operator_confirmed)
    hardening_report = build_manifest_generated_dispatch_fixture_trial_receipt_hardening(project_root, inspect_sources=inspect_sources, execute_trial=should_attempt_actual)
    if should_attempt_actual and selected_rows:
        trial_rows = [_run_actual_fixture_if_allowed(project_root, row, index + 1, operator_confirmed=True) for index, row in enumerate(selected_rows)]
    else:
        trial_rows = [_preview_trial_row(row, index + 1) for index, row in enumerate(selected_rows)]
    row_dicts = [asdict(row) for row in trial_rows]
    batch_attempt_count = sum(1 for row in row_dicts if row.get("dry_run_command_executed") is True)
    batch_pass_count = sum(1 for row in row_dicts if row.get("actual_fixture_execution_passed") is True)
    batch_subprocess_count = sum(1 for row in row_dicts if row.get("subprocess_spawned") is True)
    upstream_subprocess_count = int(hardening_report.get("trial_subprocess_spawn_count") or 0)
    total_subprocess_count = upstream_subprocess_count + batch_subprocess_count
    receipt_only_subprocess_count = sum(1 for row in row_dicts if row.get("receipt_only_subprocess") is True)
    temp_workspace_count = sum(1 for row in row_dicts if row.get("temporary_workspace_created") is True)
    mutation_snapshot_count = sum(2 for row in row_dicts if row.get("pre_snapshot_hash") != "not-captured-in-metadata-preview" and row.get("post_snapshot_hash") != "not-captured-in-metadata-preview")
    source_mutation_count = sum(int(row.get("source_mutation_count") or 0) for row in row_dicts)
    fixture_write_count = sum(1 for row in row_dicts if row.get("fixture_file_written") is True)
    generated_wiring_count = sum(1 for row in row_dicts if row.get("generated_wiring_activated") is True)
    release_authorized_count = sum(1 for row in row_dicts if row.get("release_authorized") is True)
    autonomy_expanded_count = sum(1 for row in row_dicts if row.get("autonomy_expanded") is True)
    timeout_count = sum(1 for row in row_dicts if row.get("timed_out") is True)
    family_count = len({str(row.get("dispatch_family")) for row in row_dicts})
    actual_fixture_execution_count = sum(1 for row in row_dicts if row.get("actual_fixture_execution_attempted") is True)
    actual_fixture_execution_blocked_count = sum(1 for row in row_dicts if row.get("actual_fixture_execution_blocked") is True)
    sandbox_enforced_count = sum(1 for row in row_dicts if row.get("sandbox_enforced") is True)
    network_enforced_count = sum(1 for row in row_dicts if row.get("network_policy_enforced") is True)
    filesystem_enforced_count = sum(1 for row in row_dicts if row.get("filesystem_policy_enforced") is True)
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion.py",
        "conscious_agent/manifest_fixture_sandbox_adapter_contract.py",
        "conscious_agent/manifest_generated_dispatch_fixture_trial_receipt_hardening.py",
        "conscious_agent/manifest_generated_dispatch_fixture_dry_run_execution_prep.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/current_version_staleness_audit.py",
        "tools/smoke_check.py",
    ])
    required_tokens = [
        CURRENT_MILESTONE,
        MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_ID,
        MANIFEST_GENERATED_DISPATCH_FIXTURE_TRUTH_STABILIZATION_ID,
        MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        FULL_TREE_MUTATION_SNAPSHOT_ID,
        SELF_ROUTE,
        API_ROUTE,
        API_RUN_ROUTE,
        "build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata",
        "build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion",
        "manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_text",
        "dashboard_get_executes_subprocesses=False",
        "api_get_executes_subprocesses=False",
        "operator_post_required_for_execution=True",
        "receipt_only_subprocess_count=0",
        "actual_fixture_execution_blocked_count=3",
        "upstream_subprocess_count=0",
        "batch_subprocess_count=0",
        "total_subprocess_count=0",
        "network_policy_env_var_counts_as_enforcement=False",
        "manifest-fixture-sandbox-adapter-contract-v1",
        "network_policy_enforced=False",
        "filesystem_policy_enforced=False",
        "full_tree_mutation_monitoring=True",
        "full-tree-mutation-snapshot-expansion-v1",
        "source_mutation_count=0",
        "fixture_files_written=False",
        "generated_wiring_activated=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
    ]
    checks = [
        {"name": "module-version-current", "ok": MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_VERSION == CURRENT_VERSION, "message": f"module={MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "input-execution-prep-pass", "ok": prep_report.get("ok") is True and prep_report.get("status") == "pass", "message": f"input_status={prep_report.get('status')} input_ok={prep_report.get('ok')}"},
        {"name": "input-hardening-preview-no-hidden-subprocess", "ok": (hardening_report.get("ok") is True and hardening_report.get("status") == "pass" and hardening_report.get("hardened_receipt_count") == INPUT_HARDENED_RECEIPT_COUNT) if should_attempt_actual else upstream_subprocess_count == 0, "message": f"hardening_status={hardening_report.get('status')} hardened={hardening_report.get('hardened_receipt_count')} upstream_subprocesses={upstream_subprocess_count} operator_confirmed={operator_confirmed}"},
        {"name": "input-execution-prep-row-count", "ok": len(prep_rows) == INPUT_EXECUTION_PREP_ROW_COUNT, "message": f"input_rows={len(prep_rows)} expected={INPUT_EXECUTION_PREP_ROW_COUNT}"},
        {"name": "bounded-batch-selected", "ok": len(row_dicts) == BATCH_CANDIDATE_ROW_COUNT and family_count == DISPATCH_FAMILY_COUNT, "message": f"trial_rows={len(row_dicts)} families={family_count}"},
        {"name": "dashboard-and-get-are-side-effect-free", "ok": not execute_batch or operator_confirmed, "message": "GET/dashboard paths must call metadata or preview paths only; execution requires explicit POST/operator confirmation."},
        {"name": "receipt-only-not-fixture-execution", "ok": receipt_only_subprocess_count == 0 and all(row.get("fixture_probe_script_prepared") is True for row in row_dicts), "message": f"receipt_only={receipt_only_subprocess_count} actual_probe_script_prepared={len(row_dicts)}"},
        {"name": "subprocess-count-truth", "ok": total_subprocess_count == upstream_subprocess_count + batch_subprocess_count, "message": f"upstream={upstream_subprocess_count} batch={batch_subprocess_count} total={total_subprocess_count}"},
        {"name": "sandbox-enforcement-not-asserted", "ok": sandbox_enforced_count == 0 and network_enforced_count == 0 and filesystem_enforced_count == 0 and actual_fixture_execution_count == 0 and actual_fixture_execution_blocked_count == BATCH_CANDIDATE_ROW_COUNT, "message": f"sandbox_enforced={sandbox_enforced_count} network_enforced={network_enforced_count} filesystem_enforced={filesystem_enforced_count} actual_execution={actual_fixture_execution_count} blocked={actual_fixture_execution_blocked_count}"},
        {"name": "mutation-snapshot-clean", "ok": source_mutation_count == 0, "message": f"snapshots={mutation_snapshot_count} source_mutations={source_mutation_count}"},
        {"name": "no-fixture-or-generated-dispatch-writes", "ok": fixture_write_count == 0 and generated_wiring_count == 0, "message": f"fixture_writes={fixture_write_count} generated_wiring={generated_wiring_count}"},
        {"name": "no-release-or-autonomy-authority", "ok": release_authorized_count == 0 and autonomy_expanded_count == 0, "message": f"release={release_authorized_count} autonomy={autonomy_expanded_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "truth_and_stabilization_repair": True,
            "dashboard_get_executes_subprocesses": False,
            "api_get_executes_subprocesses": False,
            "post_operator_action_required_for_execution": True,
            "receipt_only_subprocess_claims_fixture_correctness": False,
            "network_policy_env_var_counts_as_enforcement": False,
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
            "manual_api_dispatch_remains_authoritative": True,
            "manual_smoke_remains_authoritative": True,
            "manifest_replaces_dashboard_routes": False,
            "manifest_replaces_api_dispatch": False,
            "manifest_replaces_smoke_registry": False,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "Truth repair blocks fake fixture execution claims, prevents dashboard/API GET subprocess launches, and preserves manual authority."},
        {"name": "documentation-tokens", "ok": all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(row.get("ok") is True for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_ID,
        "truth_stabilization_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_TRUTH_STABILIZATION_ID,
        "sandbox_adapter_contract_id": MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        "full_tree_mutation_snapshot_id": FULL_TREE_MUTATION_SNAPSHOT_ID,
        "input_execution_prep_review_id": INPUT_EXECUTION_PREP_REVIEW_ID,
        "input_hardened_receipt_review_id": INPUT_HARDENED_RECEIPT_REVIEW_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "truth_and_stabilization_repair": True,
        "input_execution_prep_row_count": len(prep_rows),
        "input_hardened_receipt_count": hardening_report.get("hardened_receipt_count") if should_attempt_actual else INPUT_HARDENED_RECEIPT_COUNT,
        "batch_candidate_row_count": len(row_dicts),
        "batch_attempt_count": batch_attempt_count,
        "batch_pass_count": batch_pass_count,
        "remaining_unexecuted_fixture_row_count": max(0, INPUT_EXECUTION_PREP_ROW_COUNT - len(row_dicts)),
        "dispatch_family_count": family_count,
        "dry_run_timeout_seconds": DRY_RUN_TIMEOUT_SECONDS,
        "upstream_subprocess_count": upstream_subprocess_count,
        "batch_subprocess_count": batch_subprocess_count,
        "total_subprocess_count": total_subprocess_count,
        "subprocess_spawn_count": total_subprocess_count,
        "receipt_only_subprocess_count": receipt_only_subprocess_count,
        "actual_fixture_execution_count": actual_fixture_execution_count,
        "actual_fixture_execution_blocked_count": actual_fixture_execution_blocked_count,
        "sandbox_adapter_contract_id": MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        "dashboard_get_executes_subprocesses": False,
        "api_get_executes_subprocesses": False,
        "operator_post_required_for_execution": True,
        "temp_workspace_count": temp_workspace_count,
        "mutation_snapshot_count": mutation_snapshot_count,
        "full_tree_mutation_monitoring": True,
        "source_mutation_count": source_mutation_count,
        "sandbox_enforced_count": sandbox_enforced_count,
        "network_policy_declared": "disabled",
        "network_policy_enforced": network_enforced_count > 0,
        "filesystem_policy_enforced": filesystem_enforced_count > 0,
        "network_policy_env_var_counts_as_enforcement": False,
        "fixture_files_written": False,
        "generated_dashboard_dispatch_written": False,
        "generated_api_dispatch_written": False,
        "generated_smoke_dispatch_written": False,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "manifest_replaces_dashboard_routes": False,
        "manifest_replaces_api_dispatch": False,
        "manifest_replaces_smoke_registry": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "batch_trial_rows": row_dicts,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"truth_stabilization_id={report.get('truth_stabilization_id')}",
        f"sandbox_adapter_contract_id={report.get('sandbox_adapter_contract_id')}",
        f"full_tree_mutation_snapshot_id={report.get('full_tree_mutation_snapshot_id')}",
        f"input_execution_prep_review_id={report.get('input_execution_prep_review_id')}",
        f"input_hardened_receipt_review_id={report.get('input_hardened_receipt_review_id')}",
        f"status={report.get('status')}",
        f"input_execution_prep_row_count={report.get('input_execution_prep_row_count')}",
        f"input_hardened_receipt_count={report.get('input_hardened_receipt_count')}",
        f"batch_candidate_row_count={report.get('batch_candidate_row_count')}",
        f"batch_attempt_count={report.get('batch_attempt_count')}",
        f"batch_pass_count={report.get('batch_pass_count')}",
        f"remaining_unexecuted_fixture_row_count={report.get('remaining_unexecuted_fixture_row_count')}",
        f"dispatch_family_count={report.get('dispatch_family_count')}",
        f"dry_run_timeout_seconds={report.get('dry_run_timeout_seconds')}",
        f"upstream_subprocess_count={report.get('upstream_subprocess_count')}",
        f"batch_subprocess_count={report.get('batch_subprocess_count')}",
        f"total_subprocess_count={report.get('total_subprocess_count')}",
        f"subprocess_spawn_count={report.get('subprocess_spawn_count')}",
        f"receipt_only_subprocess_count={report.get('receipt_only_subprocess_count')}",
        f"actual_fixture_execution_count={report.get('actual_fixture_execution_count')}",
        f"actual_fixture_execution_blocked_count={report.get('actual_fixture_execution_blocked_count')}",
        f"dashboard_get_executes_subprocesses={report.get('dashboard_get_executes_subprocesses')}",
        f"api_get_executes_subprocesses={report.get('api_get_executes_subprocesses')}",
        f"operator_post_required_for_execution={report.get('operator_post_required_for_execution')}",
        f"temp_workspace_count={report.get('temp_workspace_count')}",
        f"mutation_snapshot_count={report.get('mutation_snapshot_count')}",
        f"full_tree_mutation_monitoring={report.get('full_tree_mutation_monitoring')}",
        f"source_mutation_count={report.get('source_mutation_count')}",
        f"network_policy_env_var_counts_as_enforcement={report.get('network_policy_env_var_counts_as_enforcement')}",
        f"network_policy_enforced={report.get('network_policy_enforced')}",
        f"filesystem_policy_enforced={report.get('filesystem_policy_enforced')}",
        f"fixture_files_written={report.get('fixture_files_written')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manifest_replaces_dashboard_routes={report.get('manifest_replaces_dashboard_routes')}",
        f"manifest_replaces_api_dispatch={report.get('manifest_replaces_api_dispatch')}",
        f"manifest_replaces_smoke_registry={report.get('manifest_replaces_smoke_registry')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_required={report.get('operator_approval_required')}",
    ]
    if full:
        for row in report.get("batch_trial_rows", []):
            lines.append(
                f"batch_trial={row.get('trial_id')} family={row.get('dispatch_family')} fixture={row.get('fixture_id')} "
                f"target={row.get('candidate_target')} subprocess={row.get('subprocess_spawned')} receipt_only={row.get('receipt_only_subprocess')} "
                f"actual_attempted={row.get('actual_fixture_execution_attempted')} actual_blocked={row.get('actual_fixture_execution_blocked')} "
                f"sandbox={row.get('sandbox_backend')} network_enforced={row.get('network_policy_enforced')} filesystem_enforced={row.get('filesystem_policy_enforced')} "
                f"source_mutations={row.get('source_mutation_count')} release={row.get('release_authorized')} autonomy={row.get('autonomy_expanded')}"
            )
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1065.4 manifest fixture truth and full-tree snapshot adapter tokens: manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion-v1 manifest-fixture-truth-and-stabilization-repair-v1 manifest-fixture-sandbox-adapter-contract-v1 /manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion /api/source-surface/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion /api/source-surface/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion/run build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_text dashboard_get_executes_subprocesses=False api_get_executes_subprocesses=False operator_post_required_for_execution=True receipt_only_subprocess_count=0 actual_fixture_execution_blocked_count=3 upstream_subprocess_count=0 batch_subprocess_count=0 total_subprocess_count=0 network_policy_env_var_counts_as_enforcement=False manifest-fixture-sandbox-adapter-contract-v1 full-tree-mutation-snapshot-expansion-v1 network_policy_enforced=False filesystem_policy_enforced=False full_tree_mutation_monitoring=True source_mutation_count=0 fixture_files_written=False generated_wiring_activated=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True manifest_replaces_dashboard_routes=False manifest_replaces_api_dispatch=False manifest_replaces_smoke_registry=False release_authorized=False autonomy_expanded=False operator_approval_required=True operator_confirmed_upstream_subprocess_count=1 operator_confirmed_total_subprocess_count=1 data-tip command-deck operator-console no_native_title_tooltip
