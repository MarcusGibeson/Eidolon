from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from approval_release_workflow import (
    APPROVAL_RELEASE_VERSION,
    AI_PATCH_REVIEW_BUNDLE,
    VALIDATED_PATCH_APPROVAL_MANIFEST,
    REVIEW_BUNDLE_INTEGRITY,
    APPROVAL_READY,
    VALIDATED_AI_APPLY,
    VALIDATED_AI_DRY_RUN_APPLY,
    POST_APPLY_REVIEW,
    PACKAGE_BUILD_PLAN,
    APPROVAL_TO_RELEASE_LOOP,
    build_ai_patch_review_bundle,
    build_review_bundle_integrity,
    build_approval_ready,
    build_post_apply_review,
    build_package_build_plan,
    build_approval_to_release_loop,
)
from release_pipeline import RELEASE_READINESS, build_release_readiness
from code_patch_release import build_release_artifact, build_release_audit_trail
from patch_drafting import APPROVAL_STATE
from workspace_orchestration import _timeline_event

RELEASE_PACKAGING_VERSION = "30.0"
RELEASE_PACKAGE_DIR = DATA_DIR / "release_package"
RELEASES_DIR = DATA_DIR / "releases"
RELEASE_MANIFEST_INTEGRITY = RELEASE_PACKAGE_DIR / "release_manifest_integrity.json"
PACKAGE_INVENTORY = RELEASE_PACKAGE_DIR / "package_inventory.json"
PACKAGE_CHECKSUMS = RELEASE_PACKAGE_DIR / "package_checksums.json"
RELEASE_NOTES = RELEASE_PACKAGE_DIR / "release_notes.json"
RELEASE_HANDOFF_REPORT = RELEASE_PACKAGE_DIR / "release_handoff_report.json"
BUILD_RELEASE_ZIP = RELEASE_PACKAGE_DIR / "build_release_zip.json"
VERIFY_RELEASE_UNZIP = RELEASE_PACKAGE_DIR / "verify_release_unzip.json"
RELEASE_PIPELINE_AUDIT = RELEASE_PACKAGE_DIR / "release_pipeline_audit.json"
VERIFIED_RELEASE_PACKAGE_LOOP = RELEASE_PACKAGE_DIR / "verified_release_package_loop.json"

EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", "reports"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log"}
EXCLUDE_FILES = {
    "approval_state.json",
    "memories.json",
    "thoughts.log",
}
# v20.0.1: release zips use a source-only data profile by default.
# Runtime/private/generated data is excluded unless explicitly allowlisted here.
SOURCE_ONLY_DATA_FILES = {
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/projects.json",
    "data/workspaces/active_project.json",
}
SOURCE_ONLY_DATA_PREFIXES = (
    "data/workspaces/command_profiles/",
)
EXCLUDE_PARTS = {
    ("data", "chat_actions"),
    ("data", "controlled_build_reports"),
    ("data", "diagnostics"),
    ("data", "diagnostic_reports"),
    ("data", "maintenance_scans"),
    ("data", "notifications"),
    ("data", "onboarding"),
    ("data", "patch_drafts"),
    ("data", "patch_workspace"),
    ("data", "patches"),
    ("data", "release_package"),
    ("data", "releases"),
    ("data", "self_improvements"),
    ("data", "session_plans"),
    ("data", "stable_loops"),
    ("data", "test_reports"),
    ("data", "test_reviews"),
    ("data", "watch_reports"),
    ("data", "work_cycles"),
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    RELEASE_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    _ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _status_from(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("status", "pass")).lower() for row in rows}
    if statuses & {"blocked", "failed", "fail"}:
        return "blocked"
    if statuses & {"warn", "warning"}:
        return "warn"
    return "pass"


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def summarize_release_report(report: dict[str, Any], list_limit: int = 25) -> dict[str, Any]:
    """Return a dashboard/API-safe summary without giant inventory/checksum payloads."""
    summary = {
        key: value
        for key, value in report.items()
        if key not in {"included", "excluded", "checksums", "steps", "readme_excerpt"}
    }
    for key in ("included", "excluded", "checksums"):
        items = report.get(key)
        if isinstance(items, list):
            summary[f"{key}_sample"] = items[:list_limit]
            summary[f"{key}_truncated"] = len(items) > list_limit
    steps = report.get("steps")
    if isinstance(steps, dict):
        summary["steps"] = {
            name: {
                "status": value.get("status"),
                "ok": value.get("ok"),
                "message": value.get("message"),
                "included_count": value.get("included_count"),
                "excluded_count": value.get("excluded_count"),
                "checksum_count": value.get("checksum_count"),
                "package_name": value.get("package_name"),
            }
            for name, value in steps.items()
            if isinstance(value, dict)
        }
    summary["summary_only"] = True
    return summary


def _current_version() -> str:
    settings = _read_json(DATA_DIR / "settings.json", {})
    return str(settings.get("version") or settings.get("last_updated_for") or RELEASE_PACKAGING_VERSION).lstrip("v")


def _package_name(default: str | None = None) -> str:
    version = _current_version().replace(".", "_")
    return default or f"Eidolon_v{version}.zip"


def _rel_path(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR)).replace(os.sep, "/")


def _is_source_data_file(rel: str) -> bool:
    return rel in SOURCE_ONLY_DATA_FILES or any(rel.startswith(prefix) for prefix in SOURCE_ONLY_DATA_PREFIXES)


def _is_excluded(path: Path) -> tuple[bool, str]:
    rel = _rel_path(path)
    parts = Path(rel).parts
    if any(part in EXCLUDE_DIRS for part in parts):
        return True, "excluded generated/cache/env directory"
    if path.suffix in EXCLUDE_SUFFIXES:
        return True, "excluded generated/log/bytecode file"
    if path.name in EXCLUDE_FILES:
        return True, "excluded live approval state"
    if rel.startswith("data/") and not _is_source_data_file(rel):
        return True, "excluded private/runtime data by source-only package profile"
    if len(parts) >= 2 and (parts[0], parts[1]) in EXCLUDE_PARTS:
        return True, "excluded generated release-package output"
    if path.suffix == ".zip":
        return True, "excluded nested release zip"
    return False, "included source release file"


def _should_prune_dir(parent: Path, dirname: str) -> bool:
    if dirname in EXCLUDE_DIRS:
        return True
    rel = str((parent / dirname).relative_to(ROOT_DIR)).replace(os.sep, "/")
    if rel == "data":
        return False
    if rel.startswith("data/"):
        prefix = rel + "/"
        if any(item.startswith(prefix) for item in SOURCE_ONLY_DATA_FILES):
            return False
        if any(allowed.startswith(prefix) or prefix.startswith(allowed) for allowed in SOURCE_ONLY_DATA_PREFIXES):
            return False
        return True
    return False


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for root, dirs, filenames in os.walk(ROOT_DIR):
        root_path = Path(root)
        dirs[:] = sorted(d for d in dirs if not _should_prune_dir(root_path, d))
        for name in sorted(filenames):
            files.append(root_path / name)
    return sorted(files)


def build_release_manifest_integrity(project_id: str = "eidolon", package_name: str | None = None, save: bool = True) -> dict[str, Any]:
    """v19.1: verify release metadata and package manifest consistency."""
    version = _current_version()
    settings = _read_json(DATA_DIR / "settings.json", {})
    projects = _read_json(DATA_DIR / "projects.json", {})
    workspace_projects = _read_json(DATA_DIR / "workspaces" / "projects.json", {})
    readme_path = ROOT_DIR / "README_NEXT_STEPS.md"
    readme = readme_path.read_text(encoding="utf-8", errors="replace") if readme_path.exists() else ""
    dashboard_text = (ROOT_DIR / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="replace")
    api_text = (ROOT_DIR / "conscious_agent" / "api_server.py").read_text(encoding="utf-8", errors="replace")
    bundle = _read_json(AI_PATCH_REVIEW_BUNDLE, {}) or {"status": "warn", "ok": True, "message": "Review bundle has not been saved yet; run --ai-patch-review-bundle when preparing approval."}
    integrity = _read_json(REVIEW_BUNDLE_INTEGRITY, {}) or {"status": "warn", "ok": True, "message": "Review integrity has not been saved yet; run --ai-patch-review-integrity when preparing approval."}
    readiness = _read_json(RELEASE_READINESS, {}) or {"status": "warn", "ok": True, "message": "Release readiness has not been saved yet; run --release-readiness or --doctor before final handoff."}
    package_plan = _read_json(PACKAGE_BUILD_PLAN, {}) or {"status": "warn", "ok": True, "message": "Package build plan has not been saved yet; run --package-build-plan when preparing handoff."}
    manifest = _read_json(VALIDATED_PATCH_APPROVAL_MANIFEST, {})
    rows = [
        {"name": "settings-version", "status": "pass" if (str(settings.get("version") or settings.get("settings_version")) == version and settings.get("last_updated_for") == f"v{version}") else "blocked", "message": f"settings version={settings.get('version') or settings.get('settings_version')} last_updated_for={settings.get('last_updated_for')} expected=v{version}"},
        {"name": "projects-version", "status": "pass" if projects.get("last_updated_for") == f"v{version}" else "blocked", "message": f"projects last_updated_for={projects.get('last_updated_for')} expected=v{version}"},
        {"name": "workspace-root-version", "status": "pass" if str(workspace_projects.get("version")) in {version, f"v{version}"} else "blocked", "message": f"workspace root version={workspace_projects.get('version')} expected={version} or v{version}"},
        {"name": "workspace-project-version", "status": "pass" if any(str(item.get("version")) in {version, f"v{version}"} and str(item.get("current_milestone", "")).find(f"v{version}") >= 0 for item in workspace_projects.get("projects", [])) else "blocked", "message": f"active workspace project metadata must reference v{version}."},
        {"name": "readme-section", "status": "pass" if f"v{version}" in readme else "blocked", "message": f"README must document v{version}."},
        {"name": "dashboard-version", "status": "pass" if f'DASHBOARD_VERSION = "{version}"' in dashboard_text else "blocked", "message": "Dashboard version marker must match release."},
        {"name": "api-version", "status": "pass" if f'API_VERSION = "{version}"' in api_text else "blocked", "message": "API version marker must match release."},
        {"name": "approval-manifest", "status": "pass" if manifest.get("artifact_hashes") else "warn", "message": "Validated patch approval manifest is present or not needed for packaging-only handoff."},
        {"name": "review-bundle", "status": "pass" if bundle.get("ok") else "warn", "message": bundle.get("message", "review bundle preview unavailable")},
        {"name": "review-integrity", "status": "pass" if integrity.get("ok") else "warn", "message": integrity.get("message", "integrity preview unavailable")},
        {"name": "release-readiness", "status": "pass" if readiness.get("ok") else "warn", "message": readiness.get("message", "release readiness preview unavailable")},
        {"name": "package-plan", "status": "pass" if package_plan.get("ok") else "warn", "message": package_plan.get("message", "package plan preview unavailable")},
    ]
    status = _status_from(rows)
    report = {
        "version": RELEASE_PACKAGING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "release_version": version,
        "package_name": package_name or _package_name(),
        "rows": rows,
        "message": "Release manifest integrity verifies version markers, README, package plan, and approval/release artifacts.",
    }
    if save:
        _write_json(RELEASE_MANIFEST_INTEGRITY, report)
    else:
        report["preview_only"] = True
    return report


def build_package_inventory(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v19.2: classify release package files."""
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for path in _iter_files():
        rel = _rel_path(path)
        exclude, reason = _is_excluded(path)
        row = {"path": rel, "size": path.stat().st_size, "reason": reason}
        if exclude:
            excluded.append(row)
        else:
            included.append(row)
    rows = [
        {"name": "included-files", "status": "pass" if included else "blocked", "message": f"{len(included)} file(s) included."},
        {"name": "readme-included", "status": "pass" if any(row["path"] == "README_NEXT_STEPS.md" for row in included) else "blocked", "message": "README_NEXT_STEPS.md must be packaged."},
        {"name": "approval-state-excluded", "status": "pass" if not any(row["path"].endswith("approval_state.json") for row in included) else "blocked", "message": "Live approval state is absent from included package files."},
        {"name": "source-only-data-profile", "status": "pass" if not any(row["path"].startswith("data/") and not _is_source_data_file(row["path"]) for row in included) else "blocked", "message": "Only allowlisted source-safe data files may be packaged."},
        {"name": "data-runtime-excluded", "status": "pass" if any(row["path"].startswith("data/") and row["path"] not in SOURCE_ONLY_DATA_FILES for row in excluded) else "warn", "message": "Runtime/private data folders are excluded by default."},
        {"name": "venv-excluded", "status": "pass", "message": ".git, .venv, __pycache__, .pyc, logs, generated package files, private runtime data, and nested zips are excluded."},
    ]
    status = _status_from(rows)
    report = {
        "version": RELEASE_PACKAGING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "package_profile": "source_only",
        "included_count": len(included),
        "excluded_count": len(excluded),
        "included": included,
        "excluded": excluded,
        "rows": rows,
        "message": "Package inventory classified included and excluded files for a guarded release zip.",
    }
    if save:
        _write_json(PACKAGE_INVENTORY, report)
    else:
        report["preview_only"] = True
    return report


def build_package_checksums(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v19.3: generate SHA-256 hashes for included package files."""
    inventory = build_package_inventory(project_id=project_id, save=False)
    return _build_package_checksums_from_inventory(project_id=project_id, inventory=inventory, save=save)


def _build_package_checksums_from_inventory(project_id: str, inventory: dict[str, Any], save: bool = True) -> dict[str, Any]:
    """Generate checksums from a caller-provided inventory to avoid repeated full-tree scans."""
    checksums = []
    for row in inventory.get("included", []):
        path = ROOT_DIR / row["path"]
        if path.exists() and path.is_file():
            checksums.append({"path": row["path"], "sha256": _sha256_file(path), "size": path.stat().st_size, "category": "included"})
    rows = [
        {"name": "checksum-count", "status": "pass" if len(checksums) == inventory.get("included_count") else "blocked", "message": f"{len(checksums)} checksum(s) for {inventory.get('included_count')} included files."},
        {"name": "inventory-ok", "status": "pass" if inventory.get("ok") else "blocked", "message": inventory.get("message", "inventory missing")},
    ]
    status = _status_from(rows)
    report = {
        "version": RELEASE_PACKAGING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "checksum_count": len(checksums),
        "checksums": checksums,
        "rows": rows,
        "message": "Package checksums generated for included release files.",
    }
    if save:
        _write_json(PACKAGE_CHECKSUMS, report)
    else:
        report["preview_only"] = True
    return report


def _readme_section(version: str) -> str:
    readme = ROOT_DIR / "README_NEXT_STEPS.md"
    text = readme.read_text(encoding="utf-8", errors="replace") if readme.exists() else ""
    idx = text.find(f"v{version}")
    if idx < 0:
        return ""
    return text[max(0, idx - 200): idx + 3000]


def build_release_notes(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v19.4: generate release notes from README and release metadata."""
    version = _current_version()
    section = _readme_section(version)
    commands = [
        "--release-manifest-integrity",
        "--package-inventory",
        "--package-checksums",
        "--release-notes",
        "--release-handoff-report",
        "--build-release-zip",
        "--verify-release-unzip",
        "--release-pipeline-audit",
        "--verified-release-package-loop",
    ]
    rows = [
        {"name": "readme-section", "status": "pass" if section else "warn", "message": f"README section for v{version} found." if section else f"README section for v{version} not found."},
        {"name": "command-count", "status": "pass", "message": f"{len(commands)} release packaging command(s) listed."},
    ]
    status = _status_from(rows)
    report = {
        "version": RELEASE_PACKAGING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "release_version": version,
        "title": f"Eidolon v{version} Release Notes",
        "major_changes": [
            "Verified release package loop with manifest integrity checks.",
            "Package inventory and checksum reports.",
            "Release notes and handoff report generation.",
            "Guarded zip builder and unzip verification previews.",
            "Release dashboard/package review surface.",
        ],
        "new_commands": commands,
        "known_warnings": [
            "Ollama health depends on the local service running.",
            "chromadb must be installed from requirements.txt for semantic memory features.",
        ],
        "readme_excerpt": section[:2500],
        "rows": rows,
        "message": "Release notes generated from README and v20 packaging metadata.",
    }
    if save:
        _write_json(RELEASE_NOTES, report)
    else:
        report["preview_only"] = True
    return report


def build_release_handoff_report(project_id: str = "eidolon", package_name: str | None = None, save: bool = True) -> dict[str, Any]:
    """v19.5: generate final handoff report for the packaged release."""
    manifest = build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=False)
    inventory = build_package_inventory(project_id=project_id, save=False)
    checksums = _build_package_checksums_from_inventory(project_id=project_id, inventory=inventory, save=False)
    notes = build_release_notes(project_id=project_id, save=False)
    return _build_release_handoff_report_from_parts(project_id=project_id, package_name=package_name, manifest=manifest, inventory=inventory, checksums=checksums, notes=notes, save=save)


def _build_release_handoff_report_from_parts(
    project_id: str,
    package_name: str | None,
    manifest: dict[str, Any],
    inventory: dict[str, Any],
    checksums: dict[str, Any],
    notes: dict[str, Any],
    save: bool = True,
) -> dict[str, Any]:
    """Build the handoff report from already-computed release reports."""
    readiness = _read_json(RELEASE_READINESS, {}) or {"status": "warn", "ok": True, "message": "Release readiness has not been saved yet; run --release-readiness or --doctor before final handoff."}
    approval = _read_json(APPROVAL_STATE, {})
    rows = [
        {"name": "manifest", "status": "pass" if manifest.get("ok") else "blocked", "message": manifest.get("message")},
        {"name": "inventory", "status": "pass" if inventory.get("ok") else "blocked", "message": inventory.get("message")},
        {"name": "checksums", "status": "pass" if checksums.get("ok") else "blocked", "message": checksums.get("message")},
        {"name": "release-notes", "status": "pass" if notes.get("ok") else "warn", "message": notes.get("message")},
        {"name": "release-readiness", "status": "pass" if readiness.get("ok") else "warn", "message": readiness.get("message")},
        {"name": "approval-neutral", "status": "pass" if not approval.get("approved") else "warn", "message": "Packaged handoff should not include a live unconsumed approval."},
    ]
    status = _status_from(rows)
    report = {
        "version": RELEASE_PACKAGING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "release_version": _current_version(),
        "package_name": package_name or _package_name(),
        "manifest_status": manifest.get("status"),
        "checksums_status": checksums.get("status"),
        "readme_status": next((r.get("status") for r in manifest.get("rows", []) if r.get("name") == "readme-section"), "unknown"),
        "approval_state": {"approved": bool(approval.get("approved")), "status": approval.get("status", "missing")},
        "known_warnings": [r.get("message") for r in rows if r.get("status") == "warn"],
        "commands_tested": [
            "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
            "python conscious_agent/main.py --verified-release-package-loop",
            "python -u tools/smoke_check.py",
        ],
        "recommended_first_commands_after_unzip": [
            "python -m pip install -r requirements.txt",
            "python conscious_agent/main.py --doctor",
            "python conscious_agent/main.py --release-manifest-integrity",
            "python -u tools/smoke_check.py",
        ],
        "rows": rows,
        "message": "Release handoff report prepared for the verified package.",
    }
    if save:
        _write_json(RELEASE_HANDOFF_REPORT, report)
    else:
        report["preview_only"] = True
    return report


def build_release_zip(project_id: str = "eidolon", package_name: str | None = None, confirm: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v19.6: guarded zip builder."""
    package_name = package_name or _package_name()
    manifest = build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=False)
    inventory = build_package_inventory(project_id=project_id, save=False)
    checksums = _build_package_checksums_from_inventory(project_id=project_id, inventory=inventory, save=False)
    notes = build_release_notes(project_id=project_id, save=False)
    handoff = _build_release_handoff_report_from_parts(project_id=project_id, package_name=package_name, manifest=manifest, inventory=inventory, checksums=checksums, notes=notes, save=False)
    return _build_release_zip_from_parts(project_id=project_id, package_name=package_name, manifest=manifest, inventory=inventory, checksums=checksums, handoff=handoff, confirm=confirm, dry_run=dry_run, save=save)


def _build_release_zip_from_parts(
    project_id: str,
    package_name: str,
    manifest: dict[str, Any],
    inventory: dict[str, Any],
    checksums: dict[str, Any],
    handoff: dict[str, Any],
    confirm: bool = False,
    dry_run: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """Build or preview a release zip from caller-provided package reports."""
    rows = [
        {"name": "manifest", "status": "pass" if manifest.get("ok") else "blocked", "message": manifest.get("message")},
        {"name": "inventory", "status": "pass" if inventory.get("ok") else "blocked", "message": inventory.get("message")},
        {"name": "checksums", "status": "pass" if checksums.get("ok") else "blocked", "message": checksums.get("message")},
        {"name": "handoff", "status": "pass" if handoff.get("ok") else "blocked", "message": handoff.get("message")},
        {"name": "explicit-confirm", "status": "pass" if dry_run or confirm else "blocked", "message": "Real zip build requires --confirm."},
    ]
    status = _status_from(rows)
    target = RELEASES_DIR / package_name
    built = False
    if status != "blocked" and confirm and not dry_run:
        _ensure_dirs()
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for row in inventory.get("included", []):
                src = ROOT_DIR / row["path"]
                if src.exists() and src.is_file():
                    archive.write(src, arcname=f"Eidolon/{row['path']}")
        built = True
    report = {
        "version": RELEASE_PACKAGING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "built" if built else "dry_run" if status != "blocked" else "blocked",
        "ok": status != "blocked",
        "dry_run": dry_run or not confirm,
        "package_name": package_name,
        "zip_path": str(target) if built else None,
        "included_count": inventory.get("included_count"),
        "rows": rows,
        "message": "Source-only release zip built." if built else "Source-only release zip dry-run completed; no archive written." if status != "blocked" else "Release zip blocked by prechecks.",
    }
    if save:
        _write_json(BUILD_RELEASE_ZIP, report)
        if built:
            _timeline_event("release_zip_built", {"project_id": project_id, "package_name": package_name, "zip_path": str(target)}, save=True)
    else:
        report["preview_only"] = True
    return report


def build_verify_release_unzip(project_id: str = "eidolon", package_name: str | None = None, save: bool = True) -> dict[str, Any]:
    """v19.7: verify a release zip after extraction."""
    package_name = package_name or _package_name()
    target = RELEASES_DIR / package_name
    rows: list[dict[str, Any]] = []
    if not target.exists():
        rows.append({"name": "zip-exists", "status": "warn", "message": f"{target} does not exist yet; run --build-release-zip --confirm to create it."})
        status = _status_from(rows)
        report = {"version": RELEASE_PACKAGING_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": True, "package_name": package_name, "rows": rows, "message": "No release zip found yet; unzip verification is pending."}
        if save:
            _write_json(VERIFY_RELEASE_UNZIP, report)
        else:
            report["preview_only"] = True
        return report
    temp_dir = RELEASE_PACKAGE_DIR / "unzip_verify_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(target, "r") as archive:
            archive.extractall(temp_dir)
        extracted_root = temp_dir / "Eidolon"
        main_py = extracted_root / "conscious_agent" / "main.py"
        rows.extend([
            {"name": "zip-exists", "status": "pass", "message": str(target)},
            {"name": "extracts", "status": "pass" if extracted_root.exists() else "blocked", "message": "Archive extracted to temporary verification folder."},
            {"name": "main-py", "status": "pass" if main_py.exists() else "blocked", "message": "main.py exists after extraction."},
            {"name": "readme", "status": "pass" if (extracted_root / "README_NEXT_STEPS.md").exists() else "blocked", "message": "README exists after extraction."},
            {"name": "approval-neutral", "status": "pass" if not (extracted_root / "data" / "patch_drafts" / "approval_state.json").exists() else "blocked", "message": "Live approval state is not packaged."},
            {"name": "runtime-data-excluded", "status": "pass" if not any((extracted_root / item).exists() for item in ["data/chroma", "data/chat_actions", "data/dashboard_chat", "data/backups", "data/code_patches", "data/memories.json"]) else "blocked", "message": "Private/runtime data folders are absent after extraction."},
            {"name": "portable-root", "status": "pass" if "/mnt/data" not in json.dumps([str(p.relative_to(extracted_root)).replace(os.sep, "/") for p in extracted_root.rglob('*')][:200]) else "warn", "message": "Portable path check completed."},
        ])
    except Exception as error:
        rows.append({"name": "extracts", "status": "blocked", "message": str(error)})
    finally:
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass
    status = _status_from(rows)
    report = {"version": RELEASE_PACKAGING_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": status != "blocked", "package_name": package_name, "rows": rows, "message": "Release unzip verification completed."}
    if save:
        _write_json(VERIFY_RELEASE_UNZIP, report)
    else:
        report["preview_only"] = True
    return report


def _cached_release_artifact(path: Path, message: str) -> dict[str, Any]:
    cached = _read_json(path, {})
    if isinstance(cached, dict) and cached:
        return cached
    return {"status": "warn", "ok": True, "message": message}


def build_release_pipeline_audit(project_id: str = "eidolon", package_name: str | None = None, save: bool = True) -> dict[str, Any]:
    """v19.9/v21.0: audit the approval-to-package chain without rebuilding heavyweight AI review artifacts during dashboard/package checks."""
    bundle = _cached_release_artifact(AI_PATCH_REVIEW_BUNDLE, "Review bundle has not been saved yet; refresh it before approving a generated patch.")
    integrity = _cached_release_artifact(REVIEW_BUNDLE_INTEGRITY, "Review bundle integrity has not been saved yet; run --ai-patch-review-integrity before approval.")
    ready = _cached_release_artifact(APPROVAL_READY, "Approval-ready gate has not been saved yet; run --approval-ready before applying a generated patch.")
    post_apply = _cached_release_artifact(POST_APPLY_REVIEW, "No real post-apply review exists in this packaged handoff state.")
    readiness = _read_json(RELEASE_READINESS, {}) or {"status": "warn", "ok": True, "message": "Release readiness has not been saved yet; run --release-readiness or --doctor before final handoff."}
    manifest = build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=False)
    inventory = build_package_inventory(project_id=project_id, save=False)
    checksums = _build_package_checksums_from_inventory(project_id=project_id, inventory=inventory, save=False)
    notes = build_release_notes(project_id=project_id, save=False)
    handoff = _build_release_handoff_report_from_parts(project_id=project_id, package_name=package_name, manifest=manifest, inventory=inventory, checksums=checksums, notes=notes, save=False)
    zip_plan = _build_release_zip_from_parts(project_id=project_id, package_name=package_name or _package_name(), manifest=manifest, inventory=inventory, checksums=checksums, handoff=handoff, confirm=False, dry_run=True, save=False)
    return _build_release_pipeline_audit_from_parts(project_id=project_id, package_name=package_name, bundle=bundle, integrity=integrity, ready=ready, post_apply=post_apply, readiness=readiness, manifest=manifest, checksums=checksums, handoff=handoff, zip_plan=zip_plan, save=save)


def _build_release_pipeline_audit_from_parts(
    project_id: str,
    package_name: str | None,
    bundle: dict[str, Any],
    integrity: dict[str, Any],
    ready: dict[str, Any],
    post_apply: dict[str, Any],
    readiness: dict[str, Any],
    manifest: dict[str, Any],
    checksums: dict[str, Any],
    handoff: dict[str, Any],
    zip_plan: dict[str, Any],
    save: bool = True,
) -> dict[str, Any]:
    """Audit the approval-to-package chain from already-computed reports."""
    rows = [
        {"name": "draft-approval-binding", "status": "pass" if bundle.get("manifest") else "warn", "message": "Review bundle contains a validated manifest."},
        {"name": "validated-manifest-binding", "status": "pass" if integrity.get("ok") else "warn", "message": integrity.get("message")},
        {"name": "approval-ready", "status": "pass" if ready.get("ok") else "warn", "message": ready.get("message")},
        {"name": "post-apply-review", "status": "pass" if post_apply.get("ok") else "warn", "message": post_apply.get("message")},
        {"name": "release-readiness", "status": "pass" if readiness.get("ok") else "warn", "message": readiness.get("message")},
        {"name": "manifest-integrity", "status": "pass" if manifest.get("ok") else "blocked", "message": manifest.get("message")},
        {"name": "checksums", "status": "pass" if checksums.get("ok") else "blocked", "message": checksums.get("message")},
        {"name": "handoff", "status": "pass" if handoff.get("ok") else "blocked", "message": handoff.get("message")},
        {"name": "zip-builder", "status": "pass" if zip_plan.get("ok") else "blocked", "message": zip_plan.get("message")},
    ]
    status = _status_from(rows)
    report = {"version": RELEASE_PACKAGING_VERSION, "checked_at": _now(), "project_id": project_id, "status": status, "ok": status != "blocked", "package_name": package_name or _package_name(), "rows": rows, "message": "Release pipeline audit completed across approval, readiness, manifest, checksum, handoff, and zip prechecks."}
    if save:
        _write_json(RELEASE_PIPELINE_AUDIT, report)
    else:
        report["preview_only"] = True
    return report


def build_verified_release_package_loop(project_id: str = "eidolon", package_name: str | None = None, confirm: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v20.0: prepare a complete verified release package from the approved release state."""
    package_name = package_name or _package_name()
    manifest = build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=save)
    inventory = build_package_inventory(project_id=project_id, save=save)
    checksums = _build_package_checksums_from_inventory(project_id=project_id, inventory=inventory, save=save)
    notes = build_release_notes(project_id=project_id, save=save)
    handoff = _build_release_handoff_report_from_parts(project_id=project_id, package_name=package_name, manifest=manifest, inventory=inventory, checksums=checksums, notes=notes, save=save)
    bundle = _cached_release_artifact(AI_PATCH_REVIEW_BUNDLE, "Review bundle has not been saved yet; refresh it before approving a generated patch.")
    integrity = _cached_release_artifact(REVIEW_BUNDLE_INTEGRITY, "Review bundle integrity has not been saved yet; run --ai-patch-review-integrity before approval.")
    ready = _cached_release_artifact(APPROVAL_READY, "Approval-ready gate has not been saved yet; run --approval-ready before applying a generated patch.")
    post_apply = _cached_release_artifact(POST_APPLY_REVIEW, "No real post-apply review exists in this packaged handoff state.")
    readiness = _read_json(RELEASE_READINESS, {}) or {"status": "warn", "ok": True, "message": "Release readiness has not been saved yet; run --release-readiness or --doctor before final handoff."}
    zip_report = _build_release_zip_from_parts(project_id=project_id, package_name=package_name, manifest=manifest, inventory=inventory, checksums=checksums, handoff=handoff, confirm=confirm, dry_run=dry_run or not confirm, save=save)
    audit = _build_release_pipeline_audit_from_parts(project_id=project_id, package_name=package_name, bundle=bundle, integrity=integrity, ready=ready, post_apply=post_apply, readiness=readiness, manifest=manifest, checksums=checksums, handoff=handoff, zip_plan=zip_report, save=save)
    unzip = build_verify_release_unzip(project_id=project_id, package_name=package_name, save=save)
    blocked = [name for name, report in {
        "manifest": manifest,
        "inventory": inventory,
        "checksums": checksums,
        "handoff": handoff,
        "audit": audit,
        "zip": zip_report,
    }.items() if isinstance(report, dict) and report.get("ok") is False]
    status = "blocked" if blocked else "package_built" if confirm and not dry_run and zip_report.get("status") == "built" else "dry_run"
    report = {
        "version": RELEASE_PACKAGING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "dry_run": dry_run or not confirm,
        "package_name": package_name,
        "steps": {
            "manifest_integrity": manifest,
            "inventory": inventory,
            "checksums": checksums,
            "release_notes": notes,
            "handoff": handoff,
            "pipeline_audit": audit,
            "zip_builder": zip_report,
            "unzip_verification": unzip,
        },
        "blocked_steps": blocked,
        "message": "Verified release package loop completed and stopped.",
    }
    if save:
        _write_json(VERIFIED_RELEASE_PACKAGE_LOOP, report)
        _timeline_event("verified_release_package_loop", {"project_id": project_id, "status": status, "package_name": report.get("package_name"), "dry_run": report.get("dry_run")}, save=True)
    else:
        report["preview_only"] = True
    return report


def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# {title}",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at', '')}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Message: {report.get('message', '')}",
    ]
    if report.get("package_name"):
        lines.append(f"Package: {report.get('package_name')}")
    rows = report.get("rows") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:100]:
            lines.append(f"- {str(row.get('status', 'info')).upper()} {row.get('name') or row.get('path')}: {row.get('message') or row.get('reason', '')}")
    if report.get("blocked_steps"):
        lines.extend(["", "## Blocked Steps"])
        lines.extend([f"- {item}" for item in report.get("blocked_steps", [])])
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def release_manifest_integrity_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.1 Release Manifest Integrity", report or build_release_manifest_integrity(save=False), full)


def package_inventory_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.2 Package Inventory", report or build_package_inventory(save=False), full)


def package_checksums_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.3 Package Checksums", report or build_package_checksums(save=False), full)


def release_notes_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.4 Release Notes", report or build_release_notes(save=False), full)


def release_handoff_report_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.5 Release Handoff Report", report or build_release_handoff_report(save=False), full)


def build_release_zip_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.6 Guarded Zip Builder", report or build_release_zip(save=False), full)


def verify_release_unzip_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.7 Verify Release Unzip", report or build_verify_release_unzip(save=False), full)


def release_pipeline_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.9 Release Pipeline Audit", report or build_release_pipeline_audit(save=False), full)


def verified_release_package_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v21.0 Verified Release Package Loop", report or build_verified_release_package_loop(save=False), full)


def print_release_manifest_integrity(project_id: str = "eidolon", package_name: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=True)
    _json_print(report) if json_output else print(release_manifest_integrity_text(report, full))


def print_package_inventory(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_package_inventory(project_id=project_id, save=True)
    _json_print(report) if json_output else print(package_inventory_text(report, full))


def print_package_checksums(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_package_checksums(project_id=project_id, save=True)
    _json_print(report) if json_output else print(package_checksums_text(report, full))


def print_release_notes(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_notes(project_id=project_id, save=True)
    _json_print(report) if json_output else print(release_notes_text(report, full))


def print_release_handoff_report(project_id: str = "eidolon", package_name: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_handoff_report(project_id=project_id, package_name=package_name, save=True)
    _json_print(report) if json_output else print(release_handoff_report_text(report, full))


def print_build_release_zip(project_id: str = "eidolon", package_name: str | None = None, confirm: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_release_zip(project_id=project_id, package_name=package_name, confirm=confirm, dry_run=dry_run or not confirm, save=True)
    _json_print(report) if json_output else print(build_release_zip_text(report, full))


def print_verify_release_unzip(project_id: str = "eidolon", package_name: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_verify_release_unzip(project_id=project_id, package_name=package_name, save=True)
    _json_print(report) if json_output else print(verify_release_unzip_text(report, full))


def print_release_pipeline_audit(project_id: str = "eidolon", package_name: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_pipeline_audit(project_id=project_id, package_name=package_name, save=True)
    _json_print(report) if json_output else print(release_pipeline_audit_text(report, full))


def print_verified_release_package_loop(project_id: str = "eidolon", package_name: str | None = None, confirm: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_verified_release_package_loop(project_id=project_id, package_name=package_name, confirm=confirm, dry_run=dry_run or not confirm, save=True)
    _json_print(report) if json_output else print(verified_release_package_loop_text(report, full))
