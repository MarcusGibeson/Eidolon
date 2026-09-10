from __future__ import annotations

"""v1265.0-v1265.2 foundations for isolated self-modification.

A validated v1264 plan may materialize a source-only clean copy of Eidolon in
external runtime storage.  The active source tree is read-only.  This module
creates no provider, execution, application, installation, release, or
self-update authority.
"""

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from alternative_planning_foundations import validate_alternative_plan
from ordinary_chat_development_campaign import _proposal_lock
from package_integrity import forbidden_runtime_path_matches, source_package_bytes

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1265.2"
MAX_SOURCE_FILES = 6000
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_RUNTIME_RECORD_BYTES = 4 * 1024 * 1024
NON_MUTATION_CATEGORIES = frozenset({"evidence_acquisition", "evidence_resolution"})
IGNORED_PARTS = frozenset({".git", ".hg", ".svn", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
IGNORED_SUFFIXES = frozenset({".pyc", ".pyo", ".log", ".zip"})

SELF_MODIFICATION_DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "active_source_mutation_authorized": False,
    "selected_project_mutation_authorized": False,
    "source_application_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "self_update_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(256 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _runtime_root(runtime_root: str | Path | None) -> Path:
    if runtime_root is None:
        raise ValueError("isolated_self_modification_runtime_root_required")
    return Path(runtime_root).expanduser().resolve()


def _base_dir(runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "isolated_self_modification"


def _record_path(operation_id: str, runtime_root: str | Path | None) -> Path:
    if not re.fullmatch(r"selfmod_[a-f0-9]{24}", str(operation_id or "")):
        raise ValueError("invalid_self_modification_operation_id")
    return _base_dir(runtime_root) / "records" / f"{operation_id}.json"


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    data = (json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    if len(data) > MAX_RUNTIME_RECORD_BYTES:
        raise ValueError("isolated_self_modification_record_too_large")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, suffix=".tmp") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno()); tmp = Path(handle.name)
        os.replace(tmp, path); tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_RUNTIME_RECORD_BYTES:
        raise ValueError("isolated_self_modification_record_too_large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("isolated_self_modification_record_invalid")
    return value


def _is_link_like(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        st = os.lstat(path)
    except OSError:
        return True
    attrs = int(getattr(st, "st_file_attributes", 0) or 0)
    return bool(attrs & int(getattr(os, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def _safe_relative(raw: str) -> str:
    text = str(raw or "").strip().replace("\\", "/")
    pure = PurePosixPath(text)
    if not text or pure.is_absolute() or re.match(r"^[A-Za-z]:", text) or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("unsafe_self_modification_relative_path")
    if any(part.casefold() in IGNORED_PARTS for part in pure.parts) or pure.suffix.casefold() in IGNORED_SUFFIXES:
        raise ValueError("excluded_self_modification_relative_path")
    if pure.parts and pure.parts[0].casefold() == "data":
        raise ValueError("private_runtime_self_modification_path_rejected")
    return pure.as_posix()


def _source_identity(root: Path) -> bool:
    return (
        (root / "conscious_agent" / "release_authority.py").is_file()
        and (root / "conscious_agent" / "package_integrity.py").is_file()
        and (root / "README_NEXT_STEPS.md").is_file()
    )


def _validated_source_paths(root: Path) -> list[Path]:
    source_paths: list[Path] = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        parent = Path(current)
        retained_dirs: list[str] = []
        for name in dirs:
            if name.casefold() in IGNORED_PARTS or (parent == root and name.casefold() == "data"):
                continue
            path = parent / name
            if _is_link_like(path):
                raise ValueError("self_source_link_or_reparse_rejected")
            retained_dirs.append(name)
        dirs[:] = sorted(retained_dirs, key=str.casefold)
        for name in files:
            path = parent / name
            if path.suffix.casefold() not in IGNORED_SUFFIXES:
                source_paths.append(path)
    return sorted(source_paths, key=lambda p: p.relative_to(root).as_posix().casefold())


def _manifest_from_paths(root: Path, source_paths: Iterable[Path], content_digests: Mapping[str, str] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    folded: set[str] = set()
    supplied = {str(key): str(value).casefold() for key, value in (content_digests or {}).items()}
    actual_paths: set[str] = set()
    for path in source_paths:
        rel = path.relative_to(root).as_posix()
        if _is_link_like(path):
            raise ValueError("self_source_link_or_reparse_rejected")
        if not path.is_file():
            raise ValueError("self_source_special_file_rejected")
        if forbidden_runtime_path_matches([rel]):
            raise ValueError("self_source_private_runtime_entry_rejected")
        key = rel.casefold()
        if key in folded:
            raise ValueError("self_source_casefold_collision")
        folded.add(key)
        actual_paths.add(rel)
        size = path.stat().st_size
        total += size
        if len(rows) + 1 > MAX_SOURCE_FILES or total > MAX_SOURCE_BYTES:
            raise ValueError("self_source_inventory_bound_exceeded")
        content_digest = supplied.get(rel) if content_digests is not None else _file_digest(path)
        if not content_digest or not re.fullmatch(r"[a-f0-9]{64}", content_digest):
            raise ValueError("self_source_preverified_digest_invalid")
        rows.append({"relative_path": rel, "size_bytes": size, "content_digest": content_digest})
    if content_digests is not None and actual_paths != set(supplied):
        raise ValueError("self_source_preverified_manifest_paths_mismatch")
    digest = _digest(rows)
    return {"files": rows, "file_count": len(rows), "total_bytes": total, "source_manifest_digest": digest}


def source_only_manifest(source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    if not root.is_dir() or _is_link_like(root):
        raise ValueError("self_source_root_invalid")
    return _manifest_from_paths(root, _validated_source_paths(root))


def source_only_manifest_from_content_digests(source_root: str | Path, content_digests: Mapping[str, str]) -> dict[str, Any]:
    """Rebind a just-verified content map to the strict source-only contract."""
    root = Path(source_root).expanduser().resolve(strict=True)
    if not root.is_dir() or _is_link_like(root):
        raise ValueError("self_source_root_invalid")
    return _manifest_from_paths(root, _validated_source_paths(root), content_digests)


def _copy_manifest(source_root: Path, workspace_root: Path, manifest: Mapping[str, Any]) -> None:
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=False)
    for row in manifest.get("files") or []:
        rel = _safe_relative(str(row.get("relative_path") or ""))
        target = workspace_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source_package_bytes(source_root, rel))


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in record.items() if k not in {"record_digest", "operation_status", "provider_called_this_invocation"}})


def validate_self_modification_foundation(record: Mapping[str, Any]) -> dict[str, Any]:
    digest_ok = bool(record.get("record_digest")) and str(record.get("record_digest")) == _record_digest(record)
    authority_ok = all(record.get(k) is v for k, v in SELF_MODIFICATION_DENIED_AUTHORITY.items())
    semantic = (
        str(record.get("operation_id") or "").startswith("selfmod_")
        and bool(record.get("source_manifest_digest"))
        and bool(record.get("workspace_baseline_manifest_digest"))
        and record.get("active_source_modified") is False
        and record.get("isolated_workspace_modified") is False
        and record.get("operator_review_required") is True
    )
    ok = digest_ok and authority_ok and semantic
    return {"ok": ok, "status": "isolated_self_modification_foundation_valid" if ok else "isolated_self_modification_foundation_invalid", "digest_valid": digest_ok, "authority_denied": authority_ok, "semantic_valid": semantic}


def prepare_isolated_self_modification(
    source_root: str | Path,
    plan: Mapping[str, Any],
    selection: Mapping[str, Any],
    backlog: Mapping[str, Any],
    *,
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    if not _source_identity(root):
        raise ValueError("source_is_not_eidolon")
    plan_validation = validate_alternative_plan(plan, selection, backlog)
    if not plan_validation.get("ok"):
        raise ValueError("invalid_v1264_plan")
    if str(plan.get("status") or "") != "alternative_plan_selected" or not plan.get("selected_approach_id"):
        raise ValueError("unique_v1264_plan_required")
    if str(plan.get("category") or "") in NON_MUTATION_CATEGORIES:
        return {
            "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "status": "self_modification_not_applicable_read_only_plan", "plan_digest": plan.get("plan_digest", ""),
            "mutation_candidate": False, "active_source_modified": False, "isolated_workspace_modified": False,
            "operator_review_required": True, **SELF_MODIFICATION_DENIED_AUTHORITY,
        }
    manifest = source_only_manifest(root)
    if str(plan.get("source_manifest_digest") or "") != str(backlog.get("source_manifest_digest") or ""):
        raise ValueError("plan_backlog_source_binding_invalid")
    # v1261/v1262 source manifests use their own bounded evidence inventory and are
    # intentionally not identical to this source-only copy manifest.  Bind both.
    operation_id = "selfmod_" + hashlib.sha256(f"{plan.get('plan_digest')}:{manifest['source_manifest_digest']}".encode()).hexdigest()[:24]
    path = _record_path(operation_id, runtime_root)
    with _proposal_lock("devc_" + operation_id.split("_", 1)[1], _runtime_root(runtime_root)):
        existing = _read_json(path)
        if existing:
            if not validate_self_modification_foundation(existing).get("ok") and existing.get("phase") == "prepared":
                raise ValueError("stored_self_modification_record_invalid")
            return {**existing, "operation_status": "restored"}
        workspace = _base_dir(runtime_root) / "workspaces" / operation_id / "Eidolon"
        _copy_manifest(root, workspace, manifest)
        copied = source_only_manifest(workspace)
        if copied["source_manifest_digest"] != manifest["source_manifest_digest"]:
            shutil.rmtree(workspace.parent, ignore_errors=True)
            raise ValueError("self_modification_workspace_copy_mismatch")
        selected = next(row for row in plan.get("approaches") or [] if row.get("approach_id") == plan.get("selected_approach_id"))
        record = {
            "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "status": "isolated_self_modification_authorization_required", "phase": "prepared",
            "operation_id": operation_id, "plan_digest": str(plan.get("plan_digest") or ""),
            "selection_digest": str(selection.get("selection_digest") or ""), "backlog_digest": str(backlog.get("backlog_digest") or ""),
            "assessment_digest": str(backlog.get("assessment_digest") or ""),
            "planning_source_manifest_digest": str(plan.get("source_manifest_digest") or ""),
            "source_manifest_digest": manifest["source_manifest_digest"], "source_file_count": manifest["file_count"], "source_total_bytes": manifest["total_bytes"],
            "workspace_baseline_manifest_digest": copied["source_manifest_digest"], "workspace_path": str(workspace),
            "selected_approach_id": str(plan.get("selected_approach_id") or ""), "selected_strategy_code": str(selected.get("strategy_code") or ""),
            "selected_approach_digest": str(selected.get("approach_digest") or ""), "objective_code": str(plan.get("objective_code") or ""), "category": str(plan.get("category") or ""),
            "authorization_phrase": "", "mutation_candidate": True, "operator_review_required": True,
            "active_source_modified": False, "isolated_workspace_modified": False, "provider_contacted": False, "tests_executed": False,
            "candidate_review_available": False, "content_minimized": True, **SELF_MODIFICATION_DENIED_AUTHORITY,
        }
        auth_digest = _digest({k: record[k] for k in ("operation_id", "plan_digest", "source_manifest_digest", "workspace_baseline_manifest_digest", "selected_approach_digest")})
        record["authorization_digest"] = auth_digest
        record["authorization_phrase"] = f"Authorize isolated self-modification {operation_id} digest {auth_digest}."
        record["record_digest"] = _record_digest(record)
        _write_json(path, record)
        return {**record, "operation_status": "created"}


def load_self_modification(operation_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return _read_json(_record_path(operation_id, runtime_root))


def check_self_source_freshness(operation_id: str, source_root: str | Path, *, runtime_root: str | Path | None) -> dict[str, Any]:
    record = load_self_modification(operation_id, runtime_root=runtime_root)
    if not record:
        return {"ok": False, "status": "self_modification_record_missing"}
    current = source_only_manifest(source_root)
    ok = current["source_manifest_digest"] == record.get("source_manifest_digest")
    return {"ok": ok, "status": "self_source_current" if ok else "stale_self_source_detected", "expected_source_manifest_digest": record.get("source_manifest_digest", ""), "current_source_manifest_digest": current["source_manifest_digest"]}


def public_self_modification_foundation(record: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in {"workspace_path", "authorization_phrase"}}


__all__ = [
    "CONTRACT_VERSION", "SELF_MODIFICATION_DENIED_AUTHORITY", "source_only_manifest", "prepare_isolated_self_modification",
    "load_self_modification", "check_self_source_freshness", "validate_self_modification_foundation", "public_self_modification_foundation",
    "_digest", "_record_digest", "_write_json", "_record_path", "_runtime_root", "_safe_relative", "_is_link_like",
]
