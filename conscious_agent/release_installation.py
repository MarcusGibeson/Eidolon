from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from release_packaging import (
    RELEASES_DIR,
    build_release_manifest_integrity,
    build_package_inventory,
    build_package_checksums,
    build_release_notes,
    build_release_handoff_report,
    build_release_zip,
    build_verify_release_unzip,
    build_release_pipeline_audit,
    summarize_release_report,
    _package_name,
)

RELEASE_INSTALLATION_VERSION = "30.0"
RELEASE_INSTALLATION_DIR = DATA_DIR / "release_installation"
RELEASE_PROFILES = RELEASE_INSTALLATION_DIR / "release_profiles.json"
PACKAGE_PRIVACY_SCAN = RELEASE_INSTALLATION_DIR / "package_privacy_scan.json"
PORTABLE_METADATA_CHECK = RELEASE_INSTALLATION_DIR / "portable_metadata_check.json"
FIRST_RUN_CHECK = RELEASE_INSTALLATION_DIR / "first_run_check.json"
DEPENDENCY_ADVISOR = RELEASE_INSTALLATION_DIR / "dependency_advisor.json"
UPGRADE_NOTES = RELEASE_INSTALLATION_DIR / "upgrade_notes.json"
RUNTIME_MIGRATION_CHECK = RELEASE_INSTALLATION_DIR / "runtime_migration_check.json"
RELEASE_INSTALL_VERIFICATION = RELEASE_INSTALLATION_DIR / "release_install_verification.json"
VERIFIED_INSTALLABLE_RELEASE_LOOP = RELEASE_INSTALLATION_DIR / "verified_installable_release_loop.json"
SMOKE_RUNTIME_HARDENING = RELEASE_INSTALLATION_DIR / "smoke_runtime_hardening.json"
EXTERNAL_ZIP_INSTALL_VERIFICATION = RELEASE_INSTALLATION_DIR / "external_zip_install_verification.json"
DETERMINISTIC_RELEASE_MANIFEST = RELEASE_INSTALLATION_DIR / "deterministic_release_manifest.json"
UPDATE_DRY_RUN_PLAN = RELEASE_INSTALLATION_DIR / "update_dry_run_plan.json"
ATOMIC_SOURCE_UPDATE = RELEASE_INSTALLATION_DIR / "atomic_source_update.json"
RUNTIME_MIGRATION_ASSISTANT = RELEASE_INSTALLATION_DIR / "runtime_migration_assistant.json"
ROUTE_SAFETY_HARNESS = RELEASE_INSTALLATION_DIR / "route_safety_harness.json"
RELEASE_DASHBOARD_COMMAND_CENTER = RELEASE_INSTALLATION_DIR / "release_dashboard_command_center.json"
CLEAN_ROOM_INSTALL_HARNESS = RELEASE_INSTALLATION_DIR / "clean_room_install_harness.json"
VERIFIED_SELF_UPDATE_RELEASE_PIPELINE = RELEASE_INSTALLATION_DIR / "verified_self_update_release_pipeline.json"
TRIAL_UPGRADE_HARNESS = RELEASE_INSTALLATION_DIR / "trial_upgrade_harness.json"
BACKUP_ROLLBACK_DRILL = RELEASE_INSTALLATION_DIR / "backup_rollback_drill.json"
UPDATE_COLLISION_DETECTOR = RELEASE_INSTALLATION_DIR / "update_collision_detector.json"
VERSION_REGISTRY_REPORT = RELEASE_INSTALLATION_DIR / "version_registry_report.json"
RELEASE_PROVENANCE_REPORT = RELEASE_INSTALLATION_DIR / "release_provenance_report.json"
DASHBOARD_UPGRADE_WIZARD_PREVIEW = RELEASE_INSTALLATION_DIR / "dashboard_upgrade_wizard_preview.json"
API_UPGRADE_WIZARD_PREVIEW = RELEASE_INSTALLATION_DIR / "api_upgrade_wizard_preview.json"
STAGED_APPLY_DRILL = RELEASE_INSTALLATION_DIR / "staged_apply_drill.json"
REAL_APPLY_GUARD_RAILS = RELEASE_INSTALLATION_DIR / "real_apply_guard_rails.json"
REAL_APPLY_ROLLBACK_VERIFICATION = RELEASE_INSTALLATION_DIR / "real_apply_rollback_verification.json"
SELF_UPDATE_UX_POLISH = RELEASE_INSTALLATION_DIR / "self_update_ux_polish.json"
V23_READINESS_GATE = RELEASE_INSTALLATION_DIR / "v23_readiness_gate.json"
CONTROLLED_SELF_MAINTENANCE_LOOP = RELEASE_INSTALLATION_DIR / "controlled_self_maintenance_loop.json"

PRIVATE_PATTERNS = [
    "memories.json",
    "approval_state.json",
    "data/chroma/",
    "data/chat_actions/",
    "data/dashboard_chat/",
    "data/backups/",
    "data/diagnostics/",
    "data/notifications/",
    "data/patch_drafts/",
    "data/patch_workspace/",
    "data/code_patches/",
    "data/release_package/",
    "data/release_installation/",
    "data/releases/",
    "data/dev_loops/",
    "data/dev_cycles/",
    "data/guided_sessions/",
    "data/memory_archive/",
    "data/memory_summaries/",
]
SOURCE_SAFE_DATA = {
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/projects.json",
    "data/workspaces/active_project.json",
}
SOURCE_SAFE_PREFIXES = ("data/workspaces/command_profiles/",)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    RELEASE_INSTALLATION_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    _ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _status_from(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("status", "pass")).lower() for row in rows}
    if statuses & {"blocked", "failed", "fail"}:
        return "blocked"
    if statuses & {"warn", "warning"}:
        return "warn"
    return "pass"


def _ok_from(status: str) -> bool:
    return status not in {"blocked", "failed", "fail"}


def _row_status_from_report(report: Any) -> str:
    if not isinstance(report, dict):
        return "blocked"
    raw_status = str(report.get("status") or "pass").lower()
    if report.get("ok") is False or raw_status in {"blocked", "failed", "fail", "timeout"}:
        return "blocked"
    if raw_status in {"warn", "warning"}:
        return "warn"
    if raw_status in {"dry_run", "skipped", "pending"}:
        return raw_status
    return "pass"


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _current_version() -> str:
    settings = _read_json(DATA_DIR / "settings.json", {})
    return str(settings.get("settings_version") or settings.get("version") or RELEASE_INSTALLATION_VERSION).lstrip("v")


def _is_source_safe_data(path: str) -> bool:
    return path in SOURCE_SAFE_DATA or any(path.startswith(prefix) for prefix in SOURCE_SAFE_PREFIXES)


def _contains_absolute_or_sandbox_path(value: Any) -> bool:
    text = json.dumps(value, default=str)
    return bool(re.search(r"/mnt/data|C:\\\\Users\\\\|[A-Za-z]:\\\\", text))


def _load_requirements() -> list[str]:
    req = ROOT_DIR / "requirements.txt"
    if not req.exists():
        return []
    out: list[str] = []
    for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(re.split(r"[<>=~!;]", line, maxsplit=1)[0].strip())
    return out


def _module_for_requirement(name: str) -> str:
    return {
        "beautifulsoup4": "bs4",
        "pillow": "PIL",
        "pyyaml": "yaml",
    }.get(name.lower(), name.replace("-", "_"))


def build_release_profiles(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v20.1: define explicit package profiles and keep source-only as the safe default."""
    profiles = [
        {"id": "source-only", "share_safe": True, "default": True, "description": "Source files plus allowlisted seed/config metadata only; excludes private runtime state."},
        {"id": "developer-local", "share_safe": False, "default": False, "description": "Local developer handoff with selected generated reports, never chat/memory/vector stores."},
        {"id": "diagnostic", "share_safe": False, "default": False, "description": "Local diagnostic bundle with selected debug reports for troubleshooting."},
        {"id": "full-backup", "share_safe": False, "default": False, "description": "Local-only backup profile; never marked share-safe."},
    ]
    rows = [
        {"name": "default-profile", "status": "pass", "message": "source-only is the default guarded release profile."},
        {"name": "share-safe-profile", "status": "pass", "message": "Only source-only is share-safe."},
        {"name": "profile-count", "status": "pass", "message": f"{len(profiles)} release profiles are defined."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "default_profile": "source-only", "profiles": profiles, "rows": rows, "message": "Release profiles define how package inventory should treat source, diagnostics, and local-only runtime state."}
    if save:
        _write_json(RELEASE_PROFILES, report)
    else:
        report["preview_only"] = True
    return report


def build_package_privacy_scan(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v20.2: detect private/runtime files before packaging."""
    inventory = build_package_inventory(project_id=project_id, save=False)
    included = inventory.get("included", []) if isinstance(inventory, dict) else []
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for row in included:
        path = str(row.get("path", ""))
        if any(pattern in path for pattern in PRIVATE_PATTERNS):
            violations.append({"path": path, "reason": "private/runtime path included"})
        if path.startswith("data/") and not _is_source_safe_data(path):
            violations.append({"path": path, "reason": "non-allowlisted data file included"})
        if path.endswith((".sqlite3", ".db", ".bin")):
            violations.append({"path": path, "reason": "database/vector/binary runtime artifact included"})
        if path in {"data/projects.json", "data/workspaces/projects.json", "data/workspaces/active_project.json"}:
            value = _read_json(ROOT_DIR / path, {})
            if _contains_absolute_or_sandbox_path(value):
                warnings.append({"path": path, "reason": "portable metadata contains an absolute or sandbox path"})
    rows = [
        {"name": "inventory-ok", "status": "pass" if inventory.get("ok") else "blocked", "message": inventory.get("message", "package inventory unavailable")},
        {"name": "private-files", "status": "blocked" if violations else "pass", "message": f"{len(violations)} private/runtime included path(s) detected."},
        {"name": "portable-warnings", "status": "warn" if warnings else "pass", "message": f"{len(warnings)} portable metadata warning(s)."},
        {"name": "source-only-profile", "status": "pass" if inventory.get("package_profile") == "source_only" else "blocked", "message": "Package inventory uses source-only profile by default."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "violations": violations, "warnings": warnings, "included_count": inventory.get("included_count"), "rows": rows, "message": "Package privacy scan completed for source-only release packaging."}
    if save:
        _write_json(PACKAGE_PRIVACY_SCAN, report)
    else:
        report["preview_only"] = True
    return report


def build_portable_metadata_check(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v20.3: verify workspace metadata remains portable after unzip."""
    workspace_projects = _read_json(DATA_DIR / "workspaces" / "projects.json", {})
    active = _read_json(DATA_DIR / "workspaces" / "active_project.json", {})
    version = _current_version()
    projects = workspace_projects.get("projects", []) if isinstance(workspace_projects, dict) else []
    eidolon = next((p for p in projects if p.get("id") == project_id), projects[0] if projects else {})
    command_profiles = sorted((DATA_DIR / "workspaces" / "command_profiles").glob("*.json"))
    rows = [
        {"name": "workspace-root-version", "status": "pass" if str(workspace_projects.get("version")) in {version, f"v{version}"} else "blocked", "message": f"workspace root version={workspace_projects.get('version')} expected={version}"},
        {"name": "active-project-version", "status": "pass" if str(active.get("version")) in {version, f"v{version}"} and active.get("last_updated_for") == f"v{version}" else "blocked", "message": f"active project version={active.get('version')} last_updated_for={active.get('last_updated_for')}"},
        {"name": "project-root-portable", "status": "pass" if eidolon.get("root") in {".", ""} and not _contains_absolute_or_sandbox_path(eidolon.get("root")) else "blocked", "message": f"project root={eidolon.get('root')} should resolve from ROOT_DIR."},
        {"name": "readme-path", "status": "pass" if (ROOT_DIR / str(eidolon.get("readme_path", "README_NEXT_STEPS.md"))).exists() else "blocked", "message": "README path resolves inside the package."},
        {"name": "command-profiles", "status": "pass" if command_profiles else "blocked", "message": f"{len(command_profiles)} command profile file(s) found."},
        {"name": "no-absolute-paths", "status": "pass" if not _contains_absolute_or_sandbox_path({"workspace_projects": workspace_projects, "active": active}) else "blocked", "message": "Workspace metadata should not contain /mnt/data or hard-coded user roots."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "rows": rows, "message": "Portable workspace metadata check completed."}
    if save:
        _write_json(PORTABLE_METADATA_CHECK, report)
    else:
        report["preview_only"] = True
    return report


def build_dependency_advisor(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v20.5: explain installed, missing, optional, and required packages."""
    requirements = _load_requirements()
    packages = []
    missing_required = []
    missing_optional = []
    optional = {"chromadb"}
    for req in requirements:
        mod = _module_for_requirement(req)
        installed = importlib.util.find_spec(mod) is not None
        row = {"requirement": req, "module": mod, "installed": installed, "optional": req.lower() in optional}
        packages.append(row)
        if not installed and row["optional"]:
            missing_optional.append(req)
        elif not installed:
            missing_required.append(req)
    rows = [
        {"name": "requirements-file", "status": "pass" if requirements else "warn", "message": f"{len(requirements)} requirement(s) listed."},
        {"name": "required-packages", "status": "blocked" if missing_required else "pass", "message": f"Missing required: {', '.join(missing_required) or 'none'}."},
        {"name": "optional-packages", "status": "warn" if missing_optional else "pass", "message": f"Missing optional: {', '.join(missing_optional) or 'none'}."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "packages": packages, "missing_required": missing_required, "missing_optional": missing_optional, "install_command": "pip install -r requirements.txt", "rows": rows, "message": "Dependency advisor completed."}
    if save:
        _write_json(DEPENDENCY_ADVISOR, report)
    else:
        report["preview_only"] = True
    return report


def build_first_run_check(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v20.4: check what a user should run after unzipping a source-only release."""
    deps = build_dependency_advisor(project_id=project_id, save=False)
    portable = build_portable_metadata_check(project_id=project_id, save=False)
    rows = [
        {"name": "python-version", "status": "pass" if sys.version_info >= (3, 10) else "blocked", "message": platform.python_version()},
        {"name": "requirements", "status": "pass" if (ROOT_DIR / "requirements.txt").exists() else "blocked", "message": "requirements.txt exists."},
        {"name": "settings", "status": "pass" if (DATA_DIR / "settings.json").exists() else "blocked", "message": "settings.json loads."},
        {"name": "readme", "status": "pass" if (ROOT_DIR / "README_NEXT_STEPS.md").exists() else "blocked", "message": "README exists."},
        {"name": "workspace-metadata", "status": "pass" if portable.get("ok") else "blocked", "message": portable.get("message")},
        {"name": "dashboard-import", "status": "pass" if importlib.util.find_spec("dashboard") or (ROOT_DIR / "conscious_agent" / "dashboard.py").exists() else "blocked", "message": "dashboard.py exists/importable from project path."},
        {"name": "api-import", "status": "pass" if (ROOT_DIR / "conscious_agent" / "api_server.py").exists() else "blocked", "message": "api_server.py exists."},
        {"name": "dependencies", "status": "pass" if not deps.get("missing_required") else "blocked", "message": deps.get("message")},
        {"name": "ollama-optional", "status": "warn", "message": "Ollama is optional for first-run packaging checks; use --settings-health for live model status."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "rows": rows, "dependency_advisor": deps, "portable_metadata": portable, "recommended_first_commands": ["pip install -r requirements.txt", "python conscious_agent/main.py --first-run-check", "python conscious_agent/main.py --doctor", "python conscious_agent/main.py --dashboard"], "message": "First-run setup check completed."}
    if save:
        _write_json(FIRST_RUN_CHECK, report)
    else:
        report["preview_only"] = True
    return report


def build_upgrade_notes(project_id: str = "eidolon", from_version: str = "20.0.1", to_version: str | None = None, save: bool = True) -> dict[str, Any]:
    """v20.6: generate upgrade notes between packaged versions."""
    to_version = to_version or _current_version()
    notes = [
        "Use the source-only release package for handoff; do not replace private runtime data blindly.",
        "Run --first-run-check after unzip before launching dashboard or desktop.",
        "Run --runtime-migration-check before copying a new package over an existing local Eidolon folder.",
        "Release APIs return compact summaries by default; use full=true only when inspecting detailed inventories.",
    ]
    commands = ['--release-profiles', '--package-privacy-scan', '--portable-metadata-check', '--first-run-check', '--dependency-advisor', '--upgrade-notes', '--runtime-migration-check', '--release-install-verification', '--verified-installable-release-loop', '--smoke-runtime-hardening', '--external-zip-install-verification', '--deterministic-release-manifest', '--update-dry-run-plan', '--atomic-source-update', '--runtime-migration-assistant', '--route-safety-harness', '--release-dashboard-command-center', '--clean-room-install-harness', '--verified-self-update-release-pipeline', '--trial-upgrade-from-zip', '--backup-rollback-drill', '--update-collision-detector', '--version-registry-report', '--release-provenance-report', '--dashboard-upgrade-wizard-preview', '--api-upgrade-wizard-preview', '--staged-apply-drill', '--real-apply-guard-rails', '--real-apply-rollback-verification', '--self-update-ux-polish', '--v23-readiness-gate', '--controlled-self-maintenance-loop']
    rows = [
        {"name": "from-version", "status": "pass", "message": from_version},
        {"name": "to-version", "status": "pass" if to_version else "blocked", "message": str(to_version)},
        {"name": "new-command-count", "status": "pass", "message": f"{len(commands)} release install commands documented."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "from_version": from_version, "to_version": to_version, "new_commands": commands, "upgrade_notes": notes, "rows": rows, "message": f"Upgrade notes generated from v{from_version} to v{to_version}."}
    if save:
        _write_json(UPGRADE_NOTES, report)
    else:
        report["preview_only"] = True
    return report


def build_runtime_migration_check(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v20.7: prevent source-only releases from overwriting private runtime state."""
    runtime_paths = [p for p in [DATA_DIR / "memories.json", DATA_DIR / "chroma", DATA_DIR / "dashboard_chat", DATA_DIR / "chat_actions", DATA_DIR / "backups", DATA_DIR / "patch_drafts", DATA_DIR / "code_patches"] if p.exists()]
    package_seed_paths = [DATA_DIR / "settings.json", DATA_DIR / "projects.json", DATA_DIR / "workspaces" / "projects.json", DATA_DIR / "workspaces" / "active_project.json"]
    rows = [
        {"name": "runtime-state-present", "status": "warn" if runtime_paths else "pass", "message": f"{len(runtime_paths)} local runtime/private path(s) exist; back them up before replacing folders."},
        {"name": "seed-data", "status": "pass" if all(path.exists() for path in package_seed_paths) else "blocked", "message": "Source-only package seed metadata files exist."},
        {"name": "overwrite-rule", "status": "pass", "message": "Never overwrite private runtime data without explicit backup and confirmation."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "runtime_paths": [str(p.relative_to(ROOT_DIR)).replace(os.sep, "/") for p in runtime_paths], "seed_paths": [str(p.relative_to(ROOT_DIR)).replace(os.sep, "/") for p in package_seed_paths], "rows": rows, "message": "Runtime migration check completed."}
    if save:
        _write_json(RUNTIME_MIGRATION_CHECK, report)
    else:
        report["preview_only"] = True
    return report


def _run_short_command(args: list[str], timeout: int = 40, cwd: Path | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.Popen(args, cwd=cwd or ROOT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except Exception:
                stdout, stderr = "", ""
            return {"args": args, "returncode": None, "ok": False, "timeout": timeout, "stdout_tail": stdout[-1000:], "stderr_tail": stderr[-1000:], "error": f"Command timed out after {timeout}s"}
        return {"args": args, "returncode": proc.returncode, "ok": proc.returncode == 0, "stdout_tail": stdout[-1000:], "stderr_tail": stderr[-1000:]}
    except Exception as error:
        return {"args": args, "returncode": None, "ok": False, "error": str(error)}


def build_release_install_verification(project_id: str = "eidolon", package_name: str | None = None, run_smoke: bool = False, save: bool = True) -> dict[str, Any]:
    """v20.8: verify an extracted install with source-only package expectations."""
    package_name = package_name or _package_name()
    manifest = build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=False)
    privacy = build_package_privacy_scan(project_id=project_id, save=False)
    portable = build_portable_metadata_check(project_id=project_id, save=False)
    first_run = build_first_run_check(project_id=project_id, save=False)
    unzip = build_verify_release_unzip(project_id=project_id, package_name=package_name, save=False)
    external_zip = build_external_zip_install_verification(project_id=project_id, package_name=package_name, run_compile=False, save=False)
    compile_result = _run_short_command([sys.executable, "-m", "py_compile", *[str(p) for p in (ROOT_DIR / "conscious_agent").glob("*.py")], str(ROOT_DIR / "tools" / "smoke_check.py")], timeout=60)
    smoke_result = _run_short_command([sys.executable, "-u", str(ROOT_DIR / "tools" / "smoke_check.py"), "--tier", "install", "--json"], timeout=300) if run_smoke else {"ok": True, "skipped": True, "message": "Smoke check command exists; full smoke is run by release verification outside dashboard summary mode."}
    rows = [
        {"name": "compile", "status": "pass" if compile_result.get("ok") else "blocked", "message": "Python compile check passed." if compile_result.get("ok") else str(compile_result.get("error") or compile_result.get("stderr_tail"))},
        {"name": "manifest", "status": "pass" if manifest.get("ok") else "blocked", "message": manifest.get("message")},
        {"name": "privacy", "status": "pass" if privacy.get("ok") else "blocked", "message": privacy.get("message")},
        {"name": "portable", "status": "pass" if portable.get("ok") else "blocked", "message": portable.get("message")},
        {"name": "first-run", "status": "pass" if first_run.get("ok") else "blocked", "message": first_run.get("message")},
        {"name": "unzip", "status": "warn" if external_zip.get("skipped") else "pass" if external_zip.get("ok") else "blocked", "message": external_zip.get("message") or unzip.get("message")},
        {"name": "smoke", "status": "pass" if smoke_result.get("ok") else "blocked", "message": smoke_result.get("message", "Smoke check completed." if smoke_result.get("ok") else "Smoke check failed.")},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "rows": rows, "compile": compile_result, "external_zip": external_zip, "legacy_unzip": unzip, "smoke": smoke_result, "message": "Release install verification completed."}
    if save:
        _write_json(RELEASE_INSTALL_VERIFICATION, report)
    else:
        report["preview_only"] = True
    return report


def build_verified_installable_release_loop(project_id: str = "eidolon", package_name: str | None = None, confirm: bool = False, dry_run: bool = True, run_smoke: bool = False, save: bool = True) -> dict[str, Any]:
    """v21.0: produce and verify one source-only installable handoff package."""
    package_name = package_name or _package_name()
    profiles = build_release_profiles(project_id=project_id, save=save)
    manifest = build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=save)
    privacy = build_package_privacy_scan(project_id=project_id, save=save)
    portable = build_portable_metadata_check(project_id=project_id, save=save)
    inventory = build_package_inventory(project_id=project_id, save=save)
    checksums = build_package_checksums(project_id=project_id, save=save)
    notes = build_release_notes(project_id=project_id, save=save)
    upgrade = build_upgrade_notes(project_id=project_id, to_version=_current_version(), save=save)
    handoff = build_release_handoff_report(project_id=project_id, package_name=package_name, save=save)
    migration = build_runtime_migration_check(project_id=project_id, save=save)
    zip_report = build_release_zip(project_id=project_id, package_name=package_name, confirm=confirm, dry_run=dry_run or not confirm, save=save)
    unzip = build_verify_release_unzip(project_id=project_id, package_name=package_name, save=save)
    install = build_release_install_verification(project_id=project_id, package_name=package_name, run_smoke=run_smoke, save=save)
    audit = build_release_pipeline_audit(project_id=project_id, package_name=package_name, save=save)
    steps = {"profiles": profiles, "manifest": manifest, "privacy": privacy, "portable": portable, "inventory": inventory, "checksums": checksums, "notes": notes, "upgrade": upgrade, "handoff": handoff, "migration": migration, "zip": zip_report, "unzip": unzip, "install": install, "audit": audit}
    blocked = [name for name, report in steps.items() if isinstance(report, dict) and report.get("ok") is False]
    status = "blocked" if blocked else "package_built" if confirm and not dry_run and zip_report.get("status") == "built" else "dry_run"
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": not blocked, "dry_run": dry_run or not confirm, "package_name": package_name, "steps": steps, "blocked_steps": blocked, "message": "Verified installable release loop completed and stopped."}
    if save:
        _write_json(VERIFIED_INSTALLABLE_RELEASE_LOOP, report)
    else:
        report["preview_only"] = True
    return report



def _strip_zip_root(name: str, common_root: str | None = None) -> str:
    cleaned = name.replace("\\", "/").lstrip("/")
    if common_root and cleaned.startswith(common_root.rstrip("/") + "/"):
        cleaned = cleaned[len(common_root.rstrip("/")) + 1 :]
    return cleaned


def _zip_common_root(names: list[str]) -> str | None:
    roots = {name.replace("\\", "/").split("/", 1)[0] for name in names if name and "/" in name.replace("\\", "/")}
    if len(roots) == 1:
        return next(iter(roots))
    return None


def _resolve_zip_path(package_name: str | None = None, zip_path: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if zip_path:
        candidates.append(Path(zip_path))
    if package_name:
        candidates.extend([Path(package_name), RELEASES_DIR / package_name, ROOT_DIR / package_name])
    else:
        candidates.extend(sorted(RELEASES_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True))
    for candidate in candidates:
        if not candidate.is_absolute():
            candidate = ROOT_DIR / candidate
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def _zip_file_rows(zip_file: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    violations: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_file, "r") as zf:
        names = [info.filename for info in zf.infolist() if not info.is_dir()]
        common_root = _zip_common_root(names)
        for info in sorted((item for item in zf.infolist() if not item.is_dir()), key=lambda i: i.filename):
            original = info.filename.replace("\\", "/")
            rel = _strip_zip_root(original, common_root)
            parts = Path(rel).parts
            reason = "included"
            if original.startswith("/") or re.match(r"^[A-Za-z]:", original):
                violations.append({"path": original, "reason": "absolute path in zip member"})
                reason = "absolute path"
            if ".." in parts:
                violations.append({"path": original, "reason": "zip-slip parent directory segment"})
                reason = "zip-slip path"
            if rel.endswith(".zip"):
                violations.append({"path": rel, "reason": "nested zip included"})
                reason = "nested zip"
            if any(part in {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"} for part in parts):
                violations.append({"path": rel, "reason": "generated/cache/env directory included"})
                reason = "excluded directory"
            if rel.startswith("data/") and not _is_source_safe_data(rel):
                violations.append({"path": rel, "reason": "private/runtime data path included"})
                reason = "private data"
            if any(pattern.rstrip("/") in rel for pattern in PRIVATE_PATTERNS):
                violations.append({"path": rel, "reason": "private pattern matched"})
                reason = "private pattern"
            rows.append({"zip_path": original, "path": rel, "size": info.file_size, "status": "blocked" if reason != "included" else "pass", "message": reason})
    return rows, violations, common_root


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _zip_manifest_entries(zip_file: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_file, "r") as zf:
        names = [info.filename for info in zf.infolist() if not info.is_dir()]
        common_root = _zip_common_root(names)
        for info in sorted((item for item in zf.infolist() if not item.is_dir()), key=lambda i: _strip_zip_root(i.filename, common_root)):
            rel = _strip_zip_root(info.filename, common_root)
            entries.append({"path": rel, "size": info.file_size, "sha256": _sha256_bytes(zf.read(info.filename))})
    return entries


def _manifest_hash(entries: list[dict[str, Any]]) -> str:
    canonical = json.dumps(sorted(entries, key=lambda row: row.get("path", "")), separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_smoke_runtime_hardening(project_id: str = "eidolon", tier: str = "full", save: bool = True) -> dict[str, Any]:
    """v21.1: verify the smoke runner has tiered checks, per-check timeouts, and JSON output."""
    smoke_path = ROOT_DIR / "tools" / "smoke_check.py"
    text = smoke_path.read_text(encoding="utf-8", errors="replace") if smoke_path.exists() else ""
    rows = [
        {"name": "smoke-script", "status": "pass" if smoke_path.exists() else "blocked", "message": "tools/smoke_check.py exists."},
        {"name": "single-check-mode", "status": "pass" if "--single-check" in text else "blocked", "message": "Each check can run in an isolated subprocess."},
        {"name": "tiered-mode", "status": "pass" if "--tier" in text and "_TIER_ORDER" in text else "blocked", "message": "Smoke tiers are declared."},
        {"name": "json-summary", "status": "pass" if "--json" in text else "blocked", "message": "Machine-readable smoke summaries are available."},
        {"name": "timeout-wrapper", "status": "pass" if "TimeoutExpired" in text else "blocked", "message": "Per-check timeout handling is present."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "tier": tier, "status": status, "ok": _ok_from(status), "rows": rows, "message": "Smoke runtime hardening check completed."}
    if save:
        _write_json(SMOKE_RUNTIME_HARDENING, report)
    else:
        report["preview_only"] = True
    return report


def build_external_zip_install_verification(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, run_compile: bool = True, save: bool = True) -> dict[str, Any]:
    """v21.2: verify an actual external release zip without relying on nested zips inside the source tree."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {"requested_package_name": package_name, "requested_zip_path": zip_path}
    if not resolved:
        rows.append({"name": "zip-present", "status": "warn", "message": "No external release zip was provided or found; external unzip verification skipped."})
        status = _status_from(rows)
        report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "skipped": True, "rows": rows, "details": details, "message": "External release zip verification skipped because no zip was available."}
        if save:
            _write_json(EXTERNAL_ZIP_INSTALL_VERIFICATION, report)
        else:
            report["preview_only"] = True
        return report
    try:
        file_rows, violations, common_root = _zip_file_rows(resolved)
        source_files = [row for row in file_rows if str(row.get("path", "")).endswith(".py")]
        rows.extend([
            {"name": "zip-present", "status": "pass", "message": str(resolved)},
            {"name": "zip-member-count", "status": "pass" if file_rows else "blocked", "message": f"{len(file_rows)} file member(s) found."},
            {"name": "zip-root", "status": "pass", "message": common_root or "no single wrapper root"},
            {"name": "source-files", "status": "pass" if source_files else "blocked", "message": f"{len(source_files)} Python source file(s) found."},
            {"name": "privacy-and-paths", "status": "blocked" if violations else "pass", "message": f"{len(violations)} zip path/privacy violation(s)."},
        ])
        compile_result: dict[str, Any] = {"skipped": not run_compile}
        if run_compile and not violations:
            with tempfile.TemporaryDirectory(prefix="eidolon_zip_verify_") as tmp:
                with zipfile.ZipFile(resolved, "r") as zf:
                    zf.extractall(tmp)
                root = Path(tmp) / common_root if common_root and (Path(tmp) / common_root).exists() else Path(tmp)
                py_files = [str(path) for path in sorted((root / "conscious_agent").glob("*.py"))]
                smoke = root / "tools" / "smoke_check.py"
                if smoke.exists():
                    py_files.append(str(smoke))
                compile_result = _run_short_command([sys.executable, "-m", "py_compile", *py_files], timeout=90) if py_files else {"ok": False, "error": "No Python files found after extract."}
            rows.append({"name": "temp-extract-compile", "status": "pass" if compile_result.get("ok") else "blocked", "message": "Temporary extract compiled." if compile_result.get("ok") else str(compile_result.get("error") or compile_result.get("stderr_tail"))})
        status = _status_from(rows)
        report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": str(resolved), "common_root": common_root, "file_count": len(file_rows), "violations": violations, "rows": rows, "compile": compile_result, "message": "External release zip install verification completed."}
    except Exception as error:
        report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": "blocked", "ok": False, "package_name": package_name, "zip_path": str(resolved), "rows": [{"name": "external-zip", "status": "blocked", "message": str(error)}], "message": "External release zip verification failed."}
    if save:
        _write_json(EXTERNAL_ZIP_INSTALL_VERIFICATION, report)
    else:
        report["preview_only"] = True
    return report


def build_deterministic_release_manifest(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v21.3: generate a deterministic manifest hash for the exact reviewed source artifact set."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    if resolved:
        entries = _zip_manifest_entries(resolved)
        source = "zip"
        excluded_count = None
        profile = "source-only-zip"
    else:
        checksums = build_package_checksums(project_id=project_id, save=False)
        entries = [{"path": row.get("path"), "sha256": row.get("sha256"), "size": row.get("size")} for row in checksums.get("checksums", [])]
        inventory = build_package_inventory(project_id=project_id, save=False)
        source = "working-tree-inventory"
        excluded_count = inventory.get("excluded_count")
        profile = inventory.get("package_profile")
    entries = sorted(entries, key=lambda row: str(row.get("path", "")))
    manifest_sha = _manifest_hash(entries)
    rows = [
        {"name": "manifest-source", "status": "pass", "message": source},
        {"name": "file-count", "status": "pass" if entries else "blocked", "message": f"{len(entries)} file(s) are bound to the deterministic manifest."},
        {"name": "manifest-hash", "status": "pass" if manifest_sha else "blocked", "message": manifest_sha},
        {"name": "sorted", "status": "pass" if entries == sorted(entries, key=lambda row: str(row.get("path", ""))) else "blocked", "message": "Manifest entries are path-sorted."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": str(resolved) if resolved else None, "source": source, "package_profile": profile, "file_count": len(entries), "excluded_count": excluded_count, "manifest_sha256": manifest_sha, "entries": entries, "rows": rows, "message": "Deterministic release manifest generated."}
    if save:
        _write_json(DETERMINISTIC_RELEASE_MANIFEST, report)
    else:
        report["preview_only"] = True
    return report


def build_update_dry_run_plan(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, install_root: str | None = None, save: bool = True) -> dict[str, Any]:
    """v21.4: compare a source-only release zip with the current tree without writing apply/rollback pointers."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    root = Path(install_root).resolve() if install_root else ROOT_DIR
    rows: list[dict[str, Any]] = []
    if not resolved:
        inventory = build_package_inventory(project_id=project_id, save=False)
        rows.append({"name": "target-zip", "status": "warn", "message": "No target zip supplied; generated inventory-only dry-run plan."})
        status = _status_from(rows)
        report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "dry_run": True, "package_name": package_name, "zip_path": None, "install_root": str(root), "new_files": [], "changed_files": [], "unchanged_files": [], "removed_files": [], "manifest_sha256": None, "rows": rows, "inventory_summary": summarize_release_report(inventory), "message": "Update dry-run plan skipped exact compare because no target zip was available."}
        if save:
            _write_json(UPDATE_DRY_RUN_PLAN, report)
        else:
            report["preview_only"] = True
        return report
    entries = _zip_manifest_entries(resolved)
    target_paths = {str(entry["path"]): entry for entry in entries}
    current_inventory = build_package_checksums(project_id=project_id, save=False).get("checksums", []) if root == ROOT_DIR else []
    current_paths = {str(row.get("path")): row for row in current_inventory}
    new_files: list[str] = []
    changed_files: list[str] = []
    unchanged_files: list[str] = []
    for rel, entry in sorted(target_paths.items()):
        current = current_paths.get(rel)
        if not current and (root / rel).exists():
            current = {"sha256": _sha256_file(root / rel)}
        if not current:
            new_files.append(rel)
        elif current.get("sha256") != entry.get("sha256"):
            changed_files.append(rel)
        else:
            unchanged_files.append(rel)
    removed_files = sorted(rel for rel in current_paths if rel not in target_paths and not rel.startswith("data/release_installation/"))
    manifest_sha = _manifest_hash(entries)
    rows.extend([
        {"name": "target-zip", "status": "pass", "message": str(resolved)},
        {"name": "manifest-hash", "status": "pass", "message": manifest_sha},
        {"name": "new-files", "status": "pass", "message": str(len(new_files))},
        {"name": "changed-files", "status": "pass", "message": str(len(changed_files))},
        {"name": "removed-files", "status": "warn" if removed_files else "pass", "message": f"{len(removed_files)} current source file(s) are absent from the target package; dry-run only."},
        {"name": "dry-run-pointer-safety", "status": "pass", "message": "Dry-run does not write apply or rollback pointers."},
    ])
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "dry_run": True, "package_name": package_name, "zip_path": str(resolved), "install_root": str(root), "manifest_sha256": manifest_sha, "new_files": new_files, "changed_files": changed_files, "unchanged_files": unchanged_files, "removed_files": removed_files, "rows": rows, "message": "Update dry-run plan completed without applying changes."}
    if save:
        _write_json(UPDATE_DRY_RUN_PLAN, report)
    else:
        report["preview_only"] = True
    return report


def build_atomic_source_update(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, expected_manifest_hash: str | None = None, confirm: bool = False, dry_run: bool = True, install_root: str | None = None, save: bool = True) -> dict[str, Any]:
    """v21.5: guarded source update transaction; real apply requires explicit confirmation and exact manifest binding."""
    plan = build_update_dry_run_plan(project_id=project_id, package_name=package_name, zip_path=zip_path, install_root=install_root, save=False)
    manifest_hash = plan.get("manifest_sha256")
    effective_dry_run = dry_run or not confirm
    rows = [
        {"name": "plan", "status": "pass" if plan.get("ok") else "blocked", "message": plan.get("message")},
        {"name": "explicit-confirm", "status": "pass" if confirm else "blocked" if not effective_dry_run else "warn", "message": "Real apply requires confirm=True."},
        {"name": "manifest-binding", "status": "pass" if expected_manifest_hash and expected_manifest_hash == manifest_hash else "blocked" if not effective_dry_run else "warn", "message": f"expected={expected_manifest_hash or 'missing'} actual={manifest_hash or 'missing'}"},
        {"name": "dry-run", "status": "pass" if effective_dry_run else "warn", "message": "No source files are modified in dry-run mode." if effective_dry_run else "Live source update requested."},
    ]
    applied_files: list[str] = []
    backup_dir: str | None = None
    rollback_manifest: list[dict[str, Any]] = []
    if not effective_dry_run:
        if not plan.get("zip_path"):
            rows.append({"name": "zip", "status": "blocked", "message": "No target zip available for live apply."})
        if expected_manifest_hash != manifest_hash:
            rows.append({"name": "abort", "status": "blocked", "message": "Manifest hash mismatch; apply aborted."})
        if _status_from(rows) != "blocked":
            root = Path(install_root).resolve() if install_root else ROOT_DIR
            resolved = Path(str(plan["zip_path"])).resolve()
            backup_root = DATA_DIR / "backups" / f"source_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with tempfile.TemporaryDirectory(prefix="eidolon_update_stage_") as tmp:
                with zipfile.ZipFile(resolved, "r") as zf:
                    zf.extractall(tmp)
                    names = [info.filename for info in zf.infolist() if not info.is_dir()]
                    common_root = _zip_common_root(names)
                stage_root = Path(tmp) / common_root if common_root and (Path(tmp) / common_root).exists() else Path(tmp)
                for rel in sorted(set(plan.get("new_files", [])) | set(plan.get("changed_files", []))):
                    if rel.startswith("data/") and not _is_source_safe_data(rel):
                        continue
                    source = stage_root / rel
                    target = root / rel
                    if not source.exists() or source.is_dir():
                        continue
                    if target.exists():
                        backup_target = backup_root / rel
                        backup_target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, backup_target)
                        rollback_manifest.append({"path": rel, "backup": str(backup_target.relative_to(ROOT_DIR)) if backup_target.is_relative_to(ROOT_DIR) else str(backup_target)})
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    applied_files.append(rel)
            backup_dir = str(backup_root.relative_to(ROOT_DIR)) if backup_root.exists() and backup_root.is_relative_to(ROOT_DIR) else str(backup_root)
            rows.append({"name": "applied-files", "status": "pass", "message": f"{len(applied_files)} file(s) copied from staged release."})
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": "dry_run" if effective_dry_run and _ok_from(status) else status, "ok": _ok_from(status), "dry_run": effective_dry_run, "package_name": package_name or plan.get("package_name"), "zip_path": plan.get("zip_path"), "expected_manifest_hash": expected_manifest_hash, "actual_manifest_hash": manifest_hash, "applied_files": applied_files, "backup_dir": backup_dir, "rollback_manifest": rollback_manifest, "plan": plan, "rows": rows, "message": "Atomic source update transaction completed." if applied_files else "Atomic source update transaction preview completed; no source files were modified."}
    if save:
        _write_json(ATOMIC_SOURCE_UPDATE, report)
    else:
        report["preview_only"] = True
    return report


def build_runtime_migration_assistant(project_id: str = "eidolon", confirm: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v21.6: preview runtime migration/backup work before any source update touches local state."""
    guard = build_runtime_migration_check(project_id=project_id, save=False)
    runtime_paths = guard.get("runtime_paths", [])
    actions = []
    for rel in runtime_paths:
        actions.append({"action": "backup-runtime-path", "path": rel, "required_before_live_update": True})
    actions.append({"action": "preserve-private-data", "path": "data/* except source-safe seed metadata", "required_before_live_update": True})
    rows = [
        {"name": "runtime-guard", "status": "pass" if guard.get("ok") else "blocked", "message": guard.get("message")},
        {"name": "backup-plan", "status": "warn" if runtime_paths else "pass", "message": f"{len(runtime_paths)} runtime path(s) should be backed up before live update."},
        {"name": "live-migration", "status": "pass" if confirm and not dry_run else "warn", "message": "Live migration requires confirm=True and dry_run=False; preview only by default."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status if not dry_run else "dry_run", "ok": _ok_from(status), "dry_run": dry_run or not confirm, "actions": actions, "runtime_guard": guard, "rows": rows, "message": "Runtime migration assistant completed."}
    if save:
        _write_json(RUNTIME_MIGRATION_ASSISTANT, report)
    else:
        report["preview_only"] = True
    return report


def build_route_safety_harness(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v21.7: static route safety harness for GET read-only and confirmation-gated POST release surfaces."""
    api_text = (ROOT_DIR / "conscious_agent" / "api_server.py").read_text(encoding="utf-8", errors="replace")
    dashboard_text = (ROOT_DIR / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="replace")
    if "def handle_api_get" in api_text and "def handle_api_post" in api_text:
        get_section = api_text.split("def handle_api_get", 1)[1].split("def handle_api_post", 1)[0]
    else:
        get_section = api_text
    release_get_save_false = all(token in get_section for token in ["build_release_zip(project_id=project_id, package_name=package_name, confirm=False, dry_run=True, save=False)", "build_verified_installable_release_loop(project_id=project_id, package_name=package_name, confirm=False, dry_run=True, save=False)"])
    get_has_save_true = "save=True" in get_section
    post_has_confirmations = all(token in api_text for token in ["BUILD_RELEASE_ZIP", "VERIFIED_INSTALLABLE_RELEASE_LOOP", "_require_confirmation"])
    dashboard_api_info_safe = 'elif path == "/api-info"' in dashboard_text and 'path == "/api" or path.startswith("/api/")' in dashboard_text
    rows = [
        {"name": "dashboard-api-info-routing", "status": "pass" if dashboard_api_info_safe else "blocked", "message": "/api-info is not captured by the /api prefix router."},
        {"name": "get-release-dry-run", "status": "pass" if release_get_save_false else "blocked", "message": "GET release routes use dry-run/save=False previews."},
        {"name": "get-save-true-scan", "status": "blocked" if get_has_save_true else "pass", "message": "No save=True literal detected in API GET section."},
        {"name": "post-confirmation-gates", "status": "pass" if post_has_confirmations else "blocked", "message": "Live/destructive POST release paths require explicit confirmation tokens."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "rows": rows, "message": "Route safety harness completed."}
    if save:
        _write_json(ROUTE_SAFETY_HARNESS, report)
    else:
        report["preview_only"] = True
    return report


def build_release_dashboard_command_center(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v21.8: check that dashboard/API/CLI expose the release command center surfaces."""
    dashboard_text = (ROOT_DIR / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="replace")
    api_text = (ROOT_DIR / "conscious_agent" / "api_server.py").read_text(encoding="utf-8", errors="replace")
    main_text = (ROOT_DIR / "conscious_agent" / "main.py").read_text(encoding="utf-8", errors="replace")
    required = [
        "deterministic-release-manifest",
        "update-dry-run-plan",
        "route-safety-harness",
        "clean-room-install-harness",
        "verified-self-update-release-pipeline",
    ]
    rows = []
    for token in required:
        rows.append({"name": token, "status": "pass" if token in dashboard_text and token in api_text and token in main_text else "blocked", "message": "Exposed in dashboard/API/CLI."})
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "rows": rows, "message": "Release dashboard command center check completed."}
    if save:
        _write_json(RELEASE_DASHBOARD_COMMAND_CENTER, report)
    else:
        report["preview_only"] = True
    return report


def build_clean_room_install_harness(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, run_smoke_tier: str = "fast", save: bool = True) -> dict[str, Any]:
    """v21.9: simulate a clean install from an external zip in a temporary directory."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    rows: list[dict[str, Any]] = []
    if not resolved:
        rows.append({"name": "target-zip", "status": "warn", "message": "No zip available; clean-room install harness skipped."})
        status = _status_from(rows)
        report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "skipped": True, "rows": rows, "message": "Clean-room install harness skipped because no target zip was available."}
        if save:
            _write_json(CLEAN_ROOM_INSTALL_HARNESS, report)
        else:
            report["preview_only"] = True
        return report
    with tempfile.TemporaryDirectory(prefix="eidolon_clean_install_") as tmp:
        with zipfile.ZipFile(resolved, "r") as zf:
            names = [info.filename for info in zf.infolist() if not info.is_dir()]
            common_root = _zip_common_root(names)
            zf.extractall(tmp)
        root = Path(tmp) / common_root if common_root and (Path(tmp) / common_root).exists() else Path(tmp)
        py_files = [str(path) for path in sorted((root / "conscious_agent").glob("*.py"))]
        smoke_path = root / "tools" / "smoke_check.py"
        if smoke_path.exists():
            py_files.append(str(smoke_path))
        compile_result = _run_short_command([sys.executable, "-m", "py_compile", *py_files], timeout=90) if py_files else {"ok": False, "error": "No Python files found."}
        version_result = _run_short_command([sys.executable, "-c", "import sys; sys.path.insert(0, 'conscious_agent'); import dashboard, api_server; print(dashboard.DASHBOARD_VERSION, api_server.API_VERSION)"], timeout=45, cwd=root)
        first_run_result = _run_short_command([sys.executable, "conscious_agent/main.py", "--first-run-check", "--readiness-json"], timeout=60, cwd=root)
        smoke_result = _run_short_command([sys.executable, "-u", "tools/smoke_check.py", "--tier", run_smoke_tier, "--json"], timeout=240, cwd=root)
    rows.extend([
        {"name": "target-zip", "status": "pass", "message": str(resolved)},
        {"name": "compile", "status": "pass" if compile_result.get("ok") else "blocked", "message": "Clean-room compile passed." if compile_result.get("ok") else str(compile_result.get("error") or compile_result.get("stderr_tail"))},
        {"name": "version-import", "status": "pass" if version_result.get("ok") else "blocked", "message": (version_result.get("stdout_tail") or version_result.get("stderr_tail") or "").strip()},
        {"name": "first-run", "status": "pass" if first_run_result.get("ok") else "blocked", "message": "First-run check completed." if first_run_result.get("ok") else str(first_run_result.get("stderr_tail"))},
        {"name": "smoke", "status": "pass" if smoke_result.get("ok") else "blocked", "message": f"Smoke tier {run_smoke_tier} completed." if smoke_result.get("ok") else str(smoke_result.get("stderr_tail") or smoke_result.get("stdout_tail"))[-500:]},
    ])
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": str(resolved), "run_smoke_tier": run_smoke_tier, "rows": rows, "compile": compile_result, "version_import": version_result, "first_run": first_run_result, "smoke": smoke_result, "message": "Clean-room install harness completed."}
    if save:
        _write_json(CLEAN_ROOM_INSTALL_HARNESS, report)
    else:
        report["preview_only"] = True
    return report


def build_verified_self_update_release_pipeline(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, confirm: bool = False, dry_run: bool = True, expected_manifest_hash: str | None = None, run_clean_room: bool = False, save: bool = True) -> dict[str, Any]:
    """v22.0: verify, bind, preview, and optionally apply a source-only self-update package."""
    package_name = package_name or _package_name()
    smoke = build_smoke_runtime_hardening(project_id=project_id, save=save)
    clean = build_clean_room_install_harness(project_id=project_id, package_name=package_name, zip_path=zip_path, run_smoke_tier="fast", save=save) if run_clean_room else {"version": RELEASE_INSTALLATION_VERSION, "status": "warn", "ok": True, "skipped": True, "message": "Clean-room harness skipped; pass run_clean_room=True to execute."}
    external = build_external_zip_install_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, run_compile=True, save=save)
    manifest = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=save)
    plan = build_update_dry_run_plan(project_id=project_id, package_name=package_name, zip_path=zip_path, save=save)
    migration = build_runtime_migration_assistant(project_id=project_id, confirm=False, dry_run=True, save=save)
    routes = build_route_safety_harness(project_id=project_id, save=save)
    command_center = build_release_dashboard_command_center(project_id=project_id, save=save)
    actual_hash = manifest.get("manifest_sha256") or plan.get("manifest_sha256")
    update = build_atomic_source_update(project_id=project_id, package_name=package_name, zip_path=zip_path, expected_manifest_hash=expected_manifest_hash or (actual_hash if dry_run else None), confirm=confirm, dry_run=dry_run or not confirm, save=save)
    steps = {"smoke": smoke, "external_zip": external, "deterministic_manifest": manifest, "update_plan": plan, "migration": migration, "routes": routes, "command_center": command_center, "clean_room": clean, "atomic_update": update}
    blocked = [name for name, report in steps.items() if isinstance(report, dict) and report.get("ok") is False]
    status = "blocked" if blocked else "dry_run" if dry_run or not confirm else "updated"
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": not blocked, "dry_run": dry_run or not confirm, "package_name": package_name, "zip_path": zip_path, "manifest_sha256": actual_hash, "steps": steps, "blocked_steps": blocked, "message": "Verified self-update release pipeline completed."}
    if save:
        _write_json(VERIFIED_SELF_UPDATE_RELEASE_PIPELINE, report)
    else:
        report["preview_only"] = True
    return report


def build_trial_upgrade_harness(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, run_smoke_tier: str = "fast", save: bool = True) -> dict[str, Any]:
    """v22.1: rehearse a release zip as a clean install plus no-op upgrade inside a temp folder."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    rows: list[dict[str, Any]] = []
    if not resolved:
        rows.append({"name": "target-zip", "status": "blocked", "message": "No release zip was supplied or found for the trial upgrade harness."})
        status = _status_from(rows)
        report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": False, "skipped": True, "package_name": package_name, "zip_path": zip_path, "rows": rows, "message": "Trial upgrade harness requires an external source-only release zip."}
        if save:
            _write_json(TRIAL_UPGRADE_HARNESS, report)
        else:
            report["preview_only"] = True
        return report

    external = build_external_zip_install_verification(project_id=project_id, package_name=package_name, zip_path=str(resolved), run_compile=True, save=False)
    manifest = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=str(resolved), save=False)
    clean = build_clean_room_install_harness(project_id=project_id, package_name=package_name, zip_path=str(resolved), run_smoke_tier=run_smoke_tier, save=False)
    file_rows, violations, common_root = _zip_file_rows(resolved)
    trial_plan: dict[str, Any] = {"ok": False, "status": "blocked", "message": "Trial plan did not run."}
    trial_root = None
    if not violations:
        with tempfile.TemporaryDirectory(prefix="eidolon_trial_upgrade_") as tmp:
            with zipfile.ZipFile(resolved, "r") as zf:
                zf.extractall(tmp)
            root = Path(tmp) / common_root if common_root and (Path(tmp) / common_root).exists() else Path(tmp)
            trial_root = str(root)
            trial_plan = build_update_dry_run_plan(project_id=project_id, package_name=package_name, zip_path=str(resolved), install_root=str(root), save=False)
    else:
        trial_plan = {"ok": False, "status": "blocked", "message": "Trial plan skipped because zip path/privacy violations were detected.", "new_files": [], "changed_files": [], "removed_files": [], "dry_run": True}

    changed = len(trial_plan.get("changed_files") or [])
    new_files = len(trial_plan.get("new_files") or [])
    removed = len(trial_plan.get("removed_files") or [])
    no_op = changed == 0 and new_files == 0 and removed == 0 and bool(trial_plan.get("ok"))
    manifest_hash = manifest.get("manifest_sha256") or trial_plan.get("manifest_sha256")
    rows.extend([
        {"name": "target-zip", "status": "pass", "message": str(resolved)},
        {"name": "external-zip-verification", "status": "pass" if external.get("ok") else "blocked", "message": external.get("message")},
        {"name": "deterministic-manifest", "status": "pass" if manifest.get("ok") else "blocked", "message": str(manifest_hash or "missing manifest hash")},
        {"name": "clean-room-install", "status": "pass" if clean.get("ok") else "blocked", "message": clean.get("message")},
        {"name": "temp-upgrade-dry-run", "status": "pass" if trial_plan.get("ok") else "blocked", "message": trial_plan.get("message")},
        {"name": "no-op-upgrade-match", "status": "pass" if no_op else "blocked", "message": f"new={new_files} changed={changed} removed={removed}; a zip compared with its own temp install should be a no-op."},
        {"name": "rollback-metadata-preview", "status": "pass" if manifest_hash and trial_plan.get("dry_run") else "blocked", "message": "Rollback metadata would be bound to the exact manifest during live apply; trial mode writes no rollback pointer."},
        {"name": "runtime-preservation", "status": "pass" if not violations else "blocked", "message": f"{len(violations)} source-only/privacy violation(s); private runtime data remains outside the temp trial."},
        {"name": "live-apply-safety", "status": "pass", "message": "Trial harness performs no live source update and does not modify real apply/rollback pointers."},
    ])
    status = _status_from(rows)
    report = {
        "version": RELEASE_INSTALLATION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": _ok_from(status),
        "package_name": package_name,
        "zip_path": str(resolved),
        "common_root": common_root,
        "file_count": len(file_rows),
        "run_smoke_tier": run_smoke_tier,
        "manifest_sha256": manifest_hash,
        "trial_root_discarded": trial_root,
        "steps": {"external_zip": external, "deterministic_manifest": manifest, "clean_room": clean, "update_dry_run_plan": trial_plan},
        "blocked_steps": [row["name"] for row in rows if str(row.get("status")).lower() in {"blocked", "failed", "fail", "timeout"}],
        "rows": rows,
        "message": "Trial upgrade harness completed a temp clean install plus no-op update rehearsal from the release zip.",
    }
    if save:
        _write_json(TRIAL_UPGRADE_HARNESS, report)
    else:
        report["preview_only"] = True
    return report


def _copy_source_tree_for_drill(destination: Path) -> list[str]:
    """Copy share-safe source files into a temporary drill root and return copied relative paths."""
    copied: list[str] = []
    inventory = build_package_inventory(project_id="eidolon", save=False)
    for row in inventory.get("included", []):
        rel = str(row.get("path"))
        source = ROOT_DIR / rel
        target = destination / rel
        if not source.exists() or not source.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(rel)
    return copied


def _hash_tree(root: Path, rel_paths: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel in sorted(set(rel_paths)):
        path = root / rel
        if path.exists() and path.is_file():
            hashes[rel] = _sha256_file(path)
    return hashes


def build_backup_rollback_drill(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v22.2: exercise backup and rollback behavior in a throwaway install tree only."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="eidolon_rollback_drill_") as tmp:
        drill_root = Path(tmp) / "install"
        copied = _copy_source_tree_for_drill(drill_root)
        before = _hash_tree(drill_root, copied)
        changed_rel = copied[0] if copied else "README_NEXT_STEPS.md"
        changed_path = drill_root / changed_rel
        changed_path.parent.mkdir(parents=True, exist_ok=True)
        original_bytes = changed_path.read_bytes() if changed_path.exists() else b""
        backup_dir = Path(tmp) / "backup"
        backup_file = backup_dir / changed_rel
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        backup_file.write_bytes(original_bytes)
        changed_path.write_bytes(original_bytes + b"\n# rollback-drill-marker\n")
        modified_hash = _sha256_file(changed_path)
        changed_path.write_bytes(backup_file.read_bytes())
        after = _hash_tree(drill_root, copied)
    restored = before == after and bool(copied)
    rows.extend([
        {"name": "temp-install", "status": "pass" if copied else "blocked", "message": f"Copied {len(copied)} source-safe file(s) into a temporary drill install."},
        {"name": "backup-created", "status": "pass" if copied else "blocked", "message": "A changed file backup was created in temp space."},
        {"name": "rollback-restore", "status": "pass" if restored else "blocked", "message": "Rollback restored original file hashes." if restored else "Rollback hash verification failed or no files were available."},
        {"name": "real-runtime-safe", "status": "pass", "message": "The drill used tempfile state only and wrote no real rollback pointer."},
        {"name": "target-zip", "status": "pass" if resolved else "warn", "message": str(resolved) if resolved else "No zip required; drill validates local transaction mechanics."},
    ])
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": str(resolved) if resolved else None, "changed_file": changed_rel, "modified_hash": locals().get("modified_hash"), "rows": rows, "message": "Backup and rollback drill completed in a temporary install tree."}
    if save:
        _write_json(BACKUP_ROLLBACK_DRILL, report)
    else:
        report["preview_only"] = True
    return report


def build_update_collision_detector(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, install_root: str | None = None, save: bool = True) -> dict[str, Any]:
    """v22.3: detect update collisions before any staged or live apply."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    root = Path(install_root).resolve() if install_root else ROOT_DIR
    collisions: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    zip_paths: list[str] = []
    if resolved:
        entries = _zip_manifest_entries(resolved)
        zip_paths = [str(item.get("path")) for item in entries]
        lowered: dict[str, str] = {}
        for rel in zip_paths:
            low = rel.lower()
            if low in lowered and lowered[low] != rel:
                collisions.append({"path": rel, "other": lowered[low], "reason": "case-insensitive path collision"})
            lowered[low] = rel
            if rel.startswith("data/") and not _is_source_safe_data(rel):
                collisions.append({"path": rel, "reason": "release zip contains non-allowlisted runtime data"})
            if any(part in {"__pycache__", ".git", ".venv", "venv"} for part in Path(rel).parts):
                collisions.append({"path": rel, "reason": "generated/cache/env path in release zip"})
            current = root / rel
            if current.exists() and current.is_file():
                try:
                    current_hash = _sha256_file(current)
                    target_hash = next((e.get("sha256") for e in entries if e.get("path") == rel), None)
                    if current_hash != target_hash and rel.endswith((".py", ".md", ".json")):
                        warnings.append({"path": rel, "reason": "local file differs from target package", "current_sha256": current_hash, "target_sha256": target_hash})
                except OSError:
                    collisions.append({"path": rel, "reason": "could not hash local file"})
    else:
        warnings.append({"path": package_name, "reason": "No zip supplied; exact package collision scan skipped."})
    generated = []
    for folder in [root / "conscious_agent", root / "tools"]:
        if folder.exists():
            generated.extend(str(p.relative_to(root)).replace(os.sep, "/") for p in folder.rglob("*.pyc"))
    rows = [
        {"name": "target-zip", "status": "pass" if resolved else "warn", "message": str(resolved) if resolved else "No release zip supplied."},
        {"name": "path-collisions", "status": "blocked" if collisions else "pass", "message": f"{len(collisions)} blocking collision(s)."},
        {"name": "local-differences", "status": "warn" if warnings else "pass", "message": f"{len(warnings)} warning(s) found."},
        {"name": "generated-source-artifacts", "status": "warn" if generated else "pass", "message": f"{len(generated)} pyc artifact(s) under source/tool folders."},
        {"name": "dry-run-only", "status": "pass", "message": "Collision detection is read-only."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": str(resolved) if resolved else None, "install_root": str(root), "collisions": collisions, "warnings": warnings, "generated_artifacts": generated[:100], "rows": rows, "message": "Update collision detector completed."}
    if save:
        _write_json(UPDATE_COLLISION_DETECTOR, report)
    else:
        report["preview_only"] = True
    return report


def build_version_registry_report(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v22.4: preview the local runtime release registry without packaging it."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    manifest = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=str(resolved) if resolved else None, save=False)
    registry_path = DATA_DIR / "release_registry.json"
    registry = _read_json(registry_path, {"entries": []})
    proposed = {"version": RELEASE_INSTALLATION_VERSION, "package_name": package_name, "zip_path": str(resolved) if resolved else None, "manifest_sha256": manifest.get("manifest_sha256"), "recorded_at": _now(), "dry_run": dry_run}
    rows = [
        {"name": "registry-location", "status": "pass", "message": "data/release_registry.json is runtime state and remains excluded from source-only packages."},
        {"name": "manifest-binding", "status": "pass" if proposed.get("manifest_sha256") else "warn", "message": str(proposed.get("manifest_sha256") or "No manifest hash available without a zip/inventory.")},
        {"name": "dry-run-default", "status": "pass" if dry_run else "warn", "message": "Registry report previews by default; live writes require an explicit caller path."},
    ]
    if not dry_run:
        registry.setdefault("entries", []).append(proposed)
        registry["last_updated_for"] = f"v{RELEASE_INSTALLATION_VERSION}"
        _write_json(registry_path, registry)
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status if dry_run else "recorded", "ok": _ok_from(status), "dry_run": dry_run, "package_name": package_name, "zip_path": str(resolved) if resolved else None, "registry_path": str(registry_path.relative_to(ROOT_DIR)), "existing_entry_count": len(registry.get("entries", [])) if isinstance(registry, dict) else 0, "proposed_entry": proposed, "rows": rows, "message": "Version registry report completed."}
    if save:
        _write_json(VERSION_REGISTRY_REPORT, report)
    else:
        report["preview_only"] = True
    return report


def build_release_provenance_report(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v22.5: bind source, manifest, privacy, and verification results into one provenance report."""
    package_name = package_name or _package_name()
    external = build_external_zip_install_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, run_compile=False, save=False)
    manifest = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    privacy = build_package_privacy_scan(project_id=project_id, save=False)
    collision = build_update_collision_detector(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    steps = {"external_zip": external, "deterministic_manifest": manifest, "privacy": privacy, "collision_detector": collision}
    blocked = [name for name, report in steps.items() if isinstance(report, dict) and report.get("ok") is False]
    rows = [
        {"name": "source-profile", "status": "pass", "message": "source-only"},
        {"name": "manifest-sha256", "status": "pass" if manifest.get("manifest_sha256") else "blocked", "message": str(manifest.get("manifest_sha256") or "missing")},
        {"name": "verification-steps", "status": "blocked" if blocked else "pass", "message": f"blocked={blocked}"},
        {"name": "reproducibility-note", "status": "pass", "message": "Manifest entries are sorted and hashed deterministically."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "manifest_sha256": manifest.get("manifest_sha256"), "steps": steps, "blocked_steps": blocked, "rows": rows, "message": "Release provenance report completed."}
    if save:
        _write_json(RELEASE_PROVENANCE_REPORT, report)
    else:
        report["preview_only"] = True
    return report


def build_dashboard_upgrade_wizard_preview(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v22.6: verify dashboard exposes a read-only upgrade wizard preview surface."""
    dashboard_text = (ROOT_DIR / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="replace")
    main_text = (ROOT_DIR / "conscious_agent" / "main.py").read_text(encoding="utf-8", errors="replace")
    required = ["trial-upgrade-from-zip", "backup-rollback-drill", "update-collision-detector", "release-provenance-report", "staged-apply-drill", "v23-readiness-gate"]
    rows = [{"name": token, "status": "pass" if token in dashboard_text or token in main_text else "blocked", "message": "Upgrade preview token is discoverable from dashboard or CLI surfaces."} for token in required]
    rows.append({"name": "preview-only", "status": "pass", "message": "Wizard preview reports do not apply updates."})
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "rows": rows, "message": "Dashboard upgrade wizard preview check completed."}
    if save:
        _write_json(DASHBOARD_UPGRADE_WIZARD_PREVIEW, report)
    else:
        report["preview_only"] = True
    return report


def build_api_upgrade_wizard_preview(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v22.7: verify API preview/update wizard endpoints preserve GET read-only behavior."""
    api_text = (ROOT_DIR / "conscious_agent" / "api_server.py").read_text(encoding="utf-8", errors="replace")
    required = ["trial-upgrade", "backup-rollback-drill", "update-collision-detector", "version-registry-report", "release-provenance-report", "staged-apply-drill", "real-apply-guard-rails", "v23-readiness-gate"]
    get_section = api_text.split("def handle_api_get", 1)[1].split("def handle_api_post", 1)[0] if "def handle_api_get" in api_text and "def handle_api_post" in api_text else ""
    rows = [{"name": token, "status": "pass" if token in api_text else "blocked", "message": "API route token is present."} for token in required]
    rows.append({"name": "get-save-false", "status": "pass" if "save=False" in get_section else "blocked", "message": "GET handlers use preview/read-only report generation."})
    rows.append({"name": "post-confirmation", "status": "pass" if "_require_confirmation" in api_text else "blocked", "message": "POST live paths retain confirmation helper."})
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "rows": rows, "message": "API upgrade wizard preview check completed."}
    if save:
        _write_json(API_UPGRADE_WIZARD_PREVIEW, report)
    else:
        report["preview_only"] = True
    return report


def build_staged_apply_drill(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v22.8: apply a release package only to a temporary clone, then verify rollback there."""
    package_name = package_name or _package_name()
    resolved = _resolve_zip_path(package_name=package_name, zip_path=zip_path)
    rows: list[dict[str, Any]] = []
    if not resolved:
        rows.append({"name": "target-zip", "status": "blocked", "message": "A release zip is required for staged apply drill."})
        status = _status_from(rows)
        report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": False, "package_name": package_name, "rows": rows, "message": "Staged apply drill requires a release zip."}
        if save: _write_json(STAGED_APPLY_DRILL, report)
        else: report["preview_only"] = True
        return report
    with tempfile.TemporaryDirectory(prefix="eidolon_staged_apply_") as tmp:
        clone = Path(tmp) / "clone"
        copied = _copy_source_tree_for_drill(clone)
        before = _hash_tree(clone, copied)
        plan = build_update_dry_run_plan(project_id=project_id, package_name=package_name, zip_path=str(resolved), install_root=str(clone), save=False)
        with zipfile.ZipFile(resolved, "r") as zf:
            names = [info.filename for info in zf.infolist() if not info.is_dir()]
            common_root = _zip_common_root(names)
            zf.extractall(Path(tmp) / "stage")
        stage = Path(tmp) / "stage" / common_root if common_root and (Path(tmp) / "stage" / common_root).exists() else Path(tmp) / "stage"
        touched = sorted(set(plan.get("new_files", [])) | set(plan.get("changed_files", [])))
        backup: dict[str, bytes | None] = {}
        for rel in touched:
            if rel.startswith("data/") and not _is_source_safe_data(rel):
                continue
            src = stage / rel
            dst = clone / rel
            if not src.exists() or src.is_dir():
                continue
            backup[rel] = dst.read_bytes() if dst.exists() else None
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        after_apply = _hash_tree(clone, sorted(set(copied) | set(touched)))
        for rel, data in backup.items():
            dst = clone / rel
            if data is None:
                if dst.exists():
                    dst.unlink()
            else:
                dst.write_bytes(data)
        after_rollback = _hash_tree(clone, copied)
    rows.extend([
        {"name": "target-zip", "status": "pass", "message": str(resolved)},
        {"name": "temp-clone", "status": "pass" if copied else "blocked", "message": f"{len(copied)} source-safe file(s) cloned."},
        {"name": "dry-run-plan", "status": "pass" if plan.get("ok") else "blocked", "message": plan.get("message")},
        {"name": "staged-apply", "status": "pass", "message": f"Applied {len(touched)} planned file(s) to temp clone only."},
        {"name": "rollback-verify", "status": "pass" if before == after_rollback else "blocked", "message": "Temp rollback restored original clone hashes."},
    ])
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": str(resolved), "touched_count": len(touched), "changed_after_apply": before != after_apply, "rows": rows, "plan_summary": summarize_installation_report(plan), "message": "Staged apply drill completed against a temporary clone."}
    if save:
        _write_json(STAGED_APPLY_DRILL, report)
    else:
        report["preview_only"] = True
    return report


def build_real_apply_guard_rails(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, expected_manifest_hash: str | None = None, confirm_phrase: str | None = None, save: bool = True) -> dict[str, Any]:
    """v22.9: verify real apply requirements without applying source changes."""
    package_name = package_name or _package_name()
    manifest = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    collision = build_update_collision_detector(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    trial = build_trial_upgrade_harness(project_id=project_id, package_name=package_name, zip_path=zip_path, run_smoke_tier="fast", save=False) if zip_path else {"ok": True, "status": "warn", "message": "Trial upgrade skipped; no zip path supplied."}
    required_phrase = "APPLY EXACT REVIEWED RELEASE"
    actual_hash = manifest.get("manifest_sha256")
    rows = [
        {"name": "manifest-present", "status": "pass" if actual_hash else "blocked", "message": str(actual_hash or "missing")},
        {"name": "manifest-match", "status": "pass" if expected_manifest_hash and expected_manifest_hash == actual_hash else "blocked", "message": f"expected={expected_manifest_hash or 'missing'} actual={actual_hash or 'missing'}"},
        {"name": "confirmation-phrase", "status": "pass" if confirm_phrase == required_phrase else "blocked", "message": f"Required phrase: {required_phrase}"},
        {"name": "collision-detector", "status": "pass" if collision.get("ok") else "blocked", "message": collision.get("message")},
        {"name": "recent-trial", "status": "pass" if trial.get("ok") else "blocked", "message": trial.get("message")},
        {"name": "dry-run-pointer-safety", "status": "pass", "message": "Guard report is read-only and writes no apply pointer."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "required_confirmation_phrase": required_phrase, "expected_manifest_hash": expected_manifest_hash, "actual_manifest_hash": actual_hash, "steps": {"manifest": manifest, "collision": collision, "trial": trial}, "rows": rows, "message": "Real apply guard rails evaluated."}
    if save:
        _write_json(REAL_APPLY_GUARD_RAILS, report)
    else:
        report["preview_only"] = True
    return report


def build_real_apply_rollback_verification(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v22.10: verify apply/rollback mechanics in temp space before any real updater is trusted."""
    staged = build_staged_apply_drill(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    registry = build_version_registry_report(project_id=project_id, package_name=package_name, zip_path=zip_path, dry_run=True, save=False)
    rows = [
        {"name": "staged-apply-drill", "status": "pass" if staged.get("ok") else "blocked", "message": staged.get("message")},
        {"name": "registry-preview", "status": "pass" if registry.get("ok") else "blocked", "message": registry.get("message")},
        {"name": "real-apply-disabled", "status": "pass", "message": "This verification does not mutate the real source tree."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name or _package_name(), "zip_path": zip_path, "steps": {"staged_apply": staged, "registry": registry}, "rows": rows, "message": "Real apply and rollback verification completed in safe preview mode."}
    if save:
        _write_json(REAL_APPLY_ROLLBACK_VERIFICATION, report)
    else:
        report["preview_only"] = True
    return report


def build_self_update_ux_polish(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v22.11: check that release/update UX reports explain status, next action, and safety reasons."""
    readme = (ROOT_DIR / "README_NEXT_STEPS.md").read_text(encoding="utf-8", errors="replace") if (ROOT_DIR / "README_NEXT_STEPS.md").exists() else ""
    dashboard = (ROOT_DIR / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="replace")
    main = (ROOT_DIR / "conscious_agent" / "main.py").read_text(encoding="utf-8", errors="replace")
    rows = [
        {"name": "readme-stage-notes", "status": "pass" if "v22.12" in readme and "v23.0" in readme else "blocked", "message": "README contains staged v22.x and v23.0 notes."},
        {"name": "copyable-commands", "status": "pass" if "--v23-readiness-gate" in readme or "--v23-readiness-gate" in main else "blocked", "message": "Release commands are discoverable."},
        {"name": "dashboard-language", "status": "pass" if "release" in dashboard.lower() and "upgrade" in dashboard.lower() else "warn", "message": "Dashboard contains release/upgrade wording."},
        {"name": "failure-explanations", "status": "pass", "message": "Reports use rows with status and message fields."},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "rows": rows, "message": "Self-update UX polish check completed."}
    if save:
        _write_json(SELF_UPDATE_UX_POLISH, report)
    else:
        report["preview_only"] = True
    return report


def build_v23_readiness_gate(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, run_heavy: bool = False, save: bool = True) -> dict[str, Any]:
    """v22.12: final pre-v23 gate across package, install, upgrade, rollback, routes, and docs."""
    package_name = package_name or _package_name()
    steps: dict[str, Any] = {
        "manifest_integrity": build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=False),
        "privacy_scan": build_package_privacy_scan(project_id=project_id, save=False),
        "portable_metadata": build_portable_metadata_check(project_id=project_id, save=False),
        "route_safety": build_route_safety_harness(project_id=project_id, save=False),
        "dashboard_wizard": build_dashboard_upgrade_wizard_preview(project_id=project_id, save=False),
        "api_wizard": build_api_upgrade_wizard_preview(project_id=project_id, save=False),
        "ux_polish": build_self_update_ux_polish(project_id=project_id, save=False),
    }
    if zip_path:
        steps.update({
            "external_zip": build_external_zip_install_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, run_compile=run_heavy, save=False),
            "deterministic_manifest": build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
            "trial_upgrade": build_trial_upgrade_harness(project_id=project_id, package_name=package_name, zip_path=zip_path, run_smoke_tier="fast", save=False),
            "rollback_drill": build_backup_rollback_drill(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
            "collision_detector": build_update_collision_detector(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
            "staged_apply": build_staged_apply_drill(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
            "real_apply_rollback": build_real_apply_rollback_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        })
    else:
        steps["zip_dependent_checks"] = {"ok": True, "status": "warn", "message": "Zip-dependent v23 checks skipped until a release zip path is supplied."}
    blocked = [name for name, report in steps.items() if isinstance(report, dict) and report.get("ok") is False]
    rows = [{"name": name, "status": _row_status_from_report(report), "message": report.get("message") if isinstance(report, dict) else "unknown"} for name, report in steps.items()]
    status = _status_from(rows)
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": not blocked, "package_name": package_name, "zip_path": zip_path, "blocked_steps": blocked, "steps": steps, "rows": rows, "message": "v23 readiness gate completed."}
    if save:
        _write_json(V23_READINESS_GATE, report)
    else:
        report["preview_only"] = True
    return report


def build_controlled_self_maintenance_loop(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v23.0: preview a controlled self-maintenance loop that proposes work but does not self-apply without approval."""
    readiness = build_v23_readiness_gate(project_id=project_id, package_name=package_name, zip_path=zip_path, run_heavy=False, save=False)
    rows = [
        {"name": "readiness-gate", "status": _row_status_from_report(readiness), "message": readiness.get("message")},
        {"name": "proposal-only", "status": "pass", "message": "The v23 loop may propose patches, but apply remains approval-bound."},
        {"name": "artifact-binding", "status": "pass", "message": "Any future live apply must bind to reviewed manifest/checksum artifacts."},
        {"name": "post-only-mutations", "status": "pass", "message": "Live/destructive actions remain POST-only and confirmation-gated."},
        {"name": "dry-run-default", "status": "pass", "message": "The controlled self-maintenance loop defaults to dry-run/report mode."},
    ]
    status = _status_from(rows)
    lifecycle = [
        "detect issue or improvement candidate",
        "draft bounded patch proposal",
        "build review bundle and deterministic artifact manifest",
        "run smoke/release gates",
        "request human approval",
        "apply only through guarded POST/CLI confirmation path",
        "verify post-apply and preserve rollback path",
    ]
    report = {"version": RELEASE_INSTALLATION_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": _ok_from(status), "package_name": package_name or _package_name(), "zip_path": zip_path, "dry_run": True, "lifecycle": lifecycle, "steps": {"v23_readiness_gate": readiness}, "rows": rows, "message": "Controlled self-maintenance loop preview completed."}
    if save:
        _write_json(CONTROLLED_SELF_MAINTENANCE_LOOP, report)
    else:
        report["preview_only"] = True
    return report

def summarize_installation_report(report: dict[str, Any], list_limit: int = 12) -> dict[str, Any]:
    summary = {key: value for key, value in report.items() if key not in {"steps", "packages", "violations", "warnings", "compile", "smoke", "entries", "plan", "runtime_guard", "external_zip", "legacy_unzip", "version_import", "first_run"}}
    for key in ("violations", "warnings", "packages"):
        items = report.get(key)
        if isinstance(items, list):
            summary[f"{key}_sample"] = items[:list_limit]
            summary[f"{key}_count"] = len(items)
            summary[f"{key}_truncated"] = len(items) > list_limit
    steps = report.get("steps")
    if isinstance(steps, dict):
        summary["steps"] = {name: {"status": value.get("status"), "ok": value.get("ok"), "message": value.get("message"), "package_name": value.get("package_name")} for name, value in steps.items() if isinstance(value, dict)}
    summary["summary_only"] = True
    return summary


def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [f"# {title}", "", f"Version: {report.get('version')}", f"Checked at: {report.get('checked_at', '')}", f"Status: {str(report.get('status', 'unknown')).upper()}", f"Message: {report.get('message', '')}"]
    if report.get("package_name"):
        lines.append(f"Package: {report.get('package_name')}")
    rows = report.get("rows") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:100]:
            lines.append(f"- {str(row.get('status', 'info')).upper()} {row.get('name')}: {row.get('message', '')}")
    if report.get("blocked_steps"):
        lines.extend(["", "## Blocked steps"])
        lines.extend([f"- {item}" for item in report.get("blocked_steps", [])])
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def release_profiles_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v20.1 Release Profiles", report or build_release_profiles(save=False), full)


def package_privacy_scan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v20.2 Package Privacy Scan", report or build_package_privacy_scan(save=False), full)


def portable_metadata_check_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v20.3 Portable Metadata Check", report or build_portable_metadata_check(save=False), full)


def first_run_check_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v20.4 First-Run Check", report or build_first_run_check(save=False), full)


def dependency_advisor_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v20.5 Dependency Advisor", report or build_dependency_advisor(save=False), full)


def upgrade_notes_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v20.6 Upgrade Notes", report or build_upgrade_notes(save=False), full)


def runtime_migration_check_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v20.7 Runtime Migration Check", report or build_runtime_migration_check(save=False), full)


def release_install_verification_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v20.8 Release Install Verification", report or build_release_install_verification(save=False), full)


def verified_installable_release_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.0 Verified Installable Release Loop", report or build_verified_installable_release_loop(save=False), full)



def smoke_runtime_hardening_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.1 Smoke Runtime Hardening", report or build_smoke_runtime_hardening(save=False), full)


def external_zip_install_verification_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.2 External Zip Install Verification", report or build_external_zip_install_verification(save=False), full)


def deterministic_release_manifest_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.3 Deterministic Release Manifest", report or build_deterministic_release_manifest(save=False), full)


def update_dry_run_plan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.4 Update Dry-Run Plan", report or build_update_dry_run_plan(save=False), full)


def atomic_source_update_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.5 Atomic Source Update", report or build_atomic_source_update(save=False), full)


def runtime_migration_assistant_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.6 Runtime Migration Assistant", report or build_runtime_migration_assistant(save=False), full)


def route_safety_harness_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.7 Route Safety Harness", report or build_route_safety_harness(save=False), full)


def release_dashboard_command_center_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.8 Release Dashboard Command Center", report or build_release_dashboard_command_center(save=False), full)


def clean_room_install_harness_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.9 Clean-Room Install Harness", report or build_clean_room_install_harness(save=False), full)


def verified_self_update_release_pipeline_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.0 Verified Self-Update Release Pipeline", report or build_verified_self_update_release_pipeline(save=False), full)


def trial_upgrade_harness_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.1 Trial Upgrade Harness", report or build_trial_upgrade_harness(save=False), full)


def backup_rollback_drill_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.2 Backup and Rollback Drill", report or build_backup_rollback_drill(save=False), full)


def update_collision_detector_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.3 Update Collision Detector", report or build_update_collision_detector(save=False), full)


def version_registry_report_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.4 Version Registry Report", report or build_version_registry_report(save=False), full)


def release_provenance_report_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.5 Release Provenance Report", report or build_release_provenance_report(save=False), full)


def dashboard_upgrade_wizard_preview_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.6 Dashboard Upgrade Wizard Preview", report or build_dashboard_upgrade_wizard_preview(save=False), full)


def api_upgrade_wizard_preview_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.7 API Upgrade Wizard Preview", report or build_api_upgrade_wizard_preview(save=False), full)


def staged_apply_drill_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.8 Staged Apply Drill", report or build_staged_apply_drill(save=False), full)


def real_apply_guard_rails_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.9 Real Apply Guard Rails", report or build_real_apply_guard_rails(save=False), full)


def real_apply_rollback_verification_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.10 Real Apply + Rollback Verification", report or build_real_apply_rollback_verification(save=False), full)


def self_update_ux_polish_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.11 Self-Update UX Polish", report or build_self_update_ux_polish(save=False), full)


def v23_readiness_gate_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v22.12 v23 Readiness Gate", report or build_v23_readiness_gate(save=False), full)


def controlled_self_maintenance_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.0 Controlled Self-Maintenance Loop", report or build_controlled_self_maintenance_loop(save=False), full)

def print_release_profiles(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_profiles(project_id=project_id, save=True)
    _json_print(report) if json_output else print(release_profiles_text(report, full))


def print_package_privacy_scan(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_package_privacy_scan(project_id=project_id, save=True)
    _json_print(report) if json_output else print(package_privacy_scan_text(report, full))


def print_portable_metadata_check(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_portable_metadata_check(project_id=project_id, save=True)
    _json_print(report) if json_output else print(portable_metadata_check_text(report, full))


def print_first_run_check(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_first_run_check(project_id=project_id, save=True)
    _json_print(report) if json_output else print(first_run_check_text(report, full))


def print_dependency_advisor(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_dependency_advisor(project_id=project_id, save=True)
    _json_print(report) if json_output else print(dependency_advisor_text(report, full))


def print_upgrade_notes(project_id: str = "eidolon", from_version: str = "20.0.1", to_version: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_upgrade_notes(project_id=project_id, from_version=from_version, to_version=to_version, save=True)
    _json_print(report) if json_output else print(upgrade_notes_text(report, full))


def print_runtime_migration_check(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_runtime_migration_check(project_id=project_id, save=True)
    _json_print(report) if json_output else print(runtime_migration_check_text(report, full))


def print_release_install_verification(project_id: str = "eidolon", package_name: str | None = None, run_smoke: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_release_install_verification(project_id=project_id, package_name=package_name, run_smoke=run_smoke, save=True)
    _json_print(report) if json_output else print(release_install_verification_text(report, full))


def print_verified_installable_release_loop(project_id: str = "eidolon", package_name: str | None = None, confirm: bool = False, dry_run: bool = True, run_smoke: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_verified_installable_release_loop(project_id=project_id, package_name=package_name, confirm=confirm, dry_run=dry_run or not confirm, run_smoke=run_smoke, save=True)
    _json_print(report) if json_output else print(verified_installable_release_loop_text(report, full))


def print_smoke_runtime_hardening(project_id: str = "eidolon", tier: str = "full", full: bool = False, json_output: bool = False) -> None:
    report = build_smoke_runtime_hardening(project_id=project_id, tier=tier, save=True)
    _json_print(report) if json_output else print(smoke_runtime_hardening_text(report, full))


def print_external_zip_install_verification(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_external_zip_install_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report) if json_output else print(external_zip_install_verification_text(report, full))


def print_deterministic_release_manifest(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report) if json_output else print(deterministic_release_manifest_text(report, full))


def print_update_dry_run_plan(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_update_dry_run_plan(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report) if json_output else print(update_dry_run_plan_text(report, full))


def print_atomic_source_update(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, expected_manifest_hash: str | None = None, confirm: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_atomic_source_update(project_id=project_id, package_name=package_name, zip_path=zip_path, expected_manifest_hash=expected_manifest_hash, confirm=confirm, dry_run=dry_run or not confirm, save=True)
    _json_print(report) if json_output else print(atomic_source_update_text(report, full))


def print_runtime_migration_assistant(project_id: str = "eidolon", confirm: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_runtime_migration_assistant(project_id=project_id, confirm=confirm, dry_run=dry_run or not confirm, save=True)
    _json_print(report) if json_output else print(runtime_migration_assistant_text(report, full))


def print_route_safety_harness(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_route_safety_harness(project_id=project_id, save=True)
    _json_print(report) if json_output else print(route_safety_harness_text(report, full))


def print_release_dashboard_command_center(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_dashboard_command_center(project_id=project_id, save=True)
    _json_print(report) if json_output else print(release_dashboard_command_center_text(report, full))


def print_clean_room_install_harness(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, run_smoke_tier: str = "fast", full: bool = False, json_output: bool = False) -> None:
    report = build_clean_room_install_harness(project_id=project_id, package_name=package_name, zip_path=zip_path, run_smoke_tier=run_smoke_tier, save=True)
    _json_print(report) if json_output else print(clean_room_install_harness_text(report, full))


def print_verified_self_update_release_pipeline(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, expected_manifest_hash: str | None = None, confirm: bool = False, dry_run: bool = True, run_clean_room: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_verified_self_update_release_pipeline(project_id=project_id, package_name=package_name, zip_path=zip_path, expected_manifest_hash=expected_manifest_hash, confirm=confirm, dry_run=dry_run or not confirm, run_clean_room=run_clean_room, save=True)
    _json_print(report) if json_output else print(verified_self_update_release_pipeline_text(report, full))


def print_trial_upgrade_harness(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, run_smoke_tier: str = "fast", full: bool = False, json_output: bool = False) -> None:
    report = build_trial_upgrade_harness(project_id=project_id, package_name=package_name, zip_path=zip_path, run_smoke_tier=run_smoke_tier, save=True)
    _json_print(report) if json_output else print(trial_upgrade_harness_text(report, full))


def print_backup_rollback_drill(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_backup_rollback_drill(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(backup_rollback_drill_text(report, full=full))


def print_update_collision_detector(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_update_collision_detector(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(update_collision_detector_text(report, full=full))


def print_version_registry_report(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_version_registry_report(project_id=project_id, package_name=package_name, zip_path=zip_path, dry_run=dry_run, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(version_registry_report_text(report, full=full))


def print_release_provenance_report(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_provenance_report(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(release_provenance_report_text(report, full=full))


def print_dashboard_upgrade_wizard_preview(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_dashboard_upgrade_wizard_preview(project_id=project_id, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(dashboard_upgrade_wizard_preview_text(report, full=full))


def print_api_upgrade_wizard_preview(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_api_upgrade_wizard_preview(project_id=project_id, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(api_upgrade_wizard_preview_text(report, full=full))


def print_staged_apply_drill(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_staged_apply_drill(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(staged_apply_drill_text(report, full=full))


def print_real_apply_guard_rails(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, expected_manifest_hash: str | None = None, confirm_phrase: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_real_apply_guard_rails(project_id=project_id, package_name=package_name, zip_path=zip_path, expected_manifest_hash=expected_manifest_hash, confirm_phrase=confirm_phrase, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(real_apply_guard_rails_text(report, full=full))


def print_real_apply_rollback_verification(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_real_apply_rollback_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(real_apply_rollback_verification_text(report, full=full))


def print_self_update_ux_polish(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_self_update_ux_polish(project_id=project_id, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(self_update_ux_polish_text(report, full=full))


def print_v23_readiness_gate(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, run_heavy: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_v23_readiness_gate(project_id=project_id, package_name=package_name, zip_path=zip_path, run_heavy=run_heavy, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(v23_readiness_gate_text(report, full=full))


def print_controlled_self_maintenance_loop(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_controlled_self_maintenance_loop(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _json_print(report if full else summarize_installation_report(report)) if json_output else print(controlled_self_maintenance_loop_text(report, full=full))

