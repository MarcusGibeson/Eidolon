from __future__ import annotations

from release_metadata import RUNTIME_VERSION

"""Authoritative current release-integrity report.

This module consolidates the current runtime, active-project, dashboard registry,
navigation, smoke registry, safety boundary, and source syntax signals into one
read-only report. It does not execute fixtures, mutate source, authorize a
release, or expand autonomy. Humanity has produced enough dashboards that
confuse evidence with permission; this one declines to join them.
"""

import ast
import argparse
import json
import os
import hashlib
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

# Support both the project's historical script-style imports and standard
# package execution via ``python -m conscious_agent...``.
MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent
for import_dir in (MODULE_DIR, PROJECT_ROOT / "tools"):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

from release_metadata import NEXT_RECOMMENDED_ARC, RUNTIME_MILESTONE, RUNTIME_VERSION
from source_project_metadata import load_source_project_metadata
from verification_evidence import evidence_stage_report, load_evidence_bundle

MODULE_VERSION = RUNTIME_VERSION
CHECK_ID = "registry-navigation-smoke-consolidation-v1"
TITLE = "Verification Truth and Evidence Attestation Hotfix"


@dataclass(frozen=True)
class IntegrityRow:
    name: str
    status: str
    summary: str
    details: Any = None
    required: bool = True

    @property
    def ok(self) -> bool:
        return self.status in {"pass", "warn"} if not self.required else self.status == "pass"

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok"] = self.ok
        return payload


def _row(name: str, ok: bool, summary: str, details: Any = None, *, required: bool = True) -> IntegrityRow:
    return IntegrityRow(name, "pass" if ok else ("warn" if not required else "fail"), summary, details, required)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _assignment_value(path: Path, name: str) -> str | None:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        for target in targets:
            if not isinstance(target, ast.Name) or target.id != name:
                continue
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
            if isinstance(value, ast.Name) and value.id == "RUNTIME_VERSION":
                return RUNTIME_VERSION
    return None




def _source_snapshot(root: Path) -> dict[str, str]:
    """Hash release-owned source and configuration files without touching runtime data."""
    paths: set[Path] = set()
    for directory in (root / "conscious_agent", root / "tools"):
        if directory.exists():
            paths.update(path for path in directory.rglob("*.py") if path.is_file())
    for pattern in ("*.py", "*.ps1", "*.sh", "requirements*.txt", "README*.md"):
        paths.update(path for path in root.glob(pattern) if path.is_file())
    for rel in (
        "data/settings.json",
        "data/workspaces/active_project.json",
        "data/workspaces/projects.json",
    ):
        path = root / rel
        if path.is_file():
            paths.add(path)
    snapshot: dict[str, str] = {}
    for path in sorted(paths):
        try:
            snapshot[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            snapshot[path.relative_to(root).as_posix()] = "[unreadable]"
    return snapshot


def _snapshot_delta(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    before_names = set(before)
    after_names = set(after)
    added = sorted(after_names - before_names)
    removed = sorted(before_names - after_names)
    changed = sorted(name for name in before_names & after_names if before[name] != after[name])
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "source_write_count": len(added) + len(changed),
        "source_delete_count": len(removed),
    }


def _unsafe_persisted_flags(value: Any, prefix: str = "") -> list[dict[str, Any]]:
    unsafe_keys = {
        "release_authorized",
        "autonomy_expanded",
        "generated_wiring_activated",
        "actual_fixture_execution_allowed",
    }
    findings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in unsafe_keys and child is True:
                findings.append({"path": path, "value": child})
            findings.extend(_unsafe_persisted_flags(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_unsafe_persisted_flags(child, f"{prefix}[{index}]"))
    return findings


def _initial_action_log_evidence(root: Path) -> dict[str, Any]:
    """Capture persisted action evidence before runtime imports can initialize empty files."""
    path = root / "data" / "action_log.json"
    if not path.exists():
        return {
            "action_log_state": "absent_source_only_empty_state",
            "action_log_valid": True,
            "action_record_count": 0,
            "unsafe_true_flags": [],
        }
    try:
        payload = _load_json(path)
    except Exception:
        payload = None
    valid = isinstance(payload, list)
    return {
        "action_log_state": "present_valid" if valid else "present_malformed",
        "action_log_valid": valid,
        "action_record_count": len(payload) if isinstance(payload, list) else 0,
        "unsafe_true_flags": _unsafe_persisted_flags(payload if valid else []),
    }


def _python_syntax_row(root: Path, evidence: dict[str, Any] | None = None) -> IntegrityRow:
    files = sorted((root / "conscious_agent").rglob("*.py")) + sorted((root / "tools").rglob("*.py"))
    launcher = root / "eidolon.py"
    if launcher.exists():
        files.append(launcher)
    compile_report = evidence_stage_report(evidence, "python-compile")
    if (
        isinstance(compile_report, dict)
        and compile_report.get("ok") is True
        and compile_report.get("status") == "pass"
        and compile_report.get("source_tree_mutation_count") == 0
        and compile_report.get("source_tree_bytecode_written") is False
        and compile_report.get("compile_execution_count") == 1
    ):
        return _row(
            "python-syntax",
            True,
            f"Accepted one attested outer compile for {len(files)} Python files.",
            {"mode": "attested_outer_python_compile", "file_count": len(files), "compile_execution_count": 1},
        )
    errors: list[str] = []
    for path in files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return _row(
        "python-syntax", not errors, f"Parsed {len(files)} Python files.",
        {"mode": "standalone_full_ast_parse", "failures": errors},
    )


def _metadata_rows(root: Path) -> list[IntegrityRow]:
    rows: list[IntegrityRow] = []
    projects = load_source_project_metadata(root)
    settings_path = root / "data" / "settings.json"
    settings = _load_json(settings_path) if settings_path.is_file() else {
        "approval_required_for_file_edits": True,
        "approval_required_for_rollbacks": True,
        "safe_mode": "strict",
    }
    workspace_active_path = root / "data" / "workspaces" / "active_project.json"
    workspace_projects_path = root / "data" / "workspaces" / "projects.json"
    workspace_active = _load_json(workspace_active_path) if workspace_active_path.is_file() else {
        "active_project_id": projects.get("active_project_id"),
        "current_milestone": projects.get("current_milestone"),
        "next_recommended_arc": projects.get("next_recommended_arc"),
    }
    workspace_projects = _load_json(workspace_projects_path) if workspace_projects_path.is_file() else {
        "active_project_id": projects.get("active_project_id"),
        "current_milestone": projects.get("current_milestone"),
        "next_recommended_arc": projects.get("next_recommended_arc"),
        "projects": projects.get("projects", []),
    }

    current = projects.get("current_project") or {}
    declared = str(projects.get("active_project") or "")
    names = [str(item.get("name") or "") for item in projects.get("projects", []) if isinstance(item, dict)]
    rows.append(_row(
        "active-project-metadata",
        bool(declared) and declared == current.get("name") and declared in names,
        "Root active-project metadata resolves to an existing current project.",
        {"active_project": declared, "current_project": current.get("name"), "project_count": len(names)},
    ))

    workspace_active_id = str(workspace_active.get("active_project_id") or "")
    workspace_entries = [item for item in workspace_projects.get("projects", []) if isinstance(item, dict)]
    workspace_match = next((item for item in workspace_entries if str(item.get("id") or "") == workspace_active_id), None)
    active_values = {
        "root_name": declared,
        "workspace_active_id": workspace_active_id,
        "workspace_project_name": (workspace_match or {}).get("name"),
        "workspace_project_ids": [str(item.get("id") or "") for item in workspace_entries],
    }
    rows.append(_row(
        "active-project-cross-file-alignment",
        bool(workspace_active_id) and isinstance(workspace_match, dict) and workspace_match.get("name") == declared,
        "Root active-project name and workspace stable-id selector resolve to the same project.",
        active_values,
    ))

    milestone_values = {
        "runtime": RUNTIME_MILESTONE,
        "projects": projects.get("current_milestone"),
        "workspace_active": workspace_active.get("current_milestone"),
        "workspace_projects": workspace_projects.get("current_milestone"),
    }
    rows.append(_row(
        "current-milestone-alignment",
        all(value == RUNTIME_MILESTONE for value in milestone_values.values()),
        "All current-state metadata files use the runtime milestone.",
        milestone_values,
    ))

    next_values = {
        "runtime": NEXT_RECOMMENDED_ARC,
        "projects": projects.get("next_recommended_arc"),
        "workspace_active": workspace_active.get("next_recommended_arc"),
        "workspace_projects": workspace_projects.get("next_recommended_arc"),
    }
    rows.append(_row(
        "next-arc-alignment",
        all(value == NEXT_RECOMMENDED_ARC for value in next_values.values()),
        "All current-state metadata files use the same next recommended arc.",
        next_values,
    ))
    return rows


def _runtime_rows(root: Path) -> list[IntegrityRow]:
    rows: list[IntegrityRow] = []
    markers = {
        "conscious_agent/api_server.py": "API_VERSION",
        "conscious_agent/dashboard.py": "DASHBOARD_VERSION",
        "conscious_agent/stabilization_checkpoint.py": "STABILIZATION_CHECKPOINT_VERSION",
        "conscious_agent/current_version_staleness_audit.py": "CURRENT_VERSION",
        "tools/smoke_registry_check_rows.py": "SMOKE_REGISTRY_CHECK_ROWS_VERSION",
    }
    values = {rel: _assignment_value(root / rel, marker) for rel, marker in markers.items()}
    rows.append(_row(
        "runtime-version-alignment",
        all(value == RUNTIME_VERSION for value in values.values()),
        "Primary runtime, dashboard, API, stabilization, and smoke registry versions agree.",
        {"expected": RUNTIME_VERSION, **values},
    ))

    from project_manager import get_active_project
    active = get_active_project()
    rows.append(_row(
        "active-project-runtime-resolution",
        isinstance(active, dict) and bool(active.get("name")),
        "The live project manager resolves an active project.",
        active,
    ))

    from api_server import build_status_payload
    status = build_status_payload()
    api_active = status.get("active_project") or {}
    rows.append(_row(
        "api-status-active-project",
        isinstance(api_active, dict) and api_active.get("name") == (active or {}).get("name"),
        "The API status payload agrees with the live project manager.",
        api_active,
    ))
    return rows


def _dashboard_rows(root: Path) -> list[IntegrityRow]:
    from dashboard_route_registry import DASHBOARD_ROUTE_REGISTRY_ITEMS

    rows: list[IntegrityRow] = []
    paths = [item.path for item in DASHBOARD_ROUTE_REGISTRY_ITEMS]
    duplicate_paths = sorted({path for path in paths if paths.count(path) > 1})
    rows.append(_row(
        "dashboard-registry-unique-paths",
        not duplicate_paths,
        f"Dashboard route registry contains {len(paths)} unique route declarations.",
        duplicate_paths,
    ))

    dashboard_source = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (
            root / "conscious_agent" / "dashboard.py",
            root / "conscious_agent" / "dashboard_layout.py",
        )
    )
    missing_renderers = sorted({item.renderer_name for item in DASHBOARD_ROUTE_REGISTRY_ITEMS if f"def {item.renderer_name}(" not in dashboard_source})
    rows.append(_row(
        "dashboard-registry-renderers-exist",
        not missing_renderers,
        "Every registered dashboard route names a concrete renderer.",
        missing_renderers,
    ))

    nav_tuples = [item.nav_tuple() for item in DASHBOARD_ROUTE_REGISTRY_ITEMS]
    rows.append(_row(
        "dashboard-navigation-metadata",
        len(nav_tuples) == len(paths) and all(len(item) == 4 and item[0].startswith("/") for item in nav_tuples),
        "Every registered route contributes complete navigation metadata.",
        {"route_count": len(paths), "navigation_count": len(nav_tuples)},
    ))

    from dashboard_dispatcher_parity import build_dashboard_dispatcher_parity_report
    parity = build_dashboard_dispatcher_parity_report(root, expected_version=RUNTIME_VERSION)
    blocked = [item for item in parity.get("rows", []) if not item.get("ok")]
    rows.append(_row(
        "dashboard-dispatcher-parity",
        parity.get("ok") is True,
        "Registry, renderer metadata, and the manual HTTP dispatcher remain aligned.",
        blocked[:20],
    ))

    prefix_ok = 'path == "/api" or path.startswith("/api/")' in dashboard_source
    native_title = ' title="' in dashboard_source or " title='" in dashboard_source
    rows.append(_row(
        "dashboard-api-info-routing",
        prefix_ok,
        "/api-info remains separate from the dashboard API prefix.",
        None,
    ))
    rows.append(_row(
        "dashboard-custom-tooltip-contract",
        "data-tip" in dashboard_source and not native_title,
        "Dashboard navigation preserves the custom data-tip tooltip contract without native title attributes.",
        {"data_tip_present": "data-tip" in dashboard_source, "native_title_present": native_title},
    ))
    return rows


def _smoke_rows(root: Path) -> list[IntegrityRow]:
    from smoke_registry_check_rows import SMOKE_REGISTRY_CHECK_ROW_SPECS
    from smoke_registry_metadata import SMOKE_TIER_ORDER

    rows: list[IntegrityRow] = []
    names = [item.name for item in SMOKE_REGISTRY_CHECK_ROW_SPECS]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    rows.append(_row(
        "smoke-sidecar-unique-names",
        not duplicate_names,
        f"Smoke sidecar contains {len(names)} uniquely named checks.",
        duplicate_names,
    ))

    allowed = set(SMOKE_TIER_ORDER)
    invalid_tiers = sorted({item.tier for item in SMOKE_REGISTRY_CHECK_ROW_SPECS if item.tier not in allowed})
    invalid_timeouts = [item.name for item in SMOKE_REGISTRY_CHECK_ROW_SPECS if int(item.timeout) <= 0]
    rows.append(_row(
        "smoke-sidecar-contracts",
        not invalid_tiers and not invalid_timeouts,
        "Smoke sidecar tiers and timeout budgets are valid.",
        {"invalid_tiers": invalid_tiers, "invalid_timeouts": invalid_timeouts, "allowed_tiers": sorted(allowed)},
    ))

    resolution_error: str | None = None
    resolved_names: list[str] = []
    try:
        import smoke_check as smoke_module
        from smoke_registry_check_rows import build_smoke_checks_from_specs

        def factory(name: str, tier: str, timeout: int, callback: Any) -> dict[str, Any]:
            if not callable(callback):
                raise TypeError(f"Smoke callback is not callable: {name}")
            return {"name": name, "tier": tier, "timeout": timeout, "callback": callback}

        resolved = build_smoke_checks_from_specs(
            factory,
            vars(smoke_module),
            project_root=root,
            expected_version=RUNTIME_VERSION,
        )
        resolved_names = [str(item.get("name")) for item in resolved]
    except Exception as exc:
        resolution_error = repr(exc)
    rows.append(_row(
        "smoke-sidecar-callables",
        resolution_error is None and resolved_names == names,
        "Every smoke sidecar row resolves through the authoritative builder to a concrete callable.",
        {"resolution_error": resolution_error, "resolved_count": len(resolved_names), "expected_count": len(names)},
    ))

    registered = CHECK_ID in names
    rows.append(_row(
        "current-release-smoke-registered",
        registered,
        "The current consolidated release-integrity check is registered in the authoritative smoke sidecar.",
        {"check_id": CHECK_ID},
    ))
    return rows



def _upgrade_migration_behavioral_proof(
    upgrade_migrate: Any,
    targeted_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    try:
        if targeted_evidence is None:
            import pre_v1078_9_corrective_tests as corrective_tests
            targeted = corrective_tests.run_targeted_regressions()
            targeted_source = "executed_by_integrity_report"
        else:
            targeted = targeted_evidence
            targeted_source = "injected_outer_verifier_evidence"
        checks["directory-inventory-schema-and-negative-fixtures"] = (
            targeted.get("ok") is True
            and targeted.get("real_evidence_touched") is False
            and all(targeted.get("checks", {}).get(name) is True for name in (
                "valid-complete-directory",
                "unsafe-artifact-content",
                "unexpected-json-file",
                "stale-evidence",
                "duplicate-references",
                "traversal-attempt",
                "hash-mismatch",
                "missing-artifact",
                "symlink-target-rejected",
                "symlink-artifact-rejected",
                "windows-reparse-point-fixture",
            ))
        )
        checks["setup-migration-review-boundary"] = (
            targeted.get("checks", {}).get("default-migration-is-review-only") is True
            and targeted.get("checks", {}).get("setup-explicit-migration-opt-in") is True
        )
        checks["bounded-compile-command-regression"] = all(
            targeted.get("checks", {}).get(name) is True
            for name in (
                "winerror-206-command-length-regression",
                "disposable-bytecode-cache",
                "compile-free-space-preflight",
                "version-inventory-prefilter-pattern",
            )
        )

        with tempfile.TemporaryDirectory(prefix="eidolon-migration-transaction-") as temp_dir:
            test_root = Path(temp_dir)
            for rel_dir, _ledger_name, _names in upgrade_migrate.TARGETS:
                base = test_root / rel_dir
                base.mkdir(parents=True, exist_ok=True)
                (base / "stale.json").write_text(json.dumps({"schema_version": "1032.0"}), encoding="utf-8")
            calls: list[tuple[Path, Path]] = []

            def flaky_move(source: str, destination: str) -> Any:
                source_path = Path(source)
                destination_path = Path(destination)
                calls.append((source_path, destination_path))
                forward = source_path.as_posix().startswith(test_root.as_posix() + "/sandbox/generated_")
                if forward:
                    manifest = destination_path.parent / "migration_manifest.json"
                    if not manifest.is_file():
                        raise AssertionError("transaction manifest absent before forward move")
                    forward_count = sum(
                        1 for prior_source, _ in calls
                        if prior_source.as_posix().startswith(test_root.as_posix() + "/sandbox/generated_")
                    )
                    if forward_count == 2:
                        raise OSError("simulated second move failure")
                return shutil.move(source, destination)

            report = upgrade_migrate.build_migration_report(test_root, apply=True, _move=flaky_move)
            manifest_path = test_root / str(report.get("quarantine_root")) / "migration_manifest.json"
            manifest = _load_json(manifest_path) if manifest_path.is_file() else {}
            checks["failed-second-move-rolls-back-with-manifest"] = (
                report.get("ok") is False
                and report.get("transaction_status") == "rolled_back"
                and all((test_root / rel_dir).is_dir() for rel_dir, _ledger_name, _names in upgrade_migrate.TARGETS)
                and manifest.get("transaction_status") == "rolled_back"
                and bool(manifest.get("planned"))
            )
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    return {
        "ok": not errors and all(checks.values()) and len(checks) == 4,
        "checks": checks,
        "errors": errors,
        "targeted_regression_source": targeted_source if not errors else None,
    }

def _operator_release_rows(
    root: Path,
    evidence: dict[str, Any] | None = None,
    evidence_metadata: dict[str, Any] | None = None,
) -> list[IntegrityRow]:
    """Validate the operator-facing verification and upgrade contracts behaviorally."""
    rows: list[IntegrityRow] = []
    evidence_metadata = dict(evidence_metadata or {})
    evidence_provided = evidence_metadata.get("provided") is True
    evidence_rejected = evidence_provided and evidence_metadata.get("valid") is not True
    rows.append(_row(
        "verification-evidence-attestation",
        not evidence_rejected,
        "Provided outer-verifier evidence passed schema, freshness, source, command, receipt, nonce, producer, and HMAC validation."
        if evidence_provided and not evidence_rejected
        else (
            "Provided outer-verifier evidence was rejected; the integrity report will not rerun or silently replace its claimed stages."
            if evidence_rejected
            else "No outer-verifier evidence was provided; this standalone report owns its expensive stages."
        ),
        evidence_metadata,
    ))

    import release_verify

    expected_smoke_steps = (
        ("release", ("--tier", "release")),
        ("install-release", (
            "--segment", "install-release",
            "--skip-check", "code-patch-release",
            "--skip-check", "release-pipeline",
            "--skip-check", "approval-release-workflow",
            *release_verify._skip_check_args(release_verify.SUPERSEDED_INSTALL_RELEASE_CHECKS),
        )),
        ("install-regression-recent", (
            "--segment", "install-regression-recent",
            "--skip-check", "current-state-integrity-staleness-hardening-v1",
        )),
    )
    actual_smoke_steps = tuple(
        (name, tuple(smoke_args))
        for name, smoke_args, _timeout in release_verify.FULL_RELEASE_SMOKE_STEPS
    )
    route_budgets = dict(release_verify.DASHBOARD_ROUTE_TIMEOUTS)
    worker_path = Path(release_verify.DASHBOARD_PROBE_WORKER)
    verifier_source = (root / "tools" / "release_verify.py").read_text(encoding="utf-8", errors="replace")
    smoke_source = (root / "tools" / "smoke_check.py").read_text(encoding="utf-8", errors="replace")
    rows.append(_row(
        "authoritative-full-verifier-contract",
        actual_smoke_steps == expected_smoke_steps
        and len(release_verify.SUPERSEDED_INSTALL_RELEASE_CHECKS) == 21
        and "dashboard-route-registry-extraction-v1" in release_verify.SUPERSEDED_INSTALL_RELEASE_CHECKS
        and "operator-governed-metadata-release-integrity-v1" in release_verify.SUPERSEDED_INSTALL_RELEASE_CHECKS
        and 60 <= route_budgets.get("/stabilization", 0) <= 120
        and worker_path.is_file()
        and "start_new_session" in verifier_source
        and "_terminate_worker_tree(process)" in verifier_source
        and "_source_tree_snapshot" in verifier_source
        and "source-tree-immutability" in verifier_source
        and "tools/verification_source_compile.py" in verifier_source
        and "tools/import_compatibility_quick.py" in verifier_source
        and "import-compatibility" in verifier_source
        and "build_project_registry(repair=False)" in smoke_source
        and "build_command_profiles(save=False)" in smoke_source
        and 'build_patch_plan(project_id="eidolon", target_version="14.0", save=False)' in smoke_source
        and "os._exit(exit_code)" in smoke_source,
        "The full verifier covers the active release superset once, records outer-owned install-release skips, isolates command trees, uses a bounded stabilization summary, and avoids duplicate compilation in quick smoke.",
        {
            "expected_smoke_steps": [[name, list(args)] for name, args in expected_smoke_steps],
            "actual_smoke_steps": [[name, list(args)] for name, args in actual_smoke_steps],
            "dashboard_route_timeouts": route_budgets,
            "probe_worker": worker_path.relative_to(root).as_posix() if worker_path.is_relative_to(root) else str(worker_path),
            "generic_process_group_isolation": "start_new_session" in verifier_source and "_terminate_worker_tree(process)" in verifier_source,
            "whole_run_source_hashing": "_source_tree_snapshot" in verifier_source and "source-tree-immutability" in verifier_source,
            "non_mutating_smoke_contract": "build_project_registry(repair=False)" in smoke_source and "build_command_profiles(save=False)" in smoke_source,
            "smoke_runner_authoritative_exit": "os._exit(exit_code)" in smoke_source,
            "bounded_stabilization_budget": 60 <= route_budgets.get("/stabilization", 0) <= 120,
            "quick_smoke_skips_duplicate_compile": "--skip-check" in verifier_source and "compile" in verifier_source,
            "in_memory_compile_registered": "tools/verification_source_compile.py" in verifier_source,
            "lightweight_import_regression_registered": "tools/import_compatibility_quick.py" in verifier_source and "import-compatibility" in verifier_source,
        },
    ))

    setup_source = (root / "setup.ps1").read_text(encoding="utf-8", errors="replace")
    setup_sh_source = (root / "setup.sh").read_text(encoding="utf-8", errors="replace")
    native_steps = (
        "Virtual environment creation",
        "pip upgrade",
        "Dependency installation",
        "Upgrade evidence inspection",
        "Quick release verification",
    )
    setup_ok = (
        "function Assert-NativeSuccess" in setup_source
        and all(f'Assert-NativeSuccess "{step}"' in setup_source for step in native_steps)
        and "[switch]$ApplyUpgradeMigration" in setup_source
        and "if ($ApplyUpgradeMigration)" in setup_source
        and "--apply-upgrade-migration" in setup_sh_source
        and 'if [ "$APPLY_UPGRADE_MIGRATION" -eq 1 ]' in setup_sh_source
        and "upgrade_migrate.py\") --apply --quiet" not in setup_source
        and 'upgrade_migrate.py" --apply --quiet' not in setup_sh_source
        and setup_source.rfind('Assert-NativeSuccess "Quick release verification"')
        < setup_source.rfind('Write-Host "Ready. Useful commands:"')
    )
    rows.append(_row(
        "setup-fail-closed-and-migration-review-boundary",
        setup_ok,
        "Setup checks native exits and inspects migration by default; moving evidence requires an explicit platform-specific opt-in.",
        {"required_native_steps": list(native_steps), "powershell_opt_in": "-ApplyUpgradeMigration", "shell_opt_in": "--apply-upgrade-migration"},
    ))

    import upgrade_migrate

    migration = upgrade_migrate.build_migration_report(root, apply=False)
    migration_clean = (
        migration.get("ok") is True
        and migration.get("files_deleted") == 0
        and migration.get("source_files_modified") == 0
        and migration.get("reversible") is True
        and migration.get("quarantine_required_count") == 0
    )
    corrective_evidence = evidence_stage_report(evidence, "corrective-suite")
    if evidence_rejected:
        corrective_evidence = {
            "ok": False,
            "status": "blocked",
            "checks": {},
            "real_evidence_touched": False,
            "evidence_source": "rejected_attestation",
        }
    migration_behavior = _upgrade_migration_behavioral_proof(upgrade_migrate, corrective_evidence)
    rows.append(_row(
        "upgrade-migration-path-hash-transaction-proof",
        migration_behavior.get("ok") is True,
        "Temporary fixtures prove exact path/hash validation and manifest-first rollback behavior without touching operator evidence.",
        migration_behavior,
    ))

    inventory_command = [
        sys.executable,
        "-m",
        "conscious_agent.version_metadata_inventory",
        "--root",
        str(root),
        "--json",
    ]
    version_inventory = evidence_stage_report(evidence, "version-inventory")
    inventory_source = "injected_outer_verifier_evidence" if version_inventory is not None else "executed_by_integrity_report"
    if evidence_rejected:
        inventory_source = "rejected_attestation"
        version_inventory = {
            "ok": False,
            "status": "blocked",
            "error": evidence_metadata.get("reason") or "outer-verifier evidence rejected",
            "worker_parse_ok": False,
        }
    elif version_inventory is None:
        try:
            inventory_completed = subprocess.run(
                inventory_command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=90,
                env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            try:
                version_inventory = json.loads(inventory_completed.stdout)
                version_inventory["worker_exit_code"] = inventory_completed.returncode
                version_inventory["worker_exit_ok"] = inventory_completed.returncode == 0
                version_inventory["worker_parse_ok"] = True
            except json.JSONDecodeError as exc:
                version_inventory = {
                    "ok": False,
                    "status": "blocked",
                    "error": f"JSONDecodeError: {exc}",
                    "worker_exit_code": inventory_completed.returncode,
                    "worker_exit_ok": inventory_completed.returncode == 0,
                    "worker_parse_ok": False,
                    "stderr_tail": "\n".join(inventory_completed.stderr.splitlines()[-20:]),
                }
        except subprocess.TimeoutExpired as exc:
            version_inventory = {"ok": False, "status": "blocked", "error": f"TimeoutExpired: {exc}", "worker_parse_ok": False}
    version_inventory = dict(version_inventory or {})
    version_inventory.setdefault("evidence_source", inventory_source)
    import_regression_source = (root / "tools" / "import_compatibility_regression.py").read_text(encoding="utf-8", errors="replace")
    rows.append(_row(
        "import-compatibility-regression-architecture",
        "PACKAGE_SENTINEL" in import_regression_source
        and "SCRIPT_SENTINEL" in import_regression_source
        and "IMPORT_CASES" in import_regression_source
        and "REPORT_CASES" in import_regression_source
        and "expensive_reports_used_for_import_resolution" in import_regression_source
        and '"--mode"' in import_regression_source,
        "Lightweight script/package import sentinels are registered separately from complete report-performance measurements.",
        {
            "authoritative_verifier_step": "import-compatibility",
            "import_mode": "imports",
            "complete_report_mode": "reports",
        },
    ))

    rows.append(_row(
        "active-version-metadata-centralization-foundation",
        version_inventory.get("ok") is True
        and version_inventory.get("text_prefilter_enabled") is True
        and version_inventory.get("ast_parsed_source_file_count", 10**9) < version_inventory.get("scanned_source_file_count", 0)
        and version_inventory.get("scan_scope", {}).get("runtime_data_scanned") is False
        and version_inventory.get("scan_scope", {}).get("sandbox_evidence_scanned") is False,
        "One runtime authority now feeds active consumers; release-owned inventory uses a read-once text prefilter and excludes runtime or sandbox state.",
        version_inventory,
    ))

    rows.append(_row(
        "in-place-upgrade-evidence-hygiene",
        migration_clean,
        "No partial retired sandbox evidence remains; the reversible migration is ready for replacement-based upgrades."
        if migration_clean
        else "Retired partial sandbox evidence must be quarantined before authoritative verification.",
        {
            **migration,
            "repair_command": "python eidolon.py upgrade-migrate --apply",
        },
    ))

    dashboard_source = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (
            root / "conscious_agent" / "dashboard.py",
            root / "conscious_agent" / "dashboard_layout.py",
        )
    )
    current_label = "CORE v{DASHBOARD_VERSION}"
    rows.append(_row(
        "dashboard-operator-status-label",
        "CORE v170.0" not in dashboard_source
        and "ALL SYSTEMS NOMINAL" not in dashboard_source
        and current_label in dashboard_source
        and "OPERATOR-GOVERNED" in dashboard_source,
        "The dashboard footer reports the current supervised runtime instead of a stale nominal-status claim.",
        {"expected_dynamic_label": current_label},
    ))
    return rows

def _stabilization_rows() -> list[IntegrityRow]:
    from stabilization_checkpoint import build_stabilization_dashboard_summary

    report = build_stabilization_dashboard_summary()
    failed = [item for item in report.get("items", []) if item.get("status") == "fail"]
    warnings = [item for item in report.get("items", []) if item.get("status") == "warn"]
    return [
        _row(
            "stabilization-checkpoint",
            not failed,
            "The bounded stabilization summary has no blocking failures; full diagnostics run in release verification.",
            {"status": report.get("status"), "failed": failed, "warning_count": len(warnings)},
        ),
        _row(
            "optional-environment-readiness",
            not warnings,
            "Optional environment and data-file checks are fully satisfied." if not warnings else "Core readiness passes; optional environment or empty-state data warnings remain.",
            warnings,
            required=False,
        ),
    ]


def _safety_rows(
    root: Path,
    source_snapshot_before: dict[str, str],
    initial_action_evidence: dict[str, Any],
) -> tuple[list[IntegrityRow], dict[str, Any]]:
    settings_path = root / "data" / "settings.json"
    settings = _load_json(settings_path) if settings_path.is_file() else {
        "approval_required_for_file_edits": True,
        "approval_required_for_rollbacks": True,
        "safe_mode": "strict",
    }
    if not isinstance(settings, dict):
        settings = {}

    approvals: list[dict[str, Any]] = []
    approval_errors: list[str] = []
    approvals_dir = root / "data" / "approvals"
    if approvals_dir.is_dir():
        for path in sorted(approvals_dir.glob("*.json")):
            try:
                payload = _load_json(path)
                if isinstance(payload, dict):
                    approvals.append(payload)
                else:
                    approval_errors.append(f"{path.name}: non-object JSON")
            except Exception as exc:
                approval_errors.append(f"{path.name}: {type(exc).__name__}: {exc}")

    from approval_manager import VALID_ACTION_TYPES
    release_capable_action_types = sorted(
        action_type
        for action_type in VALID_ACTION_TYPES
        if any(token in action_type for token in ("release", "publish", "autonomy", "self_authorize"))
    )
    active_release_authority_records = [
        {
            "id": item.get("id"),
            "status": item.get("status"),
            "action_type": item.get("action_type"),
        }
        for item in approvals
        if item.get("status") == "pending"
        and any(token in str(item.get("action_type") or "") for token in ("release", "publish", "autonomy", "self_authorize"))
    ]
    pending_mutation_approvals = sum(
        1
        for item in approvals
        if item.get("status") == "pending"
        and item.get("action_type") in {"apply_patch", "rollback_patch", "run_command", "apply_task_evaluation"}
    )

    from sandbox_backend_adapter import build_sandbox_backend_adapter_metadata
    sandbox = build_sandbox_backend_adapter_metadata(project_id="eidolon-release-integrity")
    sandbox_boundary_ok = (
        sandbox.get("audited_backend_count") == 0
        and sandbox.get("audited_os_sandbox_backend_integrated") is False
        and sandbox.get("actual_fixture_execution_allowed") is False
        and sandbox.get("actual_fixture_execution_attempted") is False
        and int(sandbox.get("actual_fixture_execution_count") or 0) == 0
        and int(sandbox.get("subprocess_spawn_count") or 0) == 0
        and sandbox.get("generated_wiring_activated") is False
        and sandbox.get("release_authorized") is False
        and sandbox.get("autonomy_expanded") is False
    )

    approval_boundary_ok = (
        settings.get("safe_mode") == "strict"
        and settings.get("approval_required_for_file_edits") is True
        and settings.get("approval_required_for_rollbacks") is True
        and not approval_errors
        and not release_capable_action_types
        and not active_release_authority_records
    )
    action_log_valid = initial_action_evidence.get("action_log_valid") is True
    persisted_unsafe_flags = list(initial_action_evidence.get("unsafe_true_flags") or [])
    persisted_evidence_ok = action_log_valid and not persisted_unsafe_flags

    source_snapshot_after = _source_snapshot(root)
    mutation_delta = _snapshot_delta(source_snapshot_before, source_snapshot_after)
    mutation_free = mutation_delta["source_write_count"] == 0 and mutation_delta["source_delete_count"] == 0

    release_authorized = bool(release_capable_action_types or active_release_authority_records or persisted_unsafe_flags)
    autonomy_expanded = any(item.get("path", "").endswith("autonomy_expanded") for item in persisted_unsafe_flags)
    evidence = {
        "settings": {
            "safe_mode": settings.get("safe_mode"),
            "approval_required_for_file_edits": settings.get("approval_required_for_file_edits"),
            "approval_required_for_rollbacks": settings.get("approval_required_for_rollbacks"),
        },
        "approval_runtime": {
            "valid_action_types": sorted(VALID_ACTION_TYPES),
            "release_capable_action_types": release_capable_action_types,
            "approval_record_count": len(approvals),
            "pending_mutation_approval_count": pending_mutation_approvals,
            "active_release_authority_records": active_release_authority_records,
            "read_errors": approval_errors,
        },
        "persisted_action_evidence": {
            **initial_action_evidence,
            "unsafe_true_flags": persisted_unsafe_flags,
        },
        "sandbox_runtime": {
            "adapter_status": sandbox.get("adapter_status"),
            "detected_backend_count": sandbox.get("detected_backend_count"),
            "audited_backend_count": sandbox.get("audited_backend_count"),
            "actual_fixture_execution_allowed": sandbox.get("actual_fixture_execution_allowed"),
            "actual_fixture_execution_attempted": sandbox.get("actual_fixture_execution_attempted"),
            "actual_fixture_execution_count": sandbox.get("actual_fixture_execution_count"),
            "subprocess_spawn_count": sandbox.get("subprocess_spawn_count"),
            "generated_wiring_activated": sandbox.get("generated_wiring_activated"),
        },
        "source_mutation_snapshot": mutation_delta,
        "release_authorized": release_authorized,
        "autonomy_expanded": autonomy_expanded,
        "generated_wiring_activated": bool(sandbox.get("generated_wiring_activated")),
        "actual_fixture_execution_count": int(sandbox.get("actual_fixture_execution_count") or 0),
        "source_write_count": mutation_delta["source_write_count"],
        "source_delete_count": mutation_delta["source_delete_count"],
    }
    rows = [
        _row(
            "runtime-approval-authority-boundary",
            approval_boundary_ok,
            "Runtime settings require explicit approval and expose no release/autonomy authorization action type.",
            evidence["approval_runtime"] | {"settings": evidence["settings"]},
        ),
        _row(
            "runtime-sandbox-execution-boundary",
            sandbox_boundary_ok,
            "The live sandbox adapter admits no audited backend, fixture execution, generated wiring, release authorization, or autonomy expansion.",
            evidence["sandbox_runtime"],
        ),
        _row(
            "persisted-authority-and-mutation-evidence",
            persisted_evidence_ok,
            "Persisted action evidence contains no true release, autonomy, generated-wiring, or fixture-execution authority flags.",
            evidence["persisted_action_evidence"],
        ),
        _row(
            "integrity-report-source-mutation-snapshot",
            mutation_free,
            "Before/after hashes prove this integrity report did not add, change, or delete release-owned source files.",
            mutation_delta,
        ),
    ]
    return rows, evidence


def build_registry_navigation_smoke_consolidation_report(
    root: str | Path,
    *,
    evidence: dict[str, Any] | None = None,
    evidence_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    source_snapshot_before = _source_snapshot(root)
    initial_action_evidence = _initial_action_log_evidence(root)
    rows: list[IntegrityRow] = [_python_syntax_row(root, evidence)]
    for builder in (_metadata_rows, _runtime_rows, _dashboard_rows, _smoke_rows):
        try:
            rows.extend(builder(root))
        except Exception as exc:
            rows.append(IntegrityRow(builder.__name__.strip("_"), "fail", f"Integrity section crashed: {exc}", repr(exc), True))
    try:
        rows.extend(_operator_release_rows(root, evidence=evidence, evidence_metadata=evidence_metadata))
    except Exception as exc:
        rows.append(IntegrityRow("operator_release_rows", "fail", f"Integrity section crashed: {exc}", repr(exc), True))
    try:
        rows.extend(_stabilization_rows())
    except Exception as exc:
        rows.append(IntegrityRow("stabilization-checkpoint", "fail", f"Stabilization report crashed: {exc}", repr(exc), True))
    safety_rows, safety_evidence = _safety_rows(root, source_snapshot_before, initial_action_evidence)
    rows.extend(safety_rows)

    failed = [row for row in rows if not row.ok]
    warnings = [row for row in rows if row.status == "warn"]
    return {
        "version": MODULE_VERSION,
        "check_id": CHECK_ID,
        "title": TITLE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not failed else "blocked",
        "ok": not failed,
        "rows": [row.as_dict() for row in rows],
        "counts": {
            "pass": sum(row.status == "pass" for row in rows),
            "warn": len(warnings),
            "fail": sum(row.status == "fail" for row in rows),
        },
        "release_authorized": safety_evidence.get("release_authorized", True),
        "autonomy_expanded": safety_evidence.get("autonomy_expanded", True),
        "source_write_count": safety_evidence.get("source_write_count", -1),
        "source_delete_count": safety_evidence.get("source_delete_count", -1),
        "actual_fixture_execution_count": safety_evidence.get("actual_fixture_execution_count", -1),
        "generated_wiring_activated": safety_evidence.get("generated_wiring_activated", True),
        "safety_evidence": safety_evidence,
        "operator_review_required": True,
        "verification_evidence": evidence_metadata or {"provided": evidence is not None, "valid": evidence is not None},
        "expensive_stage_ownership": {
            "corrective_suite": (
                "rejected_attestation"
                if (evidence_metadata or {}).get("provided") is True and (evidence_metadata or {}).get("valid") is not True
                else ("outer_verifier" if evidence_stage_report(evidence, "corrective-suite") is not None else "integrity_report")
            ),
            "version_inventory": (
                "rejected_attestation"
                if (evidence_metadata or {}).get("provided") is True and (evidence_metadata or {}).get("valid") is not True
                else ("outer_verifier" if evidence_stage_report(evidence, "version-inventory") is not None else "integrity_report")
            ),
        },
    }


def registry_navigation_smoke_consolidation_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Eidolon v{report.get('version')} {report.get('title')}",
        f"Status: {report.get('status')}",
        f"Checks: {report.get('counts')}",
    ]
    for row in report.get("rows", []):
        lines.append(f"[{row.get('status', 'unknown').upper()}] {row.get('name')}: {row.get('summary')}")
        if full and row.get("details") not in (None, [], {}):
            lines.append(json.dumps(row.get("details"), indent=2, sort_keys=True, default=str))
    lines.extend([
        "",
        f"Safety: release_authorized={report.get('release_authorized')} autonomy_expanded={report.get('autonomy_expanded')} source_write_count={report.get('source_write_count')} actual_fixture_execution_count={report.get('actual_fixture_execution_count')}",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Eidolon's authoritative release-integrity report.")
    parser.add_argument("--root", default=str(PROJECT_ROOT), help="Project root to inspect.")
    parser.add_argument("--full", action="store_true", help="Include detailed evidence for every row.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit the complete report as JSON.")
    parser.add_argument("--evidence-file", help="Consume validated stage evidence produced by the outer verifier.")
    args = parser.parse_args(argv)

    evidence, evidence_metadata = load_evidence_bundle(args.evidence_file, expected_root=args.root)
    report = build_registry_navigation_smoke_consolidation_report(
        args.root,
        evidence=evidence,
        evidence_metadata=evidence_metadata,
    )
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(registry_navigation_smoke_consolidation_text(report, full=args.full))
    return 0 if report.get("ok") is True else 1


if __name__ == "__main__":
    exit_code = main()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        os._exit(exit_code)
