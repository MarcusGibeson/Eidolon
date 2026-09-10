from __future__ import annotations

"""Read-only installation impact preview for one coherent handoff and target.

All detailed records, paths, and file-effect rows live beneath an external
runtime root. Public summaries expose only identities, digests, counts, and
bounded contradiction kinds. No source is copied, removed, replaced, or
installed by this module.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, sha256_file, utc_now
    from release_handoff_inspection import handoff_directory, handoff_record_binding
    from release_handoff_recovery import _active_private_state
    from project_identity import project_source_binding
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, sha256_file, utc_now
    from release_handoff_inspection import handoff_directory, handoff_record_binding
    from release_handoff_recovery import _active_private_state
    from project_identity import project_source_binding

INSTALLATION_PREVIEW_CONTRACT_VERSION = "1"
TARGET_INVENTORY_EXCLUDED_DIRECTORIES = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    "data", "reports", "runtime", "backups", "approvals", "memories",
    "conversations", "drafts", "tasks", "models",
}
INSTALLATION_PREVIEW_SCHEMA = "eidolon-installation-impact-preview-v1"
INSTALLATION_PREVIEW_DIRECTORY = "release_installation_previews"

SOURCE_MANAGED_PREFIXES = ("conscious_agent/", "tools/", "sandbox/")
SOURCE_MANAGED_ROOT_FILES = {
    ".gitignore", "README.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md", "requirements.txt", "pyproject.toml", "setup.cfg",
}
PROTECTED_EXACT = {
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/projects.json",
    "data/workspaces/active_project.json",
    "data/signing/trusted_public_keys.json",
}
PROTECTED_PREFIXES = (
    ".git/", ".venv/", "venv/", "__pycache__/", "data/", "reports/",
    "retired_evidence_quarantine/",
)
PROTECTED_SUFFIXES = (
    ".pyc", ".pyo", ".zip", ".bak", ".backup", ".pem", ".key", ".p12", ".pfx",
    ".sqlite", ".sqlite3", ".db", ".log",
)


def preview_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / INSTALLATION_PREVIEW_DIRECTORY


def _kind_counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows or []:
        counts[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": counts[key]} for key in sorted(counts)]


def _safe_relative(value: str) -> str:
    token = str(value or "").replace("\\", "/").strip("/")
    path = PurePosixPath(token)
    if not token or path.is_absolute() or ".." in path.parts:
        return ""
    return path.as_posix()


def _protected(path: str) -> bool:
    rel = _safe_relative(path)
    if not rel:
        return True
    lowered = rel.lower()
    return (
        rel in PROTECTED_EXACT
        or any(rel.startswith(prefix) for prefix in PROTECTED_PREFIXES)
        or lowered.endswith(PROTECTED_SUFFIXES)
        or any(part.lower() in {"credentials", "secrets", "backups", "approvals", "memories", "conversations", "drafts", "tasks", "models"} for part in PurePosixPath(rel).parts)
    )


def _source_managed(path: str) -> bool:
    rel = _safe_relative(path)
    return bool(rel and (rel in SOURCE_MANAGED_ROOT_FILES or any(rel.startswith(prefix) for prefix in SOURCE_MANAGED_PREFIXES)))


def _file_sha(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def _target_inventory(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    if root.is_symlink() or not root.is_dir():
        return {"ok": False, "entries": [], "digest": "", "findings": [{"kind": "target_root_missing_or_invalid"}]}
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(dirnames):
            child = current_path / name
            rel = child.relative_to(root).as_posix()
            if name in TARGET_INVENTORY_EXCLUDED_DIRECTORIES:
                continue
            if child.is_symlink():
                findings.append({"kind": "target_symlink", "path": rel})
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink() or not path.is_file():
                findings.append({"kind": "target_special_file", "path": rel})
                continue
            try:
                sha, size = _file_sha(path)
            except OSError:
                findings.append({"kind": "target_file_unreadable", "path": rel})
                continue
            rows.append({"path": rel, "sha256": sha, "size": size, "protected": _protected(rel), "source_managed": _source_managed(rel)})
    rows.sort(key=lambda row: row["path"])
    material = {"schema": "eidolon-target-inventory-v1", "entries": rows}
    return {"ok": not findings, "entries": rows, "digest": digest_payload(material), "findings": findings}


def _load_registry(path: str | Path | None = None) -> tuple[dict[str, Any], Path | None]:
    if path is None:
        try:
            import project_manager
        except ImportError:
            import project_manager
        return project_manager.load_projects_data(), None
    registry_path = Path(path).expanduser().resolve()
    return read_json(registry_path), registry_path


def _exact_registered_project(project_id: str, registry_path: str | Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    requested = str(project_id or "").strip()
    if not requested:
        return {}, [{"kind": "target_project_id_required"}]
    registry, path = _load_registry(registry_path)
    rows = [dict(row) for row in registry.get("projects", []) if isinstance(row, dict) and str(row.get("id") or "") == requested]
    if len(rows) != 1:
        return {}, [{"kind": "target_project_not_found" if not rows else "target_project_id_ambiguous"}]
    project = rows[0]
    root_text = str(project.get("source_root") or project.get("root") or project.get("path") or "").strip()
    if not root_text:
        return {}, [{"kind": "target_project_root_missing"}]
    root = Path(root_text).expanduser()
    if not root.is_absolute():
        base = path.parent if path is not None else Path.cwd()
        root = (base / root).resolve()
    else:
        root = root.resolve()
    project["_resolved_source_root"] = str(root)
    binding = project_source_binding(project)
    findings: list[dict[str, Any]] = []
    if not bool(binding.get("source_root_accessible", root.is_dir())):
        findings.append({"kind": "target_project_root_unavailable"})
    if binding.get("source_identity_matches") is False:
        findings.append({"kind": "target_project_identity_mismatch"})
    return project, findings


def _source_manifest_for_active(runtime_root: str | Path | None, inspection_id: str) -> dict[str, Any]:
    return read_json(handoff_directory(runtime_root) / "manifests" / f"{inspection_id}.source.json")


def _preview_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-installation-preview-binding-v1",
        "preview_id": str(record.get("preview_id") or ""),
        "handoff_generation": int(record.get("handoff_generation") or 0),
        "handoff_record_binding_sha256": str(record.get("handoff_record_binding_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "packaged_version": str(record.get("packaged_version") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_root_binding_sha256": str(record.get("target_root_binding_sha256") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "effects_sha256": str(record.get("effects_sha256") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    effects = row.get("effect_counts") if isinstance(row.get("effect_counts"), dict) else {}
    contradictions = _kind_counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    contradiction_count = sum(int(item["count"]) for item in contradictions)
    return {
        "ok": bool(row.get("ok")) and contradiction_count == 0,
        "status": str(row.get("status") or "not_previewed"),
        "contract_version": INSTALLATION_PREVIEW_CONTRACT_VERSION,
        "preview_present": bool(row),
        "preview_id": str(row.get("preview_id") or ""),
        "preview_binding_sha256": str(row.get("preview_binding_sha256") or ""),
        "handoff_generation": int(row.get("handoff_generation") or 0),
        "candidate_id": str(row.get("candidate_id") or ""),
        "packaged_version": str(row.get("packaged_version") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(row.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_identity_sha256": str(row.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "effects_sha256": str(row.get("effects_sha256") or ""),
        "effect_counts": {key: int(effects.get(key) or 0) for key in ("add", "replace", "remove", "unchanged", "protected", "conflict", "outside-approved-scope")},
        "effect_count": sum(int(value or 0) for value in effects.values()),
        "contradictions": contradictions,
        "contradiction_count": contradiction_count,
        "handoff_revalidated": bool(row.get("handoff_revalidated")),
        "target_revalidated": bool(row.get("target_revalidated")),
        "explicit_target_selected": bool(row.get("explicit_target_selected")),
        "directory_scan_performed": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "read_only_preview": True,
        "installation_apply_available": False,
        "installation_changed": False,
        "project_registry_changed": False,
        "installed": False,
        "approved": False,
        "promoted": False,
        "certified": False,
        "provider_contacted": False,
        "ordinary_conversation_affected": False,
    }


def create_installation_impact_preview(
    target_project_id: str,
    *,
    runtime_root: str | Path | None = None,
    project_registry_path: str | Path | None = None,
) -> dict[str, Any]:
    state = _active_private_state(runtime_root)
    contradictions: list[dict[str, Any]] = []
    if not state.get("ok"):
        contradictions.extend(state.get("findings") or [{"kind": "active_handoff_not_coherent"}])
    record = dict(state.get("record") or {})
    project, project_findings = _exact_registered_project(target_project_id, project_registry_path)
    contradictions.extend(project_findings)

    inspection_id = str(record.get("inspection_id") or "")
    source_manifest = _source_manifest_for_active(runtime_root, inspection_id) if inspection_id else {}
    if not source_manifest or str(source_manifest.get("manifest_sha256") or "") != str(record.get("source_manifest_sha256") or ""):
        contradictions.append({"kind": "handoff_source_manifest_missing_or_mismatched"})

    target_root = Path(str(project.get("_resolved_source_root") or ".")).resolve() if project else Path(".").resolve()
    target_inventory = _target_inventory(target_root) if project else {"ok": False, "entries": [], "digest": "", "findings": []}
    contradictions.extend(target_inventory.get("findings") or [])

    effects: list[dict[str, Any]] = []
    candidate_entries = {
        str(row.get("path") or ""): row
        for row in source_manifest.get("entries", [])
        if isinstance(row, dict) and _safe_relative(str(row.get("path") or ""))
    }
    target_entries = {str(row.get("path") or ""): row for row in target_inventory.get("entries", []) if isinstance(row, dict)}

    for path in sorted(candidate_entries):
        candidate = candidate_entries[path]
        target = target_entries.get(path)
        if _protected(path):
            kind = "protected"
        elif target is None:
            kind = "add"
        elif bool(target.get("protected")):
            kind = "protected"
        elif str(target.get("sha256") or "") == str(candidate.get("package_sha256") or "") and int(target.get("size") or 0) == int(candidate.get("package_size") or 0):
            kind = "unchanged"
        else:
            kind = "replace"
        effects.append({"path": path, "kind": kind, "candidate_sha256": str(candidate.get("package_sha256") or ""), "target_sha256": str((target or {}).get("sha256") or "")})

    for path in sorted(set(target_entries) - set(candidate_entries)):
        target = target_entries[path]
        if bool(target.get("protected")) or _protected(path):
            kind = "protected"
        elif _source_managed(path):
            kind = "remove"
        else:
            kind = "outside-approved-scope"
        effects.append({"path": path, "kind": kind, "candidate_sha256": "", "target_sha256": str(target.get("sha256") or "")})

    counts = Counter(str(row.get("kind") or "conflict") for row in effects)
    if counts.get("conflict"):
        contradictions.append({"kind": "target_conflicts_present", "count": counts["conflict"]})
    if counts.get("outside-approved-scope"):
        contradictions.append({"kind": "outside_approved_scope_present", "count": counts["outside-approved-scope"]})

    target_identity = {
        "project_id": str(project.get("id") or ""),
        "project_name": str(project.get("name") or ""),
        "root_binding": digest_payload({"root": str(target_root)}),
        "identity_markers": sorted(str(item) for item in project.get("source_identity_markers", []) if str(item)),
    }
    effects_material = [{"path": row["path"], "kind": row["kind"], "candidate_sha256": row["candidate_sha256"], "target_sha256": row["target_sha256"]} for row in effects]
    effects_sha = digest_payload({"schema": "eidolon-installation-effects-v1", "effects": effects_material})
    preview_id = f"installation-preview-{digest_payload({'handoff': record.get('record_binding_sha256'), 'target': target_identity, 'effects': effects_sha})[:24]}"
    private_record = {
        "schema": INSTALLATION_PREVIEW_SCHEMA,
        "contract_version": INSTALLATION_PREVIEW_CONTRACT_VERSION,
        "preview_id": preview_id,
        "created_at": utc_now(),
        "ok": not contradictions,
        "status": "coherent_preview" if not contradictions else "attention_required",
        "handoff_generation": int(record.get("record_generation") or 0),
        "handoff_record_binding_sha256": str(record.get("record_binding_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "packaged_version": str(record.get("packaged_version") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "selected_archive_path": str(record.get("selected_archive_path") or ""),
        "extracted_root_path": str(record.get("extracted_root_path") or ""),
        "target_project_id": str(project.get("id") or target_project_id or ""),
        "target_project_name": str(project.get("name") or ""),
        "target_root_path": str(target_root) if project else "",
        "target_root_binding_sha256": str(target_identity["root_binding"]),
        "target_identity_sha256": digest_payload(target_identity),
        "target_inventory_sha256": str(target_inventory.get("digest") or ""),
        "target_file_count": len(target_entries),
        "effects_sha256": effects_sha,
        "effect_counts": {key: int(counts.get(key) or 0) for key in ("add", "replace", "remove", "unchanged", "protected", "conflict", "outside-approved-scope")},
        "effects": effects_material,
        "contradictions": contradictions,
        "handoff_revalidated": bool(state.get("ok")),
        "target_revalidated": bool(target_inventory.get("ok")) and not project_findings,
        "explicit_target_selected": bool(project),
        "read_only_preview": True,
        "content_free": True,
    }
    private_record["preview_binding_sha256"] = _preview_binding(private_record)
    directory = preview_directory(runtime_root)
    atomic_json(directory / "records" / f"{preview_id}.json", private_record)
    if private_record["ok"]:
        atomic_json(directory / "active_preview.json", {
            "schema": INSTALLATION_PREVIEW_SCHEMA,
            "preview_id": preview_id,
            "preview_binding_sha256": private_record["preview_binding_sha256"],
            "target_project_id": private_record["target_project_id"],
            "handoff_generation": private_record["handoff_generation"],
            "content_free": True,
        })
    return _public(private_record)


def installation_impact_preview_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = preview_directory(runtime_root)
    pointer = read_json(directory / "active_preview.json")
    preview_id = str(pointer.get("preview_id") or "")
    if not preview_id:
        return _public({})
    record = read_json(directory / "records" / f"{preview_id}.json")
    if not record:
        return _public({"status": "preview_record_missing", "contradictions": [{"kind": "preview_record_missing"}]})
    contradictions = list(record.get("contradictions") or [])
    if str(pointer.get("preview_binding_sha256") or "") != str(record.get("preview_binding_sha256") or ""):
        contradictions.append({"kind": "preview_pointer_binding_mismatch"})
    if str(record.get("preview_binding_sha256") or "") != _preview_binding(record):
        contradictions.append({"kind": "preview_record_binding_mismatch"})
    state = _active_private_state(runtime_root)
    active = dict(state.get("record") or {})
    if not state.get("ok"):
        contradictions.append({"kind": "active_handoff_stale"})
    if int(active.get("record_generation") or 0) != int(record.get("handoff_generation") or 0):
        contradictions.append({"kind": "handoff_generation_changed"})
    if str(active.get("record_binding_sha256") or "") != str(record.get("handoff_record_binding_sha256") or ""):
        contradictions.append({"kind": "handoff_record_changed"})
    target_root = Path(str(record.get("target_root_path") or "."))
    inventory = _target_inventory(target_root) if str(record.get("target_root_path") or "") else {"digest": "", "ok": False}
    if str(inventory.get("digest") or "") != str(record.get("target_inventory_sha256") or ""):
        contradictions.append({"kind": "target_project_changed_after_preview"})
    current = dict(record)
    current["contradictions"] = contradictions
    current["ok"] = not contradictions
    current["status"] = "coherent_preview" if not contradictions else "stale_preview"
    current["handoff_revalidated"] = bool(state.get("ok"))
    current["target_revalidated"] = bool(inventory.get("ok")) and not any(row.get("kind") == "target_project_changed_after_preview" for row in contradictions)
    return _public(current)
