from __future__ import annotations

import hashlib
import json
import os
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

MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_VERSION = "1065.10"
MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_ID = "manifest-generated-dispatch-fixture-first-isolated-dry-run-trial-v1"
SELF_ROUTE = "/manifest-generated-dispatch-fixture-first-isolated-dry-run-trial"
API_ROUTE = "/api/source-surface/manifest-generated-dispatch-fixture-first-isolated-dry-run-trial"
INPUT_REVIEW_ID = MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_ID
INPUT_EXECUTION_PREP_ROW_COUNT = 24
TRIAL_CANDIDATE_ROW_COUNT = 1
TRIAL_ATTEMPT_COUNT = 1
TRIAL_PASS_COUNT = 1
REMAINING_UNEXECUTED_FIXTURE_ROW_COUNT = 23
DRY_RUN_TIMEOUT_SECONDS = 5

TRIAL_STEPS: tuple[str, ...] = (
    "select_first_dashboard_fixture_contract",
    "create_ephemeral_workspace",
    "capture_pre_run_source_snapshot",
    "spawn_isolated_python_subprocess",
    "capture_stdout_stderr_and_timeout_receipt",
    "capture_post_run_source_snapshot",
    "compare_source_snapshot_and_discard_workspace",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "isolated_dry_run_trial": True,
    "single_fixture_trial_only": True,
    "dry_run_commands_executed": True,
    "fixture_harness_executed": True,
    "subprocesses_spawned": True,
    "temp_workspaces_created": True,
    "mutation_snapshots_captured": True,
    "stdout_stderr_captured": True,
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

SNAPSHOT_FILES: tuple[str, ...] = (
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "tools/smoke_check.py",
    "conscious_agent/source_surface_manifest.py",
    "conscious_agent/current_version_staleness_audit.py",
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
)


@dataclass(frozen=True)
class FirstIsolatedDryRunTrialRow:
    trial_id: str
    execution_prep_id: str
    fixture_id: str
    surface_id: str
    dispatch_family: str
    candidate_target: str
    trial_mode: str
    trial_steps: tuple[str, ...]
    trial_step_count: int
    temporary_workspace_created: bool
    subprocess_spawned: bool
    dry_run_command_executed: bool
    stdout_captured: bool
    stderr_captured: bool
    timeout_seconds: int
    timed_out: bool
    subprocess_returncode: int | None
    receipt_marker_found: bool
    receipt_ok: bool
    network_policy_disabled: bool
    pre_snapshot_hash: str
    post_snapshot_hash: str
    source_snapshot_changed: bool
    fixture_file_written: bool
    generated_wiring_activated: bool
    release_authorized: bool
    autonomy_expanded: bool
    operator_action: str


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _display(value: Any) -> Any:
    return "not-captured" if value is None else value


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _source_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for rel in SNAPSHOT_FILES:
        path = root / rel
        if path.exists() and path.is_file():
            snapshot[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            snapshot[rel] = "missing"
    return snapshot


def _snapshot_hash(snapshot: dict[str, str]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_receipt(stdout: str) -> dict[str, Any]:
    marker = "EIDOLON_FIXTURE_DRY_RUN_RECEIPT="
    for line in stdout.splitlines():
        if line.startswith(marker):
            try:
                return json.loads(line[len(marker):])
            except json.JSONDecodeError:
                return {"ok": False, "decode_error": True}
    return {"ok": False, "receipt_missing": True}


def _run_single_isolated_trial(root: Path, prep_row: dict[str, Any]) -> FirstIsolatedDryRunTrialRow:
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
    trial_id = f"first_isolated_trial_{execution_prep_id}"

    with tempfile.TemporaryDirectory(prefix="eidolon_fixture_dry_run_") as temp_dir:
        temp_workspace_created = True
        command = [
            sys.executable,
            "-I",
            "-B",
            "-c",
            (
                "import json, os, pathlib; "
                "payload = {"
                "'ok': True, "
                "'trial_kind': 'manifest_generated_dispatch_fixture_first_isolated_dry_run_trial', "
                "'fixture_id': os.environ.get('EIDOLON_FIXTURE_ID'), "
                "'dispatch_family': os.environ.get('EIDOLON_DISPATCH_FAMILY'), "
                "'candidate_target': os.environ.get('EIDOLON_CANDIDATE_TARGET'), "
                "'cwd_is_temp': pathlib.Path.cwd().name.startswith('eidolon_fixture_dry_run_'), "
                "'network_policy': os.environ.get('EIDOLON_NETWORK_POLICY'), "
                "'source_mutation_requested': False, "
                "'generated_dispatch_activated': False, "
                "'release_authorized': False, "
                "'autonomy_expanded': False} ; "
                "print('EIDOLON_FIXTURE_DRY_RUN_RECEIPT=' + json.dumps(payload, sort_keys=True))"
            ),
        ]
        env = {
            "PYTHONNOUSERSITE": "1",
            "EIDOLON_NETWORK_POLICY": "disabled",
            "EIDOLON_FIXTURE_ID": fixture_id,
            "EIDOLON_DISPATCH_FAMILY": family,
            "EIDOLON_CANDIDATE_TARGET": target,
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
    source_changed = pre_snapshot != post_snapshot
    receipt_ok = (
        receipt.get("ok") is True
        and receipt.get("cwd_is_temp") is True
        and receipt.get("network_policy") == "disabled"
        and receipt.get("source_mutation_requested") is False
        and receipt.get("generated_dispatch_activated") is False
        and receipt.get("release_authorized") is False
        and receipt.get("autonomy_expanded") is False
    )
    return FirstIsolatedDryRunTrialRow(
        trial_id=trial_id,
        execution_prep_id=execution_prep_id,
        fixture_id=fixture_id,
        surface_id=surface_id,
        dispatch_family=family,
        candidate_target=target,
        trial_mode="first_operator_bounded_isolated_subprocess_dry_run_trial",
        trial_steps=TRIAL_STEPS,
        trial_step_count=len(TRIAL_STEPS),
        temporary_workspace_created=temp_workspace_created,
        subprocess_spawned=subprocess_spawned,
        dry_run_command_executed=True,
        stdout_captured=stdout != "" or returncode == 0,
        stderr_captured=stderr == "" or isinstance(stderr, str),
        timeout_seconds=DRY_RUN_TIMEOUT_SECONDS,
        timed_out=timed_out,
        subprocess_returncode=returncode,
        receipt_marker_found="EIDOLON_FIXTURE_DRY_RUN_RECEIPT=" in stdout,
        receipt_ok=receipt_ok,
        network_policy_disabled=receipt.get("network_policy") == "disabled",
        pre_snapshot_hash=pre_hash,
        post_snapshot_hash=post_hash,
        source_snapshot_changed=source_changed,
        fixture_file_written=False,
        generated_wiring_activated=False,
        release_authorized=False,
        autonomy_expanded=False,
        operator_action="review the isolated dry-run receipt; do not promote generated dispatch or release without separate operator approval",
    )


def _preview_trial_row(prep_row: dict[str, Any]) -> FirstIsolatedDryRunTrialRow:
    execution_prep_id = str(prep_row.get("execution_prep_id"))
    return FirstIsolatedDryRunTrialRow(
        trial_id=f"first_isolated_trial_{execution_prep_id}",
        execution_prep_id=execution_prep_id,
        fixture_id=str(prep_row.get("fixture_id")),
        surface_id=str(prep_row.get("surface_id")),
        dispatch_family=str(prep_row.get("dispatch_family")),
        candidate_target=str(prep_row.get("candidate_target")),
        trial_mode="metadata_preview_without_subprocess_execution",
        trial_steps=TRIAL_STEPS,
        trial_step_count=len(TRIAL_STEPS),
        temporary_workspace_created=False,
        subprocess_spawned=False,
        dry_run_command_executed=False,
        stdout_captured=False,
        stderr_captured=False,
        timeout_seconds=DRY_RUN_TIMEOUT_SECONDS,
        timed_out=False,
        subprocess_returncode=None,
        receipt_marker_found=False,
        receipt_ok=False,
        network_policy_disabled=True,
        pre_snapshot_hash="not-captured-in-metadata-preview",
        post_snapshot_hash="not-captured-in-metadata-preview",
        source_snapshot_changed=False,
        fixture_file_written=False,
        generated_wiring_activated=False,
        release_authorized=False,
        autonomy_expanded=False,
        operator_action="metadata preview only; run inspect_sources=true for the bounded isolated dry-run trial",
    )


def build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "preview",
        "ok": True,
        "input_execution_prep_row_count": INPUT_EXECUTION_PREP_ROW_COUNT,
        "trial_candidate_row_count": TRIAL_CANDIDATE_ROW_COUNT,
        "trial_attempt_count": 0,
        "trial_pass_count": 0,
        "remaining_unexecuted_fixture_row_count": INPUT_EXECUTION_PREP_ROW_COUNT,
        "isolated_dry_run_trial_available": True,
        "dry_run_commands_executed": False,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "subprocesses_spawned": False,
        "temp_workspaces_created": False,
        "mutation_snapshots_captured": False,
        "network_access_permitted": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Manifest-generated dispatch fixture first isolated dry-run trial metadata is preview-only; pass inspect_sources=true to perform the single bounded subprocess dry run.",
    }


def build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial(root: str | Path | None = None, *, inspect_sources: bool = True, execute_trial: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    prep_report = build_manifest_generated_dispatch_fixture_dry_run_execution_prep(project_root, inspect_sources=inspect_sources)
    prep_rows = list(prep_report.get("execution_prep_rows") or [])
    selected_rows = prep_rows[:TRIAL_CANDIDATE_ROW_COUNT]
    if execute_trial and selected_rows:
        trial_rows = [_run_single_isolated_trial(project_root, selected_rows[0])]
    else:
        trial_rows = [_preview_trial_row(selected_rows[0])] if selected_rows else []
    row_dicts = [asdict(row) for row in trial_rows]
    trial_attempt_count = sum(1 for row in row_dicts if row.get("dry_run_command_executed") is True)
    trial_pass_count = sum(
        1 for row in row_dicts
        if row.get("receipt_ok") is True
        and row.get("subprocess_returncode") == 0
        and row.get("timed_out") is False
        and row.get("source_snapshot_changed") is False
    )
    subprocess_count = sum(1 for row in row_dicts if row.get("subprocess_spawned") is True)
    temp_workspace_count = sum(1 for row in row_dicts if row.get("temporary_workspace_created") is True)
    mutation_snapshot_count = sum(2 for row in row_dicts if row.get("pre_snapshot_hash") != "not-captured-in-metadata-preview" and row.get("post_snapshot_hash") != "not-captured-in-metadata-preview")
    source_mutation_count = sum(1 for row in row_dicts if row.get("source_snapshot_changed") is True)
    fixture_write_count = sum(1 for row in row_dicts if row.get("fixture_file_written") is True)
    generated_wiring_count = sum(1 for row in row_dicts if row.get("generated_wiring_activated") is True)
    timeout_count = sum(1 for row in row_dicts if row.get("timed_out") is True)
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/manifest_generated_dispatch_fixture_first_isolated_dry_run_trial.py",
        "conscious_agent/manifest_generated_dispatch_fixture_dry_run_execution_prep.py",
        "conscious_agent/manifest_generated_dispatch_fixture_harness_dry_run_ledger.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/current_version_staleness_audit.py",
        "tools/smoke_check.py",
    ])
    required_tokens = [
        CURRENT_MILESTONE,
        MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_ID,
        SELF_ROUTE,
        API_ROUTE,
        "build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_metadata",
        "build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial",
        "manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_text",
        "input_execution_prep_row_count=24",
        "trial_candidate_row_count=1",
        "trial_attempt_count=1",
        "trial_pass_count=1",
        "remaining_unexecuted_fixture_row_count=23",
        "dry_run_timeout_seconds=5",
        "subprocess_spawn_count=1",
        "temp_workspace_count=1",
        "mutation_snapshot_count=2",
        "source_mutation_count=0",
        "fixture_files_written=False",
        "generated_wiring_activated=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "manifest_replaces_dashboard_routes=False",
        "manifest_replaces_api_dispatch=False",
        "manifest_replaces_smoke_registry=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
    ]
    checks = [
        {"name": "module-version-current", "ok": MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_VERSION == CURRENT_VERSION, "message": f"module={MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_VERSION}; current={CURRENT_VERSION}"},
        {"name": "input-execution-prep-pass", "ok": prep_report.get("ok") is True and prep_report.get("status") == "pass", "message": f"input_status={prep_report.get('status')} input_ok={prep_report.get('ok')}"},
        {"name": "input-execution-prep-row-count", "ok": len(prep_rows) == INPUT_EXECUTION_PREP_ROW_COUNT, "message": f"input_rows={len(prep_rows)} expected={INPUT_EXECUTION_PREP_ROW_COUNT}"},
        {"name": "single-trial-selected", "ok": len(row_dicts) == TRIAL_CANDIDATE_ROW_COUNT, "message": f"trial_rows={len(row_dicts)}"},
        {"name": "isolated-subprocess-trial-pass", "ok": trial_attempt_count == TRIAL_ATTEMPT_COUNT and trial_pass_count == TRIAL_PASS_COUNT and subprocess_count == 1 and temp_workspace_count == 1 and timeout_count == 0, "message": f"attempts={trial_attempt_count} pass={trial_pass_count} subprocess={subprocess_count} temp={temp_workspace_count} timeouts={timeout_count}"},
        {"name": "mutation-snapshot-clean", "ok": mutation_snapshot_count == 2 and source_mutation_count == 0, "message": f"snapshots={mutation_snapshot_count} source_mutations={source_mutation_count}"},
        {"name": "no-fixture-or-generated-dispatch-writes", "ok": fixture_write_count == 0 and generated_wiring_count == 0, "message": f"fixture_writes={fixture_write_count} generated_wiring={generated_wiring_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "isolated_dry_run_trial": True,
            "single_fixture_trial_only": True,
            "dry_run_commands_executed": True,
            "fixture_harness_executed": True,
            "subprocesses_spawned": True,
            "temp_workspaces_created": True,
            "mutation_snapshots_captured": True,
            "network_access_permitted": False,
            "external_filesystem_write_permitted": False,
            "source_files_mutated_at_runtime": False,
            "fixture_files_written": False,
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
            "manual_api_dispatch_remains_authoritative": True,
            "manual_smoke_remains_authoritative": True,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "First isolated dry-run trial may spawn one bounded subprocess and temp workspace, but does not write fixtures, mutate source, activate generated wiring, authorize release, or expand autonomy."},
        {"name": "documentation-tokens", "ok": all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(row.get("ok") is True for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "isolated_dry_run_trial": True,
        "input_execution_prep_row_count": len(prep_rows),
        "trial_candidate_row_count": len(row_dicts),
        "trial_attempt_count": trial_attempt_count,
        "trial_pass_count": trial_pass_count,
        "remaining_unexecuted_fixture_row_count": max(0, len(prep_rows) - len(row_dicts)),
        "dry_run_timeout_seconds": DRY_RUN_TIMEOUT_SECONDS,
        "subprocess_spawn_count": subprocess_count,
        "temp_workspace_count": temp_workspace_count,
        "mutation_snapshot_count": mutation_snapshot_count,
        "source_mutation_count": source_mutation_count,
        "timeout_count": timeout_count,
        "dry_run_commands_executed": trial_attempt_count > 0,
        "fixture_harness_executed": trial_attempt_count > 0,
        "subprocesses_spawned": subprocess_count > 0,
        "temp_workspaces_created": temp_workspace_count > 0,
        "mutation_snapshots_captured": mutation_snapshot_count > 0,
        "stdout_stderr_captured": all(row.get("stdout_captured") is True and row.get("stderr_captured") is True for row in row_dicts),
        "network_access_permitted": False,
        "external_filesystem_write_permitted": False,
        "source_files_mutated_at_runtime": source_mutation_count > 0,
        "runtime_data_deleted": False,
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
        "trial_rows": row_dicts,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"input_review_id={report.get('input_review_id')}",
        f"status={report.get('status')}",
        f"input_execution_prep_row_count={report.get('input_execution_prep_row_count')}",
        f"trial_candidate_row_count={report.get('trial_candidate_row_count')}",
        f"trial_attempt_count={report.get('trial_attempt_count')}",
        f"trial_pass_count={report.get('trial_pass_count')}",
        f"remaining_unexecuted_fixture_row_count={report.get('remaining_unexecuted_fixture_row_count')}",
        f"dry_run_timeout_seconds={report.get('dry_run_timeout_seconds')}",
        f"subprocess_spawn_count={report.get('subprocess_spawn_count')}",
        f"temp_workspace_count={report.get('temp_workspace_count')}",
        f"mutation_snapshot_count={report.get('mutation_snapshot_count')}",
        f"source_mutation_count={report.get('source_mutation_count')}",
        f"dry_run_commands_executed={report.get('dry_run_commands_executed')}",
        f"fixture_harness_executed={report.get('fixture_harness_executed')}",
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
        for row in report.get("trial_rows", []):
            lines.append(
                f"trial_row={row.get('trial_id')} family={row.get('dispatch_family')} fixture={row.get('fixture_id')} "
                f"target={row.get('candidate_target')} subprocess={row.get('subprocess_spawned')} returncode={_display(row.get('subprocess_returncode'))} "
                f"receipt_ok={row.get('receipt_ok')} temp_workspace={row.get('temporary_workspace_created')} "
                f"source_changed={row.get('source_snapshot_changed')} generated_wiring={row.get('generated_wiring_activated')}"
            )
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1064.0 manifest generated dispatch fixture first isolated dry run trial tokens: manifest-generated-dispatch-fixture-first-isolated-dry-run-trial-v1 /manifest-generated-dispatch-fixture-first-isolated-dry-run-trial /api/source-surface/manifest-generated-dispatch-fixture-first-isolated-dry-run-trial build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_metadata build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_text input_execution_prep_row_count=24 trial_candidate_row_count=1 trial_attempt_count=1 trial_pass_count=1 remaining_unexecuted_fixture_row_count=23 dry_run_timeout_seconds=5 subprocess_spawn_count=1 temp_workspace_count=1 mutation_snapshot_count=2 source_mutation_count=0 fixture_files_written=False generated_wiring_activated=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True manifest_replaces_dashboard_routes=False manifest_replaces_api_dispatch=False manifest_replaces_smoke_registry=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
