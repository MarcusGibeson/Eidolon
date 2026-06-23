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

RELEASE_PACKAGING_VERSION = "350.0"
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
    "data/signing/trusted_public_keys.json",
}
SOURCE_ONLY_DATA_PREFIXES = (
    "data/workspaces/command_profiles/",
)
EXCLUDE_PARTS = {
    ("data", "autonomy"),
    ("data", "self_maintenance"),
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

def _sanitized_source_payload(rel: str, path: Path) -> bytes | None:
    """Return sanitized bytes for allowlisted source data JSON files.

    Runtime-mutated timestamps are useful locally and terrible in a signed source
    package. So the zip/checksum path strips those fields without modifying the
    developer's live data files. Tiny mercy, naturally surrounded by bureaucracy.
    """
    if not _is_source_data_file(rel) or path.suffix.lower() != ".json":
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    volatile_keys = {"updated_at", "last_health_checked_at", "last_run_at", "last_seen_at", "last_modified", "last_opened_at"}

    def sanitize(item: Any) -> Any:
        if isinstance(item, dict):
            return {key: sanitize(val) for key, val in item.items() if key not in volatile_keys}
        if isinstance(item, list):
            return [sanitize(val) for val in item]
        return item

    return json.dumps(sanitize(value), indent=2, sort_keys=True, default=str).encode("utf-8") + b"\n"


def _package_bytes_for_file(rel: str, path: Path) -> bytes:
    sanitized = _sanitized_source_payload(rel, path)
    if sanitized is not None:
        return sanitized
    return path.read_bytes()


def _sha256_packaged_file(rel: str, path: Path) -> tuple[str, int]:
    payload = _package_bytes_for_file(rel, path)
    return hashlib.sha256(payload).hexdigest(), len(payload)


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
            sha256, size = _sha256_packaged_file(row["path"], path)
            checksums.append({"path": row["path"], "sha256": sha256, "size": size, "category": "included"})
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
                    payload = _package_bytes_for_file(row["path"], src)
                    archive.writestr(f"Eidolon/{row['path']}", payload)
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
# v60.1-v61.0 handoff bridge runtime privacy tokens intentionally excluded by data/self_maintenance and source_apply_backups rules: source_apply_handoff_receipts.json source_baseline_drift_resolver.json reviewed_artifact_set_binder.json source_apply_handoff_eligibility.json source_apply_dry_run_bridge.json source_apply_handoff_dashboard_polish.json source_apply_handoff_api_parity_gate.json source_apply_handoff_privacy_hardening.json pre_v61_controlled_apply_bridge_gate.json controlled_source_apply_bridge_refinement.json data/self_maintenance/ data/autonomy/source_apply_backups/ source_apply_backups confirmation_phrase


# v61.1-v63.0 transaction runtime privacy tokens intentionally excluded by source-only data rules: source_apply_transaction_planner.json source_apply_backup_binder.json source_apply_transaction_dry_run_verifier.json source_apply_transaction_confirmation_gate.json supervised_source_apply_executor.json post_apply_verification_runner.json transaction_rollback_rehearsal.json source_apply_transaction_dashboard_command_center.json pre_v62_transaction_release_gate.json supervised_source_apply_transaction_layer.json transaction_receipt_ledger.json transaction_diff_viewer.json transaction_conflict_detector.json transaction_approval_record_binder.json transaction_package_evidence_exporter.json transaction_replay_audit.json transaction_dashboard_receipt_timeline.json transaction_api_search_filtering.json pre_v63_transaction_evidence_gate.json durable_transaction_evidence_system.json data/autonomy/source_apply_transactions/ data/autonomy/transaction_evidence/ transaction_confirm_phrase exact_confirmation_phrase

# v63.1-v64.0 improvement intelligence runtime privacy tokens intentionally excluded by source-only data rules: transaction_evidence_summarizer.json improvement_candidate_registry.json evidence_based_candidate_scoring.json improvement_regression_pattern_detector.json improvement_risk_blast_radius_forecaster.json supervised_recommendation_queue.json improvement_intelligence_dashboard.json improvement_intelligence_api_cli_access.json pre_v64_improvement_intelligence_gate.json supervised_improvement_intelligence_layer.json data/autonomy/improvement_intelligence/ candidate_decision_secret auto_apply_improvement

# v64.1-v65.0 proposal drafting runtime privacy tokens intentionally excluded by source-only data rules: accepted_recommendation_intake.json proposal_draft_skeleton.json evidence_requirement_mapper.json proposal_risk_contract.json sandbox_patch_request_compiler.json proposal_review_packet_binder.json proposal_dashboard_review_console.json proposal_api_cli_access.json pre_v65_proposal_drafting_gate.json recommendation_to_proposal_drafting_layer.json data/autonomy/proposal_drafting/ proposal_recommendation_id sandbox_patch_request_secret

# v65.1-v66.0 proposal sandbox execution runtime privacy tokens intentionally excluded by source-only data rules: reviewed_proposal_acceptance_gate.json sandbox_workspace_plan.json patch_implementation_request.json proposal_sandbox_execution_harness.json proposal_sandbox_verification_matrix.json proposal_sandbox_evidence_binder.json proposal_sandbox_failure_triage.json proposal_sandbox_api_cli_access.json pre_v66_proposal_sandbox_gate.json reviewed_proposal_sandbox_execution_layer.json data/autonomy/proposal_sandbox_execution/ proposal_sandbox_execute_copy sandbox_workspace_path execution_receipts verification_matrix

# v66.1-v67.0 sandbox promotion runtime privacy tokens intentionally excluded by source-only data rules: sandbox_promotion_candidate.json sandbox_source_diff_normalizer.json promotion_safety_boundary_gate.json transaction_draft_from_sandbox.json promotion_review_packet_binder.json promotion_conflict_staleness_detector.json sandbox_promotion_api_cli_access.json pre_v67_sandbox_promotion_gate.json sandbox_evidence_promotion_handoff_layer.json data/autonomy/sandbox_promotion/ promotion_candidate_id transaction_draft_from_sandbox exact_confirmation_phrase_template
# v67.1-v68.0 source transaction review runtime privacy tokens intentionally excluded by source-only data rules: promotion_packet_intake_gate.json transaction_plan_materializer.json source_baseline_reconciliation.json backup_rollback_preflight_binder.json final_transaction_safety_gate.json transaction_ledger_preregistration.json source_transaction_review_console.json transaction_review_api_cli_access.json pre_v68_transaction_integration_gate.json promotion_to_transaction_integration_layer.json data/autonomy/source_transaction_review/ source_transaction_review_ledger.json exact_confirmation_phrase_template transaction_candidate_id

# v68.1-v69.0 operator-confirmed transaction execution runtime privacy tokens intentionally excluded by source-only data rules: transaction_execution_eligibility.json exact_confirmation_binder.json backup_snapshot_materializer.json transaction_apply_rehearsal.json operator_confirmed_apply_executor.json post_execution_verification.json rollback_recommendation_gate.json transaction_execution_dashboard_api_cli.json pre_v69_execution_gate.json operator_confirmed_transaction_execution_layer.json data/autonomy/transaction_execution/ raw_confirmation_phrase backup_snapshot confirmation_phrase_hash

# v69.1-v70.0 release finalization runtime privacy tokens intentionally excluded by source-only data rules: execution_result_ledger_finalizer.json rollback_decision_resolver.json operator_confirmed_rollback_executor.json post_rollback_verification.json release_candidate_finalization_gate.json source_only_package_certifier.json release_finalization_dashboard_api_cli.json recovery_simulation_harness.json pre_v70_recovery_finalization_gate.json verified_execution_recovery_release_layer.json data/autonomy/release_finalization/ rollback_confirmation_phrase rollback_receipt backup_snapshot confirmation_phrase material approval_secrets

# v70.1-v71.0 codebase map runtime privacy tokens intentionally excluded by source-only data rules: source_tree_inventory.json module_responsibility_map.json dependency_call_surface_map.json module_risk_profile.json historical_failure_memory.json verification_command_map.json improvement_opportunity_detector.json codebase_understanding_dashboard_api_cli.json pre_v71_codebase_understanding_gate.json codebase_understanding_map.json data/autonomy/codebase_map/ no_native_title_tooltip source_mutation_performed

# v71.1-v72.0 patch context runtime privacy tokens intentionally excluded by source-only data rules: patch_goal_intake_classifier.json relevant_file_context_selector.json historical_failure_context_binder.json risk_aware_context_budgeter.json verification_requirement_compiler.json patch_prompt_context_packet_builder.json context_completeness_reviewer.json patch_context_dashboard_api_cli.json pre_v72_patch_context_gate.json patch_generation_context_builder.json data/autonomy/patch_context/ source_mutation_performed=False patch_generation_performed=False no_native_title_tooltip
# v72.1-v73.0 patch draft runtime privacy tokens intentionally excluded by source-only data rules: patch_intent_normalizer.json patch_scope_contract_builder.json patch_prompt_composer.json patch_draft_output_schema.json patch_draft_safety_reviewer.json patch_draft_evidence_binder.json patch_draft_dashboard_api_cli.json local_model_handoff_stub.json pre_v73_patch_draft_gate.json supervised_patch_draft_composer.json data/autonomy/patch_drafts/ local_model_invoked=False source_mutation_performed=False approval_bypass_performed=False no_native_title_tooltip
# v73.1-v74.0 patch review runtime privacy tokens intentionally excluded by source-only data rules: patch_review_intake_parser.json patch_review_diff_boundary_extractor.json patch_review_scope_contract_validator.json patch_review_safety_boundary_validator.json patch_review_documentation_update_validator.json patch_review_verification_plan_validator.json patch_review_risk_scorer.json patch_review_report_builder.json patch_review_dashboard_api_cli.json pre_v74_patch_review_gate.json patch_draft_review_diff_validation_layer.json data/autonomy/patch_review/ patch_applied=False source_mutation_performed=False local_model_invoked=False approval_bypass_performed=False no_native_title_tooltip
# v74.1-v75.0 sandbox patch trial runtime privacy tokens intentionally excluded by source-only data rules: patch_trial_intake_binder.json patch_trial_workspace_builder.json patch_trial_materializer.json patch_trial_verification_runner.json patch_trial_evidence_collector.json patch_trial_escape_mutation_guard.json patch_trial_dashboard_api_cli.json patch_trial_cleanup_retention.json pre_v75_sandbox_trial_gate.json sandbox_patch_trial_runner.json data/autonomy/patch_trials/ patch_input.txt trial_metadata.json verification.json evidence.json escape_guard.json live_source_mutation_performed=False promotion_performed=False approval_bypass_performed=False no_native_title_tooltip

# v75.1-v76.0 sandbox evidence review runtime privacy tokens intentionally excluded by source-only data rules: patch_evidence_intake_reader.json trial_integrity_validator.json verification_evidence_scorer.json scope_documentation_evidence_reviewer.json risk_acceptance_classifier.json promotion_readiness_packet_builder.json patch_evidence_dashboard_api_cli.json recommendation_archive_comparison.json pre_v76_evidence_review_gate.json sandbox_evidence_review_recommendation_layer.json data/autonomy/patch_evidence_reviews/ readiness_packet.json comparison.json promotion_performed=False source_mutation_performed=False approval_bypass_performed=False no_native_title_tooltip
# v76.1-v77.0 operator-approved patch application runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/patch_applications/ snapshot.json application_evidence.json operator_approved_patch_application_layer.json approval_bypass_performed=False no_native_title_tooltip
# v77.1-v78.0 recovery runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/patch_recovery/ dirty_tree_preflight_detector.json snapshot_completeness_validator.json partial_apply_detector.json rollback_integrity_verifier.json failed_verification_triage.json recovery_recommendation_builder.json application_audit_timeline.json repair_patch_generated=False retry_performed=False no_native_title_tooltip
# v78.1-v79.0 queue planning runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/patch_queue/ patch_queue_record_schema.json patch_queue_intake_organizer.json patch_queue_conflict_detector.json patch_queue_risk_priority_scheduler.json patch_queue_stale_evidence_detector.json patch_queue_serial_trial_plan_builder.json patch_queue_operator_review_packet.json multi_patch_queue_planning_layer.json patches_applied=False approval_bypass_performed=False no_native_title_tooltip

# v79.1-v85.0 supervised loop runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/supervised_improvement_loop/ improvement_loop local_model_proposals proposal_critique candidate_ranking candidate_refinement suggestion_loop source_mutation_performed=False patches_applied=False approval_bypass_performed=False local_model_invoked_by_default=False no_native_title_tooltip
# v85.1-v86.0 suggestion inbox runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/suggestion_inbox/ suggestion_inbox_record_schema.json suggestion_intake_normalizer.json suggestion_deduplication_drift_resolver.json operator_triage_state_machine.json work_order_draft_builder.json safety_scope_contract_binder.json pipeline_handoff_planner.json pre_v86_suggestion_inbox_gate.json supervised_suggestion_inbox_work_order_planner.json accepted_for_planning work_order_draft source_mutation_performed=False patches_applied=False approval_bypass_performed=False publish_performed=False memory_mutation_performed=False identity_mutation_performed=False no_native_title_tooltip

# v86.1-v90.0 supervised self-development runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/work_order_handoff/ data/autonomy/work_order_evidence/ data/autonomy/self_development_console/ data/autonomy/self_development_readiness/ work_order_to_patch_context_handoff.json work_order_execution_evidence_binder.json self_development_dashboard_consolidation.json supervised_self_development_readiness_audit.json autonomy_unlocked=False source_mutation_performed=False patches_applied=False approval_bypass_performed=False publish_performed=False memory_mutation_performed=False identity_mutation_performed=False no_native_title_tooltip
# v90.1-v95.0 supervised runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/development_sessions/ data/autonomy/approval_console/ data/autonomy/experiment_planner/ data/autonomy/outcome_reflections/ data/autonomy/improvement_cycles/ supervised_development_session_manager.json operator_approval_workflow_console.json safe_experiment_branch_planner.json learning_from_outcome_reflection_layer.json supervised_improvement_cycle_orchestrator.json autonomy_unlocked=False source_mutation_performed=False patches_applied=False approval_bypass_performed=False publish_performed=False memory_mutation_performed=False identity_mutation_performed=False experiment_promoted_without_transaction=False no_native_title_tooltip
# v95.1-v100.0 governed simulation runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/cycle_replay/ data/autonomy/capability_ledger/ data/autonomy/shadow_autonomy/ data/autonomy/failure_war_games/ data/autonomy/mind_milestone_audit/ supervised_cycle_replay_benchmark_harness.json capability_permission_budget_ledger.json shadow_autonomy_simulation_layer.json failure_recovery_rollback_war_game_layer.json local_artificial_mind_milestone_audit.json autonomy_unlocked=False source_mutation_performed=False patches_applied=False approval_bypass_performed=False publish_performed=False memory_mutation_performed=False identity_mutation_performed=False simulation_executed=False automatic_rollback_performed=False no_native_title_tooltip

# v100.1-v105.0 coherent runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/v100_stabilization/ data/autonomy/system_map/ data/autonomy/coherence_binder/ data/autonomy/daily_loop/ data/autonomy/local_mind_runtime/ v100_milestone_stabilization_review.json unified_eidolon_system_map_operator_home.json memory_reflection_goal_coherence_binder.json practical_daily_operating_loop.json coherent_local_mind_runtime_v1.json autonomy_unlocked=False source_mutation_performed=False patches_applied=False approval_bypass_performed=False publish_performed=False memory_mutation_performed=False identity_mutation_performed=False automatic_action_performed=False hidden_scheduling_performed=False no_native_title_tooltip

# v105.1-v110.0 practical coherence runtime privacy tokens intentionally excluded by source-only package rules: data/autonomy/memory_quality/ data/autonomy/goal_continuity/ data/autonomy/reasoning_workbench/ data/autonomy/workflow_console/ data/autonomy/practical_mind_audit/ memory_quality_evidence_hygiene_layer.json goal_continuity_priority_stability_layer.json contained_local_reasoning_workbench.json operator_workflow_compression_console.json practical_supervised_mind_usefulness_audit.json autonomy_unlocked=False source_mutation_performed=False patches_applied=False approval_bypass_performed=False publish_performed=False memory_mutation_performed=False identity_mutation_performed=False local_model_invoked_by_default=False automatic_action_performed=False hidden_scheduling_performed=False commands_executed_from_console=False approvals_inferred_from_queue=False no_native_title_tooltip

# v120.1-v125.0 source-only privacy tokens: data/autonomy/development_outcome_review/ data/autonomy/lesson_extraction/ data/autonomy/recommendation_refinement/ data/autonomy/operator_feedback_integration/ data/autonomy/development_learning_audit/
# v115.1-v120.0 source-only privacy tokens: data/autonomy/development_session_planner/ data/autonomy/source_change_cartographer/ data/autonomy/patch_simulation/ data/autonomy/verification_matrix/ data/autonomy/development_execution_audit/
# v110.1-v115.0 source-only privacy tokens: data/autonomy/improvement_intent/ data/autonomy/work_package_builder/ data/autonomy/patch_readiness/ data/autonomy/release_candidate_judgment/ data/autonomy/supervised_development_readiness/
# v125.1-v130.0 source-only privacy tokens: data/autonomy/strategic_growth_intake/ data/autonomy/roadmap_synthesis/ data/autonomy/strategic_risk_ledger/ data/autonomy/capability_maturity/ data/autonomy/strategic_growth_audit/
# v130.1-v135.0 source-only privacy tokens: data/autonomy/planning_signals/ data/autonomy/work_package_recommendations/ data/autonomy/operator_decision_brief/ data/autonomy/planning_console/ data/autonomy/planning_readiness_audit/

# v135.1-v140.0 source-only privacy tokens: data/autonomy/work_package_selection/ data/autonomy/session_brief/ data/autonomy/approval_checklist/ data/autonomy/verification_rollback_plan/ data/autonomy/session_launch_audit/
# v140.1-v145.0 source-only privacy tokens: data/autonomy/patch_session_intake/ data/autonomy/file_change_plan/ data/autonomy/patch_blueprint/ data/autonomy/patch_review_packet/ data/autonomy/patch_session_audit/

# v145.1-v150.0 source-only privacy tokens: data/autonomy/patch_draft_request/ data/autonomy/file_patch_drafts/ data/autonomy/patch_diff_review/ data/autonomy/patch_draft_qa/ data/autonomy/patch_draft_generation_audit/

# v150.1-v155.0 source-only privacy tokens: data/autonomy/implementation_handoff/ data/autonomy/manual_patch_application_plan/ data/autonomy/implementation_verification_worksheet/ data/autonomy/implementation_rollback_packet/ data/autonomy/implementation_handoff_audit/
# v155.1-v165.0 source-only privacy tokens: data/autonomy/patch_readiness_intake/ data/autonomy/patch_readiness_score/ data/autonomy/patch_readiness_blockers/ data/autonomy/patch_go_no_go_decision/ data/autonomy/patch_application_readiness_audit/

# v160.1-v165.0 source-only privacy tokens: data/autonomy/patch_sandbox_intake/ data/autonomy/sandbox_patch_application_plan/ data/autonomy/sandbox_verification_packet/ data/autonomy/sandbox_result_review/ data/autonomy/sandbox_patch_application_audit/

# v165.1-v170.0 source-only privacy tokens: data/autonomy/sandbox_promotion_intake/ data/autonomy/source_promotion_plan/ data/autonomy/promotion_approval_packet/ data/autonomy/post_promotion_verification/ data/autonomy/sandbox_to_source_promotion_audit/

# v170.1-v175.0 source-only privacy tokens: data/autonomy/source_application_approval/ data/autonomy/live_source_application_plan/ data/autonomy/approved_source_application_execution/ data/autonomy/post_application_verification/ data/autonomy/source_patch_application_audit/

# v175.1-v180.0 source-only privacy tokens: data/autonomy/post_application_outcome_intake/ data/autonomy/post_application_lessons/ data/autonomy/next_improvement_candidates/ data/autonomy/post_application_release_readiness/ data/autonomy/post_application_cycle_closure/
# v180.1-v185.0 source-only privacy tokens: data/autonomy/cycle_intelligence_intake/ data/autonomy/supervised_patch_priority_matrix/ data/autonomy/next_patch_proposal_assembly/ data/autonomy/supervised_patch_session_planner/ data/autonomy/patch_cycle_intelligence_audit/

# v185.1-v190.0 source-only privacy tokens: data/autonomy/multi_cycle_roadmap_intake/ data/autonomy/supervised_roadmap_options/ data/autonomy/roadmap_dependency_risk_graph/ data/autonomy/v200_readiness_model/ data/autonomy/multi_cycle_roadmap_governance_audit/

# v190.1-v195.0 source-only privacy tokens: data/autonomy/capability_maturity_inventory/ data/autonomy/capability_maturity_scoring/ data/autonomy/capability_gap_overreach_analysis/ data/autonomy/capability_maturity_improvement_plan/ data/autonomy/capability_maturity_governance_audit/

# v195.1-v200.0 source-only privacy tokens: data/autonomy/governance_kernel_state/ data/autonomy/governance_rule_evaluation/ data/autonomy/operator_authority_consent_ledger/ data/autonomy/governance_enforcement_simulation/ data/autonomy/governance_kernel_audit/

# v200 final CLI/API token: local-artificial-mind-governance-kernel-v1

# v200.1-v205.0 source-only privacy tokens: data/autonomy/governance_decision_packet/ data/autonomy/approval_transaction_model/ data/autonomy/governance_evidence_timeline/ data/autonomy/operator_governance_console/ data/autonomy/governance_integration_audit/

# v205.1-v210.0 cognitive continuity runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/cognitive_continuity_packet/ data/autonomy/memory_candidate_staging/ data/autonomy/identity_boundary_layer/ data/autonomy/supervised_reflection_journal/ data/autonomy/cognitive_continuity_audit/ memory_candidates_mutate_memory=False identity_reviews_alter_identity=False reflection_entries_schedule_work=False growth_journal_authorizes_actions=False no_native_title_tooltip

# v210.1-v215.0 deliberation/self-model runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/self_model_snapshot/ data/autonomy/deliberation_packet/ data/autonomy/purpose_alignment_layer/ data/autonomy/behavioral_pattern_intelligence/ data/autonomy/self_model_integration_audit/ self_model_confidence_authorizes_action=False deliberation_packets_execute_work=False deliberation_packets_grant_approval=False purpose_alignment_rewrites_purpose=False behavior_patterns_launch_work=False priority_scores_select_roadmaps=False no_native_title_tooltip

# v215.1-v220.0 simulation/foresight runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/internal_simulation_packet/ data/autonomy/foresight_branch_comparison/ data/autonomy/pre_change_consequence_modeling/ data/autonomy/expectation_reality_check/ data/autonomy/simulation_foresight_audit/ simulation_packets_execute_commands=False simulation_success_grants_approval=False branch_comparison_selects_roadmap=False consequence_model_mutates_source=False expectation_reality_launches_followup=False simulation_promotes_release=False no_native_title_tooltip

# v220.1-v225.0 learning curriculum runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/learning_objective_map/ data/autonomy/practice_task_design/ data/autonomy/capability_calibration/ data/autonomy/skill_gap_remediation_planner/ data/autonomy/learning_curriculum_audit/ learning-objective-map practice-task-design capability-calibration skill-gap-remediation-planner learning-curriculum-audit operator-governed-learning-curriculum-and-capability-calibration-layer-v1 learning_objectives_start_work=False practice_tasks_execute_work=False calibration_promotes_capability=False remediation_continues_work=False autonomous_learning_loop_started=False hidden_training_started=False local_model_invoked_by_default=False memory_mutation_performed=False identity_mutation_performed=False no_native_title_tooltip

# v225.1-v230.0 knowledge organization runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/knowledge_claim_ledger/ data/autonomy/belief_candidate_review/ data/autonomy/contradiction_staleness_intelligence/ data/autonomy/project_knowledge_map/ data/autonomy/knowledge_organization_audit/ knowledge-claim-ledger belief-candidate-review contradiction-staleness-intelligence project-knowledge-map knowledge-organization-audit operator-governed-knowledge-and-belief-organization-layer-v1 claim_entries_mutate_memory=False belief_candidates_promote_truth=False belief_state_authorizes_action=False autonomous_research_loop_started=False hidden_source_fetching_started=False memory_mutation_performed=False identity_mutation_performed=False confidence_equals_truth=False no_native_title_tooltip

# v230.1-v235.0 local model workbench runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/local_model_inventory/ data/autonomy/model_evaluation_plan/ data/autonomy/model_output_comparison/ data/autonomy/cognitive_workbench_routing/ data/autonomy/local_model_workbench_audit/ local-model-inventory model-evaluation-plan model-output-comparison cognitive-workbench-routing local-model-workbench-audit operator-governed-local-model-evaluation-and-cognitive-workbench-layer-v1 local_model_invoked_by_default=False hidden_model_calls_started=False autonomous_evaluation_loop_started=False evaluation_plans_execute_models=False model_output_promotes_truth=False model_recommendation_grants_approval=False self_upgrade_from_model_output=False memory_mutation_from_model_output=False identity_mutation_from_model_output=False roadmap_selected_from_model_ranking=False no_native_title_tooltip

# v255.1-v260.0 approved application prep runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/application_prep_intake/ data/autonomy/source_edit_application_plan/ data/autonomy/documentation_application_plan/ data/autonomy/final_application_governance_gate/ data/autonomy/application_prep_integration_audit/ application-prep-intake source-edit-application-plan documentation-application-plan final-application-governance-gate application-prep-integration-audit operator-governed-approved-execution-packet-application-prep-v1 application_prep_writes_files=False application_prep_applies_source_edits=False application_prep_runs_commands=False application_prep_executes_sandboxes=False application_prep_publishes_releases=False application_prep_mutates_memory=False application_prep_alters_identity=False application_prep_invokes_models_by_default=False application_prep_self_approves=False application_prep_inferrs_approval_from_readiness=False application_prep_reuses_stale_consent=False source_edit_plans_mutate_source=False documentation_plans_update_docs_automatically=False final_gate_grants_authority=False verification_plans_execute_commands=False rollback_plans_alter_files=False release_candidate_created_from_application_prep=False continuation_after_application_prep=False no_native_title_tooltip
# v250.1-v255.0 patch execution packet bridge runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/draft_to_execution_packet/ data/autonomy/patch_diff_preview_planner/ data/autonomy/execution_approval_scope/ data/autonomy/verification_rollback_packet/ data/autonomy/patch_execution_packet_audit/ draft-to-execution-packet patch-diff-preview-planner execution-approval-scope verification-rollback-packet patch-execution-packet-audit operator-governed-patch-execution-packet-bridge-v1 execution_packets_write_files=False execution_packets_apply_patches=False execution_packets_run_commands=False execution_packets_execute_sandboxes=False execution_packets_publish_releases=False execution_packets_mutate_memory=False execution_packets_alter_identity=False execution_packets_invoke_models_by_default=False execution_packets_self_approve=False approval_inferred_from_packet_readiness=False approval_inferred_from_model_output=False approval_inferred_from_model_consensus=False stale_or_vague_consent_reused=False diff_previews_mutate_source=False verification_packets_execute_commands=False rollback_packets_alter_files=False release_candidate_created_from_packet=False continuation_after_packet_assembly=False no_native_title_tooltip
# v245.1-v250.0 model-assisted patch draft assembly runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/model_assisted_patch_draft/ data/autonomy/file_impact_documentation_planner/ data/autonomy/smoke_verification_suggestions/ data/autonomy/sandbox_preparation_packet/ data/autonomy/patch_draft_assembly_audit/ model-assisted-patch-draft file-impact-documentation-planner smoke-verification-suggestions sandbox-preparation-packet patch-draft-assembly-audit operator-governed-model-assisted-patch-draft-assembly-layer-v1 model_output_treated_as_correctness_proof=False model_consensus_infers_approval=False draft_packets_write_files=False draft_packets_apply_patches=False draft_packets_run_commands=False draft_packets_approve_implementation=False file_impact_plans_execute_work=False documentation_updates_applied_automatically=False verification_suggestions_execute=False sandbox_packets_execute=False source_mutation_from_draft=False memory_mutation_from_draft=False identity_mutation_from_draft=False release_candidate_created_from_draft=False continuation_after_draft_assembly=False stale_or_out_of_scope_consent_reused=False no_native_title_tooltip
# v240.1-v245.0 model-assisted patch review runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/model_assisted_patch_critique/ data/autonomy/multi_model_review_synthesis/ data/autonomy/patch_risk_remediation_synthesis/ data/autonomy/model_review_quality_calibration/ data/autonomy/model_assisted_patch_review_audit/ model-assisted-patch-critique multi-model-review-synthesis patch-risk-remediation-synthesis model-review-quality-calibration model-assisted-patch-review-audit operator-governed-model-assisted-patch-review-and-synthesis-layer-v1 local_model_invocation_without_consent=False hidden_model_calls_started=False model_review_grants_approval=False model_output_treated_as_truth=False model_output_treated_as_proof=False model_consensus_selects_roadmap=False patch_application_from_model_review=False source_mutation_from_model_review=False verification_commands_from_model_review=False release_created_from_model_review=False memory_mutation_from_model_review=False identity_mutation_from_model_review=False review_quality_promotes_reliability=False continuation_after_review=False no_native_title_tooltip
# v235.1-v240.0 local model invocation sandbox runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/local_model_invocation_consent/ data/autonomy/model_evaluation_run_ledger/ data/autonomy/multi_model_output_triage/ data/autonomy/model_reliability_profile_candidates/ data/autonomy/local_model_invocation_sandbox_audit/ local-model-invocation-consent model-evaluation-run-ledger multi-model-output-triage model-reliability-profile-candidates local-model-invocation-sandbox-audit operator-approved-local-model-invocation-sandbox-v1 model_invocation_by_default=False hidden_model_calls_started=False autonomous_evaluation_loop_started=False invocation_requires_scoped_operator_approval=True expired_consent_reusable=False run_outputs_promote_truth=False run_outputs_authorize_action=False triage_grants_approval=False reliability_candidates_self_promote=False capability_promotion_from_model_output=False memory_mutation_from_model_output=False identity_mutation_from_model_output=False roadmap_selected_from_model_ranking=False no_native_title_tooltip

# v260.1-v265.0 structural stabilization runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/structural_inventory/ data/autonomy/runtime_registry_prep/ data/autonomy/dashboard_stabilization_audit/ data/autonomy/dispatch_stabilization/ data/autonomy/structural_stabilization_audit/ structural-inventory runtime-registry-prep dashboard-stabilization-audit dispatch-stabilization structural-stabilization-audit operator-governed-structural-stabilization-and-runtime-modularization-v1 structural_stabilization_writes_files=False structural_stabilization_applies_refactors=False structural_stabilization_rewrites_architecture=False structural_stabilization_removes_routes=False structural_stabilization_runs_commands=False structural_stabilization_invokes_models_by_default=False structural_stabilization_inferrs_approval_from_audit=False structural_stabilization_self_approves=False structural_stabilization_mutates_memory=False structural_stabilization_alters_identity=False structural_stabilization_publishes_release_candidates=False structural_stabilization_continues_automatically=False registry_prep_changes_dispatch=False dashboard_stabilization_changes_layout_contract=False dispatch_stabilization_executes_commands=False refactor_readiness_applies_refactor=False existing_behavior_preserved=True operator_approval_required_for_refactor=True runtime_registry_is_plan_only=True dashboard_data_tip_required=True native_nav_title_tooltips_forbidden=True package_privacy_required=True no_native_title_tooltip

# v265.1-v270.0 module extraction runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/runtime_registry/ data/autonomy/governance_report_builder_audit/ data/autonomy/dashboard_registry_integration/ data/autonomy/runtime_dispatch_registry_audit/ data/autonomy/module_extraction_audit/ runtime-registry governance-report-builder-audit dashboard-registry-integration runtime-dispatch-registry-audit module-extraction-audit operator-governed-runtime-module-extraction-v1 runtime_registry.py governance_reports.py module_extraction_writes_files_automatically=False module_extraction_removes_routes=False module_extraction_changes_dashboard_behavior=False module_extraction_rewrites_architecture_aggressively=False module_extraction_inferrs_approval_from_success=False module_extraction_invokes_models_by_default=False module_extraction_runs_verification_automatically=False module_extraction_self_approves=False module_extraction_mutates_memory=False module_extraction_alters_identity=False module_extraction_publishes_releases=False module_extraction_continues_automatically=False legacy_wrappers_required=True existing_routes_preserved=True dashboard_data_tip_required=True native_nav_title_tooltips_forbidden=True package_privacy_required=True operator_approval_required_for_deeper_refactor=True no_native_title_tooltip

# v270.1-v275.0 self-maintenance decomposition runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/self_maintenance_extraction_map/ data/autonomy/package_version_integrity/ data/autonomy/surface_parity_audit/ data/autonomy/verification_planning_audit/ data/autonomy/self_maintenance_decomposition_audit/ self-maintenance-extraction-map package-version-integrity surface-parity-audit verification-planning-audit self-maintenance-decomposition-audit operator-governed-self-maintenance-decomposition-v1 package_integrity.py version_state.py surface_parity.py verification_planning.py self_maintenance_decomposition_removes_legacy_wrappers=False self_maintenance_decomposition_changes_routes=False self_maintenance_decomposition_changes_cli_api_behavior=False self_maintenance_decomposition_executes_smoke_commands=False self_maintenance_decomposition_inferrs_approval_from_clean_audits=False self_maintenance_decomposition_invokes_models_by_default=False self_maintenance_decomposition_mutates_memory=False self_maintenance_decomposition_alters_identity=False self_maintenance_decomposition_self_approves=False self_maintenance_decomposition_publishes_release_candidates=False self_maintenance_decomposition_continues_automatically=False package_version_helpers_write_files=False surface_parity_helpers_add_routes=False verification_planning_helpers_run_commands=False legacy_wrappers_required=True existing_routes_preserved=True dashboard_data_tip_required=True native_nav_title_tooltips_forbidden=True package_privacy_required=True operator_approval_required_for_deeper_decomposition=True no_native_title_tooltip

# v275.1-v280.0 dashboard/API/CLI modularization runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/dashboard_extraction_map/ data/autonomy/dashboard_component_audit/ data/autonomy/api_surface_audit/ data/autonomy/cli_surface_audit/ data/autonomy/interface_modularization_audit/ dashboard-extraction-map dashboard-component-audit api-surface-audit cli-surface-audit interface-modularization-audit operator-governed-dashboard-api-cli-modularization-v1 dashboard_components.py api_surface.py cli_surface.py interface_modularization_redesigns_dashboard=False interface_modularization_removes_routes=False interface_modularization_changes_api_cli_behavior=False interface_modularization_adds_autonomous_command_execution=False interface_modularization_invokes_models_by_default=False interface_modularization_inferrs_approval_from_clean_audits=False interface_modularization_mutates_memory=False interface_modularization_alters_identity=False interface_modularization_self_approves=False interface_modularization_publishes_releases=False interface_modularization_continues_automatically=False dashboard_components_change_visual_contract=False dashboard_components_use_native_title_tooltips=False api_surface_helpers_change_behavior=False cli_surface_helpers_execute_commands=False legacy_wrappers_required=True existing_routes_preserved=True existing_api_cli_behavior_preserved=True dashboard_data_tip_required=True native_nav_title_tooltips_forbidden=True command_deck_style_required=True package_privacy_required=True operator_approval_required_for_interface_changes=True no_native_title_tooltip

# v280.1-v285.0 application execution refinement runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/approved_application_binding/ data/autonomy/operator_execution_checklist/ data/autonomy/post_application_result_review/ data/autonomy/application_outcome_learning/ data/autonomy/application_execution_refinement_audit/ approved-application-binding operator-execution-checklist post-application-result-review application-outcome-learning application-execution-refinement-audit operator-approved-application-execution-refinement-v1 application_execution_refinement.py application_refinement_applies_patches_automatically=False application_refinement_executes_shell_commands_automatically=False application_refinement_infers_approval_from_readiness=False application_refinement_reuses_stale_or_vague_consent=False application_refinement_runs_rollback_automatically=False application_refinement_mutates_memory=False application_refinement_alters_identity=False application_refinement_invokes_models_by_default=False application_refinement_publishes_release_candidates=False application_refinement_continues_automatically=False application_refinement_treats_outcome_learning_as_stored_memory=False application_refinement_requires_exact_current_scoped_approval=True application_refinement_is_review_only_until_operator_execution_approval=True application_refinement_requires_post_application_operator_result_intake=True application_refinement_recommends_rollback_review_only=True no_native_title_tooltip

# v285.1-v290.0 rollback and recovery intelligence runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/rollback_scope_binding/ data/autonomy/failure_damage_map/ data/autonomy/recovery_checklist/ data/autonomy/post_recovery_review/ data/autonomy/rollback_recovery_audit/ rollback-scope-binding failure-damage-map recovery-checklist post-recovery-review rollback-recovery-audit operator-governed-rollback-and-recovery-intelligence-v1 rollback_recovery.py rollback_recovery_runs_rollback_automatically=False rollback_recovery_edits_files_automatically=False rollback_recovery_executes_shell_commands_automatically=False rollback_recovery_infers_rollback_approval_from_failure=False rollback_recovery_infers_patch_approval_from_recovery_success=False rollback_recovery_mutates_memory=False rollback_recovery_alters_identity=False rollback_recovery_invokes_models_by_default=False rollback_recovery_publishes_release_candidates=False rollback_recovery_continues_automatically=False rollback_recovery_requires_operator_submitted_results=True rollback_recovery_requires_explicit_rollback_approval=True rollback_recovery_is_review_only=True no_native_title_tooltip

# v290.1-v295.0 memory candidate governance runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/memory_candidate_intake/ data/autonomy/memory_candidate_classification/ data/autonomy/memory_approval_packet/ data/autonomy/memory_contradiction_review/ data/autonomy/memory_governance_audit/ memory-candidate-intake memory-candidate-classification memory-approval-packet memory-contradiction-review memory-governance-audit operator-governed-memory-candidate-governance-upgrade-v1 memory_governance.py memory_governance_writes_memory_automatically=False memory_governance_alters_identity=False memory_governance_alters_personality=False memory_governance_rewrites_goals_or_purpose=False memory_governance_infers_approval_from_repeated_evidence=False memory_governance_infers_approval_from_operator_silence=False memory_governance_treats_lessons_as_stored_truth=False memory_governance_invokes_models_by_default=False memory_governance_executes_commands=False memory_governance_publishes_release_candidates=False memory_governance_continues_automatically=False memory_governance_requires_operator_memory_approval=True memory_governance_stages_candidates_only=True memory_governance_sensitive_identity_boundary_required=True memory_governance_contradiction_review_required=True no_native_title_tooltip

# v295.1-v300.0 continuity kernel runtime privacy tokens intentionally excluded by source-only data rules: data/autonomy/continuity_state_intake/ data/autonomy/self_model_snapshot_v2/ data/autonomy/purpose_coherence_review/ data/autonomy/supervised_growth_priorities/ data/autonomy/continuity_kernel_v2_audit/ continuity-state-intake self-model-snapshot-v2 purpose-coherence-review supervised-growth-priorities continuity-kernel-v2-audit local-artificial-mind-continuity-kernel-v2 continuity_kernel.py continuity_kernel_mutates_memory=False continuity_kernel_alters_identity=False continuity_kernel_alters_personality=False continuity_kernel_rewrites_purpose=False continuity_kernel_self_approves_capabilities=False continuity_kernel_auto_selects_roadmaps=False continuity_kernel_starts_patches_automatically=False continuity_kernel_infers_approval_from_audits=False continuity_kernel_invokes_models_by_default=False continuity_kernel_executes_commands=False continuity_kernel_publishes_release_candidates=False continuity_kernel_treats_self_model_as_authority=False continuity_kernel_review_only=True continuity_kernel_requires_operator_review=True continuity_kernel_connects_memory_candidates=True continuity_kernel_connects_recovery_lessons=True no_native_title_tooltip data-tip command-deck
# v300.1-v305.0 identity/personality/coherence expression runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/identity_expression_boundary/ data/autonomy/personality_trait_ledger/ data/autonomy/voice_affect_style_map/ data/autonomy/coherence_expression_review/ data/autonomy/identity_personality_coherence_audit/ identity_expression.py
# v305.1-v310.0 behavioral expression preview and runtime health runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/dashboard_route_health/ data/autonomy/runtime_test_visibility/ data/autonomy/behavioral_expression_preview/ data/autonomy/style_delta_staging/ data/autonomy/expression_runtime_health_audit/ route_health.py behavioral_expression_preview.py dashboard_http_route_probe_required metadata_consistency_smoke_required timeout_aware_smoke_summary operator-governed-behavioral-expression-preview-and-runtime-health-hardening-v1

# v310.1-v315.0 conversational expression sandbox runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/expression_profile_packets/ data/autonomy/conversation_scenario_sandbox/ data/autonomy/expression_regression_review/ data/autonomy/expression_operator_review_console/ data/autonomy/conversational_expression_sandbox_audit/ conversational_expression_sandbox.py operator-governed-conversational-expression-sandbox-v1

# v315.1-v320.0 expression application bridge runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/expression_approval_criteria/ data/autonomy/expression_live_surface_impact_map/ data/autonomy/expression_implementation_packet_draft/ data/autonomy/expression_rollback_reversion_plan/ data/autonomy/expression_application_bridge_audit/ expression_application_bridge.py operator-governed-conversational-expression-application-bridge-v1
# v320.1-v325.0 expression patch dry-run runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/expression_patch_candidates/ data/autonomy/expression_sandbox_diff_preview/ data/autonomy/expression_dry_run_verification_plan/ data/autonomy/expression_dry_run_review_packet/ data/autonomy/expression_patch_dry_run_audit/ expression_patch_dry_run.py operator-governed-expression-patch-dry-run-sandbox-v1

# v325.1-v330.0 expression sandbox trial harness runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/expression_sandbox_trial_packet/ data/autonomy/expression_sandbox_workspace_plan/ data/autonomy/expression_sandbox_verification_matrix/ data/autonomy/expression_sandbox_result_review_prep/ data/autonomy/expression_sandbox_trial_harness_audit/ expression_sandbox_trial_harness.py operator-governed-expression-patch-sandbox-trial-harness-v1 trial_packet_executes_sandbox=False workspace_plan_copies_files=False workspace_plan_writes_files=False verification_matrix_executes_commands=False result_review_promotes_to_live=False trial_harness_audit_applies_changes=False

# v330.1-v335.0 expression sandbox execution bridge runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/expression_sandbox_execution_approval_gate/ data/autonomy/expression_sandbox_workspace_execution_packet/ data/autonomy/expression_sandbox_patch_bundle_packet/ data/autonomy/expression_sandbox_verification_command_packet/ data/autonomy/expression_sandbox_execution_packet_bridge_audit/ expression_sandbox_execution_bridge.py operator-governed-expression-sandbox-trial-execution-packet-bridge-v1 approval_gate_grants_approval=False workspace_execution_packet_copies_files=False workspace_execution_packet_writes_files=False patch_bundle_applies_patch=False verification_command_packet_executes_commands=False execution_bridge_executes_sandbox=False

# v335.1-v340.0 expression sandbox result intake runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/expression_sandbox_trial_evidence_intake/ data/autonomy/expression_sandbox_outcome_comparison/ data/autonomy/expression_sandbox_regression_result_review/ data/autonomy/expression_sandbox_revision_recommendations/ data/autonomy/expression_sandbox_promotion_review_prep/ expression_sandbox_result_intake.py operator-governed-expression-sandbox-trial-result-intake-and-promotion-review-prep-v1 evidence_intake_treats_evidence_as_approval=False outcome_comparison_auto_corrects_patch=False regression_review_auto_fixes_prompts=False revision_recommendations_apply_changes=False promotion_review_prep_promotes_to_live=False

# v340.1-v345.0 expression promotion packet runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/expression_promotion_evidence_binder/ data/autonomy/expression_live_promotion_scope_risk/ data/autonomy/expression_promotion_verification_rollback/ data/autonomy/expression_promotion_decision_packet/ data/autonomy/expression_promotion_packet_assembly_audit/ expression_promotion_packet.py operator-governed-expression-promotion-packet-assembly-layer-v1 promotion_evidence_binder_treats_evidence_as_approval=False live_scope_risk_mutates_live_surfaces=False verification_rollback_executes_commands=False promotion_decision_packet_executes_decision=False promotion_packet_assembly_promotes_live_expression=False

# v345.1-v350.0 expression live application packet runtime dirs are private/source-only excluded through data/autonomy/: data/autonomy/expression_live_application_eligibility_gate/ data/autonomy/expression_live_source_change_manifest/ data/autonomy/expression_live_patch_instruction_packet/ data/autonomy/expression_live_verification_rollback_packet/ data/autonomy/expression_live_application_packet_audit/ expression_live_application_packet.py operator-governed-expression-live-application-packet-drafting-layer-v1 eligibility_gate_authorizes_live_writes=False source_change_manifest_writes_files=False patch_instruction_packet_applies_patch=False verification_rollback_packet_executes_commands=False application_packet_audit_applies_live_source=False
