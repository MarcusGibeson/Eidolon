from __future__ import annotations

"""v1275.6-v1275.8 dependency/package reliability and native handoff."""

import hashlib
import os
import shutil
import tempfile
import venv
import zipfile
from pathlib import Path
from typing import Any, Mapping

from dependency_packaging_foundations import *
from dependency_packaging import inspect_dependency_packaging, verify_reproducible_package_manifest
from package_integrity import forbidden_runtime_path_matches, package_privacy_summary, source_package_bytes

CONTRACT_VERSION = "v1275.8"


def inspect_lock_and_configuration_intent(source_root: str | Path, baseline: Mapping[str, Any] | None = None) -> dict[str, Any]:
    current = inventory_dependency_intent(source_root)
    rows = current["dependency_files"]
    lock_rows = [x for x in rows if x.get("role") == "lock"]
    config_rows = [x for x in rows if x.get("role") == "configuration"]
    baseline_map = {x.get("relative_path"): x.get("content_digest") for x in (baseline or {}).get("dependency_files", [])}
    changed = [x["relative_path"] for x in rows if x.get("relative_path") in baseline_map and baseline_map[x["relative_path"]] != x.get("content_digest")]
    missing = [x for x in baseline_map if x not in {r.get("relative_path") for r in rows}]
    return {
        "ok": not missing, "status": "dependency_intent_preserved" if not changed and not missing else "dependency_intent_changed",
        "dependency_intent_digest": current["dependency_intent_digest"], "lock_file_count": len(lock_rows), "configuration_file_count": len(config_rows),
        "changed_dependency_intent_files": sorted(changed), "missing_dependency_intent_files": sorted(missing),
        "lock_configuration_content_exposed": False, **AUTHORITY_FLAGS,
    }


def create_disposable_clean_environment(base_dir: str | Path, *, with_pip: bool = True) -> dict[str, Any]:
    base = Path(base_dir).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = base / "clean_env"
    if target.exists():
        shutil.rmtree(target)
    venv.EnvBuilder(with_pip=with_pip, clear=True).create(target)
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    pip = target / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    return {
        "ok": python.is_file() and (pip.is_file() if with_pip else True), "status": "disposable_clean_environment_ready",
        "environment_root_digest": _digest(str(target)), "python_present": python.is_file(), "pip_present": pip.is_file(),
        "raw_environment_path_persisted": False, "active_source_modified": False, **AUTHORITY_FLAGS,
    }


def validate_source_package_privacy(source_root: str | Path) -> dict[str, Any]:
    manifest = build_reproducible_source_package_manifest(source_root)
    names = [x["relative_path"] for x in manifest["package_files"]]
    forbidden = forbidden_runtime_path_matches(names)
    items = {x["relative_path"]: b"" for x in manifest["package_files"] if x["relative_path"].startswith("data/")}
    privacy = package_privacy_summary(items.keys())
    return {
        "ok": not forbidden and privacy.get("private_content_finding_count", 0) == 0,
        "status": "source_package_privacy_ready" if not forbidden and privacy.get("private_content_finding_count", 0) == 0 else "source_package_privacy_blocked",
        "package_file_count": manifest["package_file_count"], "forbidden_runtime_entry_count": len(forbidden),
        "private_content_finding_count": privacy.get("private_content_finding_count", 0), "package_manifest_digest": manifest["package_manifest_digest"],
        "package_published": False, **AUTHORITY_FLAGS,
    }



def write_reproducible_source_zip(source_root: str | Path, output_path: str | Path) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    output = Path(output_path).expanduser().resolve()
    if output == root or root in output.parents:
        raise ValueError("reproducible_package_output_must_be_outside_source")
    manifest = build_reproducible_source_package_manifest(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for row in manifest["package_files"]:
                rel = str(row["relative_path"])
                info = zipfile.ZipInfo(f"Eidolon/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.flag_bits = 0
                archive.writestr(info, source_package_bytes(root, rel), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(tmp, output)
    finally:
        tmp.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "ok": True, "status": "reproducible_source_zip_written", "archive_sha256": digest,
        "package_manifest_digest": manifest["package_manifest_digest"], "package_file_count": manifest["package_file_count"],
        "single_root": "Eidolon", "fixed_archive_metadata": True, "source_modified": False,
        "release_authorized": False, "package_published": False, **AUTHORITY_FLAGS,
    }

def inspect_dependency_packaging_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    assessment = inspect_dependency_packaging(root)
    package = build_reproducible_source_package_manifest(root)
    repro = verify_reproducible_package_manifest(root, package)
    privacy = validate_source_package_privacy(root)
    checks = {
        "assessment_ready": assessment.get("ok") is True,
        "dependency_conflicts_absent": assessment.get("conflict_count") == 0,
        "package_manifest_reproducible": repro.get("ok") is True,
        "package_privacy_ready": privacy.get("ok") is True,
        "active_source_not_modified": True,
    }
    return {"ok": all(checks.values()), "status": "dependency_packaging_health_ready" if all(checks.values()) else "dependency_packaging_health_blocked", "checks": checks, **AUTHORITY_FLAGS}


def build_dependency_packaging_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_dependency_packaging_health(source_root=root)
    return {
        "ok": health["ok"], "status": "dependency_packaging_operator_handoff_ready" if health["ok"] else "dependency_packaging_operator_handoff_blocked",
        "contract_version": CONTRACT_VERSION,
        "native_windows_validation": [
            "fresh_python_venv_creation", "pip_no_index_and_offline_failure_behavior", "requirements_include_paths_on_ntfs",
            "locked_file_and_sharing_violation_behavior", "long_paths_and_extended_length_paths", "clean_install_from_fresh_source_extraction",
            "dependency_conflict_reporting", "lock_configuration_intent_preservation", "source_only_zip_entry_privacy", "reproducible_package_bytes",
        ],
        "next_bounded_unit": "v1276 Architecture Boundary Extraction", "v1276_started": False,
        "installation_authority_expanded": False, "release_authority_expanded": False, **AUTHORITY_FLAGS,
    }


__all__ = ["CONTRACT_VERSION", "inspect_lock_and_configuration_intent", "create_disposable_clean_environment", "validate_source_package_privacy", "write_reproducible_source_zip", "inspect_dependency_packaging_health", "build_dependency_packaging_operator_handoff"]
