from __future__ import annotations

"""Preview-first, digest-bound reconciliation for explicit version roles.

This boundary separates source-safe metadata from mutable operator runtime
metadata.  It never installs, promotes, certifies, or infers an installed
version from the source being inspected.
"""

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
import uuid

try:
    from json_storage import canonical_json_bytes, write_json_atomic
    from release_metadata import NEXT_RECOMMENDED_ARC, RUNTIME_MILESTONE, WORKING_SOURCE_VERSION
    from version_resolution import build_cross_surface_version_resolution
    from version_roles import normalize_version, version_from_artifact_name
except ImportError:
    from json_storage import canonical_json_bytes, write_json_atomic
    from release_metadata import NEXT_RECOMMENDED_ARC, RUNTIME_MILESTONE, WORKING_SOURCE_VERSION
    from version_resolution import build_cross_surface_version_resolution
    from version_roles import normalize_version, version_from_artifact_name

SOURCE_SURFACES: dict[str, tuple[str, str]] = {
    "source.settings": ("data/settings.json", "json"),
    "source.active_project": ("data/workspaces/active_project.json", "json"),
    "source.projects": ("data/workspaces/projects.json", "json"),
    "source.readme": ("README.md", "text"),
    "source.desktop_readme": ("archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "text"),
    "source.next_steps": ("README_NEXT_STEPS.md", "text"),
}
RUNTIME_SURFACES: dict[str, tuple[str, str]] = {
    "runtime.projects": ("data/projects.json", "json"),
    "runtime.settings": ("data/settings.json", "json"),
}
_ALL_SURFACES = {**SOURCE_SURFACES, **RUNTIME_SURFACES}
_VERSION_HEADING = re.compile(r"^(?P<prefix>#{1,6}\s+(?:Eidolon |Desktop Alpha )?v)(?P<version>\d+(?:\.\d+)+)(?P<rest>.*)$", re.MULTILINE)
_CURRENT_MILESTONE = re.compile(r"(?m)^(?P<prefix>Current(?: Desktop Alpha)?(?: working-source| source)? milestone:\s*\*\*v)(?P<version>\d+(?:\.\d+)+)(?P<rest>[^\n]*\*\*\.)$")


def _root(path: str | Path | None) -> Path:
    return Path(path or Path(__file__).resolve().parents[1]).resolve()


def _runtime_root(path: str | Path | None) -> Path | None:
    if path:
        return Path(path).resolve()
    explicit = os.environ.get("EIDOLON_RUNTIME_ROOT", "").strip()
    if explicit:
        return Path(explicit).resolve()
    data_root = os.environ.get("EIDOLON_DATA_DIR", "").strip()
    if data_root:
        candidate = Path(data_root).resolve()
        return candidate.parent if candidate.name == "data" else candidate
    return None


def _contained(base: Path, target: Path) -> bool:
    try:
        target.resolve(strict=False).relative_to(base.resolve(strict=False))
        return True
    except ValueError:
        return False


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_json(raw: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _source_json_proposal(surface_id: str, value: dict[str, Any], expected: str) -> dict[str, Any]:
    proposed = json.loads(json.dumps(value))
    common = {
        "version": expected,
        "root_version": expected,
        "working_source_version": expected,
        "last_updated_for": f"v{expected}",
        "current_milestone": RUNTIME_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
    }
    proposed.update(common)
    if surface_id == "source.settings":
        proposed["settings_version"] = expected
    if surface_id == "source.projects":
        for project in proposed.get("projects", []):
            if isinstance(project, dict) and str(project.get("id") or "") == "eidolon":
                project.update(common)
                project["working_version"] = expected
                # Installed and candidate roles are preserved exactly as declared.
    return proposed


def _runtime_json_proposal(value: dict[str, Any], expected: str, expected_role: str) -> dict[str, Any]:
    proposed = json.loads(json.dumps(value))
    if expected_role != "installed":
        raise ValueError("Mutable operator runtime reconciliation supports only the installed role.")
    proposed["installed_version"] = expected
    for project in proposed.get("projects", []):
        if isinstance(project, dict) and str(project.get("id") or "") == "eidolon":
            project["installed_version"] = expected
    return proposed


def _text_proposal(text: str, expected: str) -> str:
    # Current-facing README sections precede historical marker sections.  Never
    # rewrite the historical marker suffix or release history through this API.
    markers = [
        text.find("Historical retained verification markers"),
        text.find("## Historical verification markers"),
    ]
    cut = min((item for item in markers if item >= 0), default=len(text))
    current, suffix = text[:cut], text[cut:]
    current = _VERSION_HEADING.sub(lambda m: f"{m.group('prefix')}{expected}{m.group('rest')}", current, count=1)
    current = _CURRENT_MILESTONE.sub(lambda m: f"{m.group('prefix')}{expected}{m.group('rest')}", current, count=1)
    return current + suffix


def _surface_target(
    surface_id: str,
    *,
    root_dir: str | Path | None,
    runtime_root: str | Path | None,
) -> tuple[Path, Path, str, str, bool]:
    if surface_id not in _ALL_SURFACES:
        raise ValueError("Unknown version reconciliation surface.")
    relative, kind = _ALL_SURFACES[surface_id]
    mutable_runtime = surface_id in RUNTIME_SURFACES
    base = _runtime_root(runtime_root) if mutable_runtime else _root(root_dir)
    if base is None:
        raise ValueError("Mutable runtime root is not explicitly configured.")
    target = (base / relative).resolve(strict=False)
    if not _contained(base, target):
        raise ValueError("Version reconciliation target escapes its configured root.")
    return base, target, relative, kind, mutable_runtime


def _token(
    *,
    surface_id: str,
    relative_path: str,
    expected_role: str,
    expected_version: str,
    original_sha256: str,
    proposed_sha256: str,
    mutable_runtime: bool,
) -> str:
    material = "\n".join((
        "version-reconciliation-v1",
        surface_id,
        relative_path,
        expected_role,
        expected_version,
        original_sha256,
        proposed_sha256,
        "runtime" if mutable_runtime else "source",
    ))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def preview_version_reconciliation(
    surface_id: str,
    *,
    root_dir: str | Path | None = None,
    runtime_root: str | Path | None = None,
    expected_role: str = "working_source",
    expected_version: str = "",
) -> dict[str, Any]:
    base, target, relative, kind, mutable_runtime = _surface_target(
        surface_id, root_dir=root_dir, runtime_root=runtime_root
    )
    expected = normalize_version(expected_version)
    if mutable_runtime:
        if expected_role != "installed" or not expected:
            return {
                "ok": False,
                "status": "explicit_installed_version_required",
                "surface_id": surface_id,
                "expected_role": expected_role,
                "mutable_operator_runtime": True,
                "content_free": True,
            }
    else:
        expected_role = "working_source"
        expected = WORKING_SOURCE_VERSION
    try:
        raw = target.read_bytes()
    except OSError:
        return {
            "ok": False,
            "status": "missing_or_unreadable",
            "surface_id": surface_id,
            "relative_path": relative,
            "mutable_operator_runtime": mutable_runtime,
            "content_free": True,
        }

    original_sha = _digest(raw)
    if kind == "json":
        value = _safe_json(raw)
        if value is None:
            return {
                "ok": False,
                "status": "invalid_original_preserved",
                "surface_id": surface_id,
                "relative_path": relative,
                "original_sha256": original_sha,
                "mutable_operator_runtime": mutable_runtime,
                "content_free": True,
            }
        try:
            proposed_value = (
                _runtime_json_proposal(value, expected, expected_role)
                if mutable_runtime
                else _source_json_proposal(surface_id, value, expected)
            )
        except ValueError as error:
            return {
                "ok": False,
                "status": "invalid_request",
                "error": str(error),
                "surface_id": surface_id,
                "mutable_operator_runtime": mutable_runtime,
                "content_free": True,
            }
        proposed = canonical_json_bytes(proposed_value)
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return {
                "ok": False,
                "status": "invalid_original_preserved",
                "surface_id": surface_id,
                "relative_path": relative,
                "original_sha256": original_sha,
                "mutable_operator_runtime": False,
                "content_free": True,
            }
        proposed = _text_proposal(text, expected).encode("utf-8")

    proposed_sha = _digest(proposed)
    changed = proposed_sha != original_sha
    token = _token(
        surface_id=surface_id,
        relative_path=relative,
        expected_role=expected_role,
        expected_version=expected,
        original_sha256=original_sha,
        proposed_sha256=proposed_sha,
        mutable_runtime=mutable_runtime,
    )
    return {
        "ok": True,
        "status": "correction_available" if changed else "already_aligned",
        "surface_id": surface_id,
        "scope": "mutable_operator_runtime" if mutable_runtime else "source_safe",
        "relative_path": relative,
        "expected_role": expected_role,
        "expected_version": expected,
        "original_sha256": original_sha,
        "proposed_sha256": proposed_sha,
        "preview_token": token,
        "changed": changed,
        "operator_confirmation_required": changed,
        "dedicated_runtime_confirmation_required": bool(mutable_runtime and changed),
        "mutable_operator_runtime": mutable_runtime,
        "source_safe": not mutable_runtime,
        "installed": False,
        "promoted": False,
        "certified": False,
        "payload_included": False,
        "absolute_path_included": False,
        "content_free": True,
    }


def _write_text_atomic(target: Path, payload: bytes) -> None:
    temporary = target.with_name(f".{target.name}.version-reconcile-{os.getpid()}-{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        if _digest(target.read_bytes()) != _digest(payload):
            raise OSError("Version reconciliation verification failed.")
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def apply_version_reconciliation(
    surface_id: str,
    *,
    preview_token: str,
    operator_confirmed: bool,
    mutable_runtime_confirmed: bool = False,
    root_dir: str | Path | None = None,
    runtime_root: str | Path | None = None,
    expected_role: str = "working_source",
    expected_version: str = "",
) -> dict[str, Any]:
    if operator_confirmed is not True:
        return {"ok": False, "status": "literal_confirmation_required", "content_free": True}
    preview = preview_version_reconciliation(
        surface_id,
        root_dir=root_dir,
        runtime_root=runtime_root,
        expected_role=expected_role,
        expected_version=expected_version,
    )
    if not preview.get("ok"):
        return preview
    if str(preview_token or "") != str(preview.get("preview_token") or ""):
        return {
            "ok": False,
            "status": "stale_or_mismatched_preview",
            "stale_confirmation": True,
            "content_free": True,
        }
    if preview.get("mutable_operator_runtime") and mutable_runtime_confirmed is not True:
        return {
            "ok": False,
            "status": "dedicated_runtime_confirmation_required",
            "content_free": True,
        }
    if not preview.get("changed"):
        return {
            "ok": True,
            "status": "already_aligned",
            "changed": False,
            "content_free": True,
        }

    _, target, relative, kind, mutable_runtime = _surface_target(
        surface_id, root_dir=root_dir, runtime_root=runtime_root
    )
    current_raw = target.read_bytes()
    if _digest(current_raw) != preview.get("original_sha256"):
        return {
            "ok": False,
            "status": "stale_or_mismatched_preview",
            "stale_confirmation": True,
            "content_free": True,
        }
    if kind == "json":
        value = _safe_json(current_raw)
        if value is None:
            return {"ok": False, "status": "invalid_original_preserved", "content_free": True}
        expected = str(preview.get("expected_version") or "")
        proposed_value = (
            _runtime_json_proposal(value, expected, str(preview.get("expected_role") or ""))
            if mutable_runtime
            else _source_json_proposal(surface_id, value, expected)
        )
        write_json_atomic(target, proposed_value, expected_type=dict)
    else:
        text = current_raw.decode("utf-8-sig")
        payload = _text_proposal(text, str(preview.get("expected_version") or "")).encode("utf-8")
        _write_text_atomic(target, payload)

    final_sha = _digest(target.read_bytes())
    if final_sha != preview.get("proposed_sha256"):
        return {
            "ok": False,
            "status": "post_write_verification_failed",
            "uncertain_result": True,
            "content_free": True,
        }
    return {
        "ok": True,
        "status": "reconciled",
        "changed": True,
        "surface_id": surface_id,
        "scope": "mutable_operator_runtime" if mutable_runtime else "source_safe",
        "relative_path": relative,
        "expected_role": preview.get("expected_role"),
        "expected_version": preview.get("expected_version"),
        "final_sha256": final_sha,
        "mutable_operator_runtime_modified": mutable_runtime,
        "source_safe_modified": not mutable_runtime,
        "installed": False,
        "promoted": False,
        "certified": False,
        "content_free": True,
    }


def build_version_drift_preview(
    root_dir: str | Path | None = None,
    *,
    runtime_root: str | Path | None = None,
    candidate_version: str = "",
    packaged_archive_name: str = "",
    archive_root_name: str = "",
) -> dict[str, Any]:
    resolution = build_cross_surface_version_resolution(
        root_dir,
        candidate_version=candidate_version,
        packaged_archive_name=packaged_archive_name,
    )
    rows = list(resolution.get("rows") or [])
    archive_version = version_from_artifact_name(packaged_archive_name)
    if packaged_archive_name:
        ok = archive_version == WORKING_SOURCE_VERSION
        rows.append({
            "surface": "package.filename",
            "role": "packaged_archive",
            "observed_version": archive_version,
            "expected_version": WORKING_SOURCE_VERSION,
            "status": "pass" if ok else "drift",
            "ok": ok,
            "source": "explicit package filename",
            "current_surface": True,
        })
    if archive_root_name:
        ok = str(archive_root_name).strip().rstrip("/") == "Eidolon"
        rows.append({
            "surface": "package.archive_root",
            "role": "package_structure",
            "observed_version": "",
            "expected_version": "",
            "observed_root": str(archive_root_name).strip().rstrip("/"),
            "expected_root": "Eidolon",
            "status": "pass" if ok else "drift",
            "ok": ok,
            "source": "explicit archive root",
            "current_surface": True,
        })

    runtime_rows: list[dict[str, Any]] = []
    runtime_base = _runtime_root(runtime_root)
    if runtime_base is not None:
        path = runtime_base / "data" / "projects.json"
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                runtime_rows.append({
                    "surface": "runtime.projects",
                    "role": "installed",
                    "status": "invalid_original_preserved",
                    "ok": False,
                    "mutable_operator_runtime": True,
                })
            else:
                installed = normalize_version(payload.get("installed_version") if isinstance(payload, dict) else "")
                runtime_rows.append({
                    "surface": "runtime.projects",
                    "role": "installed",
                    "observed_version": installed,
                    "expected_version": "operator_declared",
                    "status": "declared" if installed else "unknown",
                    "ok": True,
                    "mutable_operator_runtime": True,
                })
    rows.extend(runtime_rows)
    try:
        from release_history import release_history_status
    except ImportError:
        from release_history import release_history_status
    history = release_history_status(root_dir)
    rows.append({
        "surface": "release.history",
        "role": "historical",
        "observed_version": "",
        "expected_version": "",
        "status": "pass" if history.get("ok") else "drift",
        "ok": bool(history.get("ok")),
        "source": "structured release-history parser",
        "current_surface": True,
        "entry_count": int(history.get("entry_count") or 0),
        "duplicate_version_count": int(history.get("duplicate_version_count") or 0),
        "ordering_violation_count": int(history.get("ordering_violation_count") or 0),
        "malformed_heading_count": int(history.get("malformed_heading_count") or 0),
        "ambiguous_heading_count": int(history.get("ambiguous_heading_count") or 0),
    })
    drift = [row for row in rows if row.get("status") in {"drift", "invalid_original_preserved"} or row.get("ok") is False]
    return {
        "ok": not drift,
        "status": "pass" if not drift else "drift_detected",
        "working_source_version": WORKING_SOURCE_VERSION,
        "rows": rows,
        "drift": drift,
        "drift_count": len(drift),
        "source_safe_drift_count": sum(not row.get("mutable_operator_runtime") for row in drift),
        "mutable_runtime_drift_count": sum(bool(row.get("mutable_operator_runtime")) for row in drift),
        "preview_only": True,
        "runtime_mutation_performed": False,
        "source_mutation_performed": False,
        "installed": False,
        "promoted": False,
        "certified": False,
        "content_free": True,
    }
