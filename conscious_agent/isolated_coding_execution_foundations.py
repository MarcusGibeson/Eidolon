from __future__ import annotations

"""v1254.0-v1254.2 foundations for bounded isolated coding work.

This module deliberately stops before implementation execution.  It turns an
explicit coding request into durable request, inspection, plan, and isolated
workspace records inside the existing development-campaign runtime store.  It
never mutates the selected project, runs commands, contacts providers, applies
changes, or grants approval/application authority.
"""

import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from broader_project_language_adapters import _detect as _detect_broader_adapter
from broader_project_language_adapters import _normalize_inventory as _normalize_adapter_inventory
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1254.2"
MAX_REQUEST_TEXT = 12_000
MAX_LIST_ITEMS = 64
MAX_FILES = 6000
MAX_FILE_BYTES = 8 * 1024 * 1024
# Eidolon's source-only tree exceeded the original v1254 prototype budget.
# This remains bounded and matches the retained self-modification file ceiling.
MAX_TOTAL_BYTES = 128 * 1024 * 1024

# Conservative by default: these names commonly contain operator/runtime/private
# material or generated dependency state.  A later bundle may add explicit,
# reviewed opt-ins; Bundle A does not.
EXCLUDED_PARTS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "vendor", "dist", "build",
    "coverage", ".coverage", "data", "runtime", "private", "secrets",
    "credentials", "tokens", "cache", "caches", "logs", "backups",
    "conversations", "memories", "prompts", "responses", "provider_payloads",
    "chroma",
})
EXCLUDED_NAMES = frozenset({
    ".env", ".env.local", ".env.production", "projects.json", "memories.json",
    "thoughts.log", "credentials.json", "secrets.json", "service-account.json",
    "id_rsa", "id_ed25519",
})
EXCLUDED_SUFFIXES = frozenset({".pem", ".p12", ".pfx", ".key", ".pyc", ".pyo", ".log"})
ALLOWED_SUFFIXES = frozenset({
    ".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html",
    ".htm", ".css", ".scss", ".json", ".toml", ".yaml", ".yml", ".md",
    ".txt", ".xml", ".java", ".kt", ".kts", ".cs", ".fs", ".vb", ".rs",
    ".go", ".php", ".sh", ".ps1", ".bat", ".cmd", ".sql",
})
ALLOWED_NAMES = frozenset({
    "package.json", "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg",
    "pytest.ini", "pom.xml", "build.gradle", "build.gradle.kts", "cargo.toml",
    "go.mod", "composer.json", "makefile", "dockerfile",
})
WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)

PREPARATION_CAPABILITIES = {
    "bounded_read_only_inspection_enabled": True,
    "bounded_planning_enabled": True,
    "isolated_workspace_materialization_enabled": True,
}

AUTHORITY_STATE = {
    "implementation_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "provider_contact_authorized": False,
    "dependency_installation_authorized": False,
    "selected_project_mutation_authorized": False,
    "source_application_authorized": False,
    "installation_authorized": False,
    "release_authorized": False,
    "approval_granted": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}


def _clean_text(value: Any, limit: int = MAX_REQUEST_TEXT) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def _clean_list(values: Iterable[Any] | None, *, limit: int = MAX_LIST_ITEMS) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = _clean_text(value, 2_000)
        key = text.casefold()
        if not text or key in seen:
            continue
        rows.append(text)
        seen.add(key)
        if len(rows) >= limit:
            break
    return rows


def _request_dir(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "coding_work_requests"


def _inspection_dir(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "coding_project_inspections"


def _plan_dir(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "coding_work_plans"


def _workspace_record_dir(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "coding_workspace_records"


def _workspace_dir(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "coding_workspaces"


def _request_path(request_id: str, runtime_root=None) -> Path:
    _validate_request_id(request_id)
    return _request_dir(runtime_root) / f"{request_id}.json"


def _inspection_path(request_id: str, runtime_root=None) -> Path:
    _validate_request_id(request_id)
    return _inspection_dir(runtime_root) / f"{request_id}.json"


def _plan_path(request_id: str, runtime_root=None) -> Path:
    _validate_request_id(request_id)
    return _plan_dir(runtime_root) / f"{request_id}.json"


def _workspace_record_path(request_id: str, runtime_root=None) -> Path:
    _validate_request_id(request_id)
    return _workspace_record_dir(runtime_root) / f"{request_id}.json"


def _validate_request_id(request_id: str) -> None:
    if not re.fullmatch(r"devc_[a-f0-9]{24}", str(request_id or "")):
        raise ValueError("invalid_coding_work_request_id")


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _resolve_project_root(raw: str | Path) -> Path:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("target_project_required")
    path = Path(text).expanduser()
    if _is_link_like(path):
        raise ValueError("target_project_link_or_junction_rejected")
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("target_project_not_directory")
    if _is_link_like(root):
        raise ValueError("target_project_link_or_junction_rejected")
    return root


def _is_link_like(path: Path) -> bool:
    """Reject symlinks and Windows reparse points (including junctions)."""
    try:
        if path.is_symlink():
            return True
    except OSError:
        return True
    try:
        stat = os.lstat(path)
    except OSError:
        return False
    attrs = int(getattr(stat, "st_file_attributes", 0) or 0)
    reparse = int(getattr(os, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attrs & reparse)


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def _safe_relative(raw: str) -> str:
    text = str(raw or "").strip().replace("\\", "/")
    if not text or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        raise ValueError("unsafe_relative_path")
    pure = PurePosixPath(text)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("unsafe_relative_path")
    if any(part.casefold() in EXCLUDED_PARTS for part in pure.parts):
        raise ValueError("private_or_excluded_relative_path")
    _validate_portable_relative(pure)
    return pure.as_posix()


def _validate_portable_relative(relative: PurePosixPath) -> None:
    """Reject names that are unsafe or ambiguous on supported Windows hosts."""
    for part in relative.parts:
        if not part or part in {".", ".."} or part.endswith((" ", ".")):
            raise ValueError("nonportable_project_path")
        if any(ord(ch) < 32 for ch in part) or any(ch in '<>:"|?*' for ch in part):
            raise ValueError("nonportable_project_path")
        stem = part.split(".", 1)[0].casefold()
        if stem in WINDOWS_RESERVED_NAMES:
            raise ValueError("windows_reserved_project_path")


def _is_private_or_excluded(relative: PurePosixPath) -> bool:
    lowered = tuple(part.casefold() for part in relative.parts)
    name = relative.name.casefold()
    suffix = relative.suffix.casefold()
    if any(part in EXCLUDED_PARTS for part in lowered):
        return True
    if name in EXCLUDED_NAMES or suffix in EXCLUDED_SUFFIXES:
        return True
    if name.startswith(".env") or "secret" in name or "credential" in name:
        return True
    return False


def _is_relevant_source(relative: PurePosixPath) -> bool:
    name = relative.name.casefold()
    suffix = relative.suffix.casefold()
    return name in ALLOWED_NAMES or suffix in ALLOWED_SUFFIXES


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_digest(relative: str) -> str:
    return hashlib.sha256(relative.encode("utf-8")).hexdigest()


def _walk_project(root: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    files: list[dict[str, Any]] = []
    total = 0
    excluded_private = 0
    excluded_links = 0
    excluded_irrelevant = 0
    stack = [root]
    while stack:
        current = stack.pop()
        if not _within(root, current):
            raise ValueError("project_containment_violation")
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name.casefold())
        except OSError as exc:
            raise ValueError(f"project_scan_failed:{type(exc).__name__}") from exc
        child_dirs: list[Path] = []
        for entry in entries:
            path = Path(entry.path)
            try:
                relative = PurePosixPath(path.relative_to(root).as_posix())
            except ValueError as exc:
                raise ValueError("project_containment_violation") from exc
            _validate_portable_relative(relative)
            if _is_private_or_excluded(relative):
                excluded_private += 1
                continue
            if _is_link_like(path):
                excluded_links += 1
                continue
            if not _within(root, path):
                excluded_links += 1
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    child_dirs.append(path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    excluded_irrelevant += 1
                    continue
            except OSError:
                excluded_links += 1
                continue
            if not _is_relevant_source(relative):
                excluded_irrelevant += 1
                continue
            size = path.stat().st_size
            if size > MAX_FILE_BYTES:
                raise ValueError(f"project_file_too_large:{relative.as_posix()}")
            total += size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("project_total_byte_budget_exceeded")
            rel = relative.as_posix()
            files.append({
                "relative_path": rel,
                "relative_path_digest": _path_digest(rel),
                "content_digest": _file_digest(path),
                "size_bytes": size,
                "suffix": relative.suffix.casefold(),
            })
            if len(files) > MAX_FILES:
                raise ValueError("project_file_count_budget_exceeded")
        stack.extend(reversed(child_dirs))
    files.sort(key=lambda row: str(row["relative_path"]).casefold())
    folded_paths = [str(row.get("relative_path") or "").casefold() for row in files]
    if len(folded_paths) != len(set(folded_paths)):
        raise ValueError("project_casefold_path_collision")
    stats = {
        "file_count": len(files),
        "total_bytes": total,
        "private_or_excluded_count": excluded_private,
        "link_or_boundary_rejection_count": excluded_links,
        "irrelevant_count": excluded_irrelevant,
    }
    return files, stats


def _manifest_digest(files: Sequence[Mapping[str, Any]]) -> str:
    minimized = [
        {
            "relative_path_digest": row.get("relative_path_digest", ""),
            "content_digest": row.get("content_digest", ""),
            "size_bytes": int(row.get("size_bytes") or 0),
        }
        for row in files
    ]
    return _digest(minimized)


def _project_type(files: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    relative_paths = [str(row.get("relative_path") or "") for row in files]
    manifest_digests = {
        PurePosixPath(path).name.casefold(): str(row.get("content_digest") or "")
        for path, row in zip(relative_paths, files)
        if PurePosixPath(path).name.casefold() in {
            "pom.xml", "build.gradle", "build.gradle.kts", "cargo.toml", "go.mod",
            "composer.json", "package.json", "pyproject.toml", "setup.py", "requirements.txt",
        }
    }
    adapter_state: dict[str, Any]
    if relative_paths:
        try:
            normalized = _normalize_adapter_inventory(relative_paths, manifest_digests)
            adapter_state = _detect_broader_adapter(normalized)
        except ValueError:
            adapter_state = {"state": "adapter_unsupported", "reason": "inventory_not_adapter_compatible", "candidate_adapter_ids": []}
    else:
        normalized = {"marker_codes": [], "source_suffixes": []}
        adapter_state = {"state": "adapter_unsupported", "reason": "empty_project", "candidate_adapter_ids": []}

    selected = dict(adapter_state.get("selected_adapter") or {})
    delegated = list(adapter_state.get("delegated_adapter_ids") or adapter_state.get("candidate_adapter_ids") or [])
    suffixes = {str(row.get("suffix") or "") for row in files}
    if selected:
        project_type = str(selected.get("project_kind") or "supported_project")
        adapter = str(selected.get("adapter_id") or "")
    elif adapter_state.get("state") == "adapter_delegated_existing":
        if "python" in delegated:
            project_type, adapter = "python_project", "python"
        elif "node_javascript" in delegated and "browser_runtime" in delegated:
            project_type, adapter = "javascript_web_project", "node_javascript+browser_runtime"
        elif "node_javascript" in delegated:
            project_type, adapter = "javascript_project", "node_javascript"
        elif "browser_runtime" in delegated:
            project_type, adapter = "static_web_project", "browser_runtime"
        else:
            project_type, adapter = "supported_existing_adapter_project", "+".join(delegated)
    elif ".py" in suffixes:
        project_type, adapter = "python_project", "python"
    elif suffixes.intersection({".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}):
        project_type, adapter = "javascript_project", "node_javascript"
    elif suffixes.intersection({".html", ".htm", ".css"}):
        project_type, adapter = "static_web_project", "browser_runtime"
    elif files:
        project_type, adapter = "unclassified_source_project", ""
    else:
        project_type, adapter = "empty_project", ""
    return {
        "project_type": project_type,
        "adapter_id": adapter,
        "adapter_state": str(adapter_state.get("state") or "adapter_unsupported"),
        "adapter_reason": str(adapter_state.get("reason") or ""),
        "candidate_adapter_ids": list(adapter_state.get("candidate_adapter_ids") or []),
        "marker_codes": list(normalized.get("marker_codes") or []),
    }


def _request_identity(
    *,
    user_objective: str,
    target_path_digest: str,
    requirements: Sequence[str],
    acceptance_criteria: Sequence[str],
    constraints: Sequence[str],
    prohibited_actions: Sequence[str],
    ambiguities: Sequence[str],
    assumptions: Sequence[str],
    expected_artifacts: Sequence[str],
    verification: Sequence[str],
    context_paths: Sequence[str],
) -> dict[str, Any]:
    return {
        "user_objective": user_objective,
        "target_path_digest": target_path_digest,
        "requirements": list(requirements),
        "acceptance_criteria": list(acceptance_criteria),
        "constraints": list(constraints),
        "prohibited_actions": list(prohibited_actions),
        "ambiguities": list(ambiguities),
        "assumptions": list(assumptions),
        "expected_artifacts": list(expected_artifacts),
        "verification": list(verification),
        "context_paths": list(context_paths),
    }


def create_or_restore_coding_work_request(
    *,
    user_objective: str,
    target_project: str | Path,
    requirements: Iterable[Any] | None = None,
    acceptance_criteria: Iterable[Any] | None = None,
    constraints: Iterable[Any] | None = None,
    prohibited_actions: Iterable[Any] | None = None,
    ambiguities: Iterable[Any] | None = None,
    assumptions: Iterable[Any] | None = None,
    expected_artifacts: Iterable[Any] | None = None,
    verification: Iterable[Any] | None = None,
    context_paths: Iterable[Any] | None = None,
    runtime_root=None,
) -> dict[str, Any]:
    objective = _clean_text(user_objective)
    if not objective:
        raise ValueError("user_objective_required")
    root = _resolve_project_root(target_project)
    target_digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    reqs = _clean_list(requirements) or [objective]
    acceptance = _clean_list(acceptance_criteria) or ["Requested behavior is implemented and verified in an isolated workspace."]
    limits = _clean_list(constraints)
    forbidden = _clean_list(prohibited_actions)
    for default in (
        "Do not modify the selected project or active Eidolon source tree.",
        "Do not copy private runtime data, secrets, conversations, memories, prompts, responses, logs, or provider payloads.",
        "Do not apply or install a candidate without separate operator authorization.",
    ):
        if default.casefold() not in {item.casefold() for item in forbidden}:
            forbidden.append(default)
    ambiguous = _clean_list(ambiguities)
    assumed = _clean_list(assumptions)
    artifacts = _clean_list(expected_artifacts) or ["Reviewable isolated workspace manifest", "Content-minimized inspection evidence", "Bounded implementation and test plan"]
    checks = _clean_list(verification) or ["Verify source snapshot freshness", "Verify selected project remains unchanged", "Verify isolated workspace contents against manifests"]
    requested_context_paths = _clean_list(context_paths)
    identity = _request_identity(
        user_objective=objective,
        target_path_digest=target_digest,
        requirements=reqs,
        acceptance_criteria=acceptance,
        constraints=limits,
        prohibited_actions=forbidden,
        ambiguities=ambiguous,
        assumptions=assumed,
        expected_artifacts=artifacts,
        verification=checks,
        context_paths=requested_context_paths,
    )
    request_digest = _digest(identity)
    request_id = f"devc_{request_digest[:24]}"
    with _proposal_lock(request_id, runtime_root):
        path = _request_path(request_id, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "record_digest") or existing.get("request_digest") != request_digest:
                return {"ok": False, "status": "coding_work_request_record_invalid", "request_id": request_id, **AUTHORITY_STATE}
            return {**existing, "operation_status": "restored"}
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "coding_work_request_ready",
            "request_id": request_id,
            "request_digest": request_digest,
            "user_objective": objective,
            "target": {
                "mode": "selected_project",
                "private_path": str(root),
                "path_digest": target_digest,
            },
            "requirements": reqs,
            "acceptance_criteria": acceptance,
            "constraints": limits,
            "prohibited_actions": forbidden,
            "authority_state": dict(AUTHORITY_STATE),
            "preparation_capabilities": dict(PREPARATION_CAPABILITIES),
            "ambiguities": ambiguous,
            "assumptions": assumed,
            "expected_artifacts": artifacts,
            "verification": checks,
            "context_paths": requested_context_paths,
            "lifecycle_state": "request_ready",
            "cancelled": False,
            "workspace_created": False,
            "selected_project_modified": False,
            "source_modified": False,
            "provider_contacted": False,
            "commands_executed": False,
            "tests_executed": False,
            **AUTHORITY_STATE,
        }
        record = _sealed(record, "record_digest")
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def load_coding_work_request(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_request_path(request_id, runtime_root))
    return record if record and _valid(record, "record_digest") else {}


def inspect_coding_project(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    _validate_request_id(request_id)
    with _proposal_lock(request_id, runtime_root):
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        if not request:
            return {"ok": False, "status": "coding_work_request_missing_or_tampered", "request_id": request_id, **AUTHORITY_STATE}
        if request.get("cancelled"):
            return {"ok": False, "status": "coding_work_request_cancelled", "request_id": request_id, **AUTHORITY_STATE}
        path = _inspection_path(request_id, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "inspection_digest") or existing.get("request_digest") != request.get("request_digest"):
                return {"ok": False, "status": "coding_project_inspection_record_invalid", "request_id": request_id, **AUTHORITY_STATE}
            return {**existing, "operation_status": "restored"}
        root = _resolve_project_root((request.get("target") or {}).get("private_path") or "")
        files, stats = _walk_project(root)
        project = _project_type(files)
        source_manifest_digest = _manifest_digest(files)
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "coding_project_inspection_ready",
            "request_id": request_id,
            "request_digest": request.get("request_digest"),
            "target_path_digest": (request.get("target") or {}).get("path_digest", ""),
            "project_type": project["project_type"],
            "adapter_id": project["adapter_id"],
            "adapter_state": project["adapter_state"],
            "adapter_reason": project["adapter_reason"],
            "candidate_adapter_ids": project["candidate_adapter_ids"],
            "marker_codes": project["marker_codes"],
            "source_manifest_digest": source_manifest_digest,
            "inventory": files,
            "inventory_digest": _digest([
                {key: row[key] for key in ("relative_path_digest", "content_digest", "size_bytes")}
                for row in files
            ]),
            **stats,
            "content_minimized": True,
            "preparation_capabilities": dict(PREPARATION_CAPABILITIES),
            "raw_file_contents_stored": False,
            "private_paths_publicly_exposed": False,
            "selected_project_modified": False,
            "source_modified": False,
            "provider_contacted": False,
            "commands_executed": False,
            "tests_executed": False,
            **AUTHORITY_STATE,
        }
        record = _sealed(record, "inspection_digest")
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def load_coding_project_inspection(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_inspection_path(request_id, runtime_root))
    return record if record and _valid(record, "inspection_digest") else {}


def check_coding_source_freshness(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
    if not request or not inspection:
        return {"ok": False, "status": "request_or_inspection_missing", "request_id": request_id, **AUTHORITY_STATE}
    try:
        root = _resolve_project_root((request.get("target") or {}).get("private_path") or "")
        files, _ = _walk_project(root)
        current = _manifest_digest(files)
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": "source_unavailable_or_boundary_rejected", "reason": str(exc), "request_id": request_id, **AUTHORITY_STATE}
    expected = str(inspection.get("source_manifest_digest") or "")
    fresh = bool(current and current == expected)
    result = {
        "ok": fresh,
        "status": "source_snapshot_fresh" if fresh else "stale_source_detected",
        "request_id": request_id,
        "expected_source_manifest_digest": expected,
        "current_source_manifest_digest": current,
        "stale_source": not fresh,
        "selected_project_modified": False,
        "source_modified": False,
        **AUTHORITY_STATE,
    }
    result["freshness_digest"] = _digest(result)
    return result


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]{3,}", text.casefold()) if token not in {"the", "and", "for", "with", "that", "this", "from", "into", "should"}}


def _candidate_files_for_requirement(requirement: str, inventory: Sequence[Mapping[str, Any]]) -> list[str]:
    terms = _tokens(requirement)
    scored: list[tuple[int, str]] = []
    for row in inventory:
        rel = str(row.get("relative_path") or "")
        path_terms = _tokens(rel.replace("/", " ").replace(".", " "))
        score = len(terms.intersection(path_terms))
        if score:
            scored.append((score, rel))
    if not scored:
        preferred = [
            str(row.get("relative_path") or "")
            for row in inventory
            if PurePosixPath(str(row.get("relative_path") or "")).suffix.casefold() in {
                ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cs", ".rs", ".go", ".php", ".html", ".css"
            }
        ]
        return preferred[:4]
    return [path for _, path in sorted(scored, key=lambda item: (-item[0], item[1].casefold()))[:4]]


def create_or_restore_coding_work_plan(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    _validate_request_id(request_id)
    with _proposal_lock(request_id, runtime_root):
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
        if not request or not inspection:
            return {"ok": False, "status": "request_or_inspection_missing", "request_id": request_id, **AUTHORITY_STATE}
        if request.get("cancelled"):
            return {"ok": False, "status": "coding_work_request_cancelled", "request_id": request_id, **AUTHORITY_STATE}
        freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
        if not freshness.get("ok"):
            return {"ok": False, "status": freshness.get("status", "stale_source_detected"), "request_id": request_id, **AUTHORITY_STATE}
        path = _plan_path(request_id, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "plan_digest") or existing.get("source_manifest_digest") != inspection.get("source_manifest_digest"):
                return {"ok": False, "status": "coding_work_plan_record_invalid", "request_id": request_id, **AUTHORITY_STATE}
            return {**existing, "operation_status": "restored"}

        inventory = list(inspection.get("inventory") or [])
        inventory_paths = {str(row.get("relative_path") or "") for row in inventory}
        context_paths = [
            path for path in request.get("context_paths") or []
            if _safe_relative(path) in inventory_paths
        ]
        requirement_links = []
        for index, requirement in enumerate(request.get("requirements") or [], 1):
            candidates = _candidate_files_for_requirement(str(requirement), inventory)
            requirement_links.append({
                "requirement_index": index,
                "requirement_digest": hashlib.sha256(str(requirement).encode("utf-8")).hexdigest(),
                "candidate_files": candidates,
                "candidate_file_path_digests": [_path_digest(path) for path in candidates],
                "link_basis": "bounded_filename_term_match" if candidates else "no_relevant_file_identified",
            })
        steps = [
            {
                "step": 1,
                "kind": "inspect",
                "description": "Use the sealed content-minimized project snapshot and request contract as the implementation basis.",
                "input_digest": inspection.get("inspection_digest", ""),
            },
            {
                "step": 2,
                "kind": "implement_in_isolation",
                "description": "Modify only the disposable workspace in a later authorized execution stage; never the selected project.",
                "input_digest": inspection.get("source_manifest_digest", ""),
            },
            {
                "step": 3,
                "kind": "verify",
                "description": "Run only separately authorized focused verification in the isolated workspace and record evidence.",
                "input_digest": request.get("request_digest", ""),
            },
            {
                "step": 4,
                "kind": "review",
                "description": "Present a reviewable diff/evidence packet; do not apply it to the selected project.",
                "input_digest": request.get("request_digest", ""),
            },
        ]
        plan = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "coding_work_plan_ready",
            "request_id": request_id,
            "request_digest": request.get("request_digest", ""),
            "inspection_digest": inspection.get("inspection_digest", ""),
            "source_manifest_digest": inspection.get("source_manifest_digest", ""),
            "project_type": inspection.get("project_type", ""),
            "adapter_id": inspection.get("adapter_id", ""),
            "requirement_file_links": requirement_links,
            "implementation_steps": steps,
            "verification_plan": list(request.get("verification") or []),
            "context_paths": context_paths,
            "expected_artifacts": list(request.get("expected_artifacts") or []),
            "acceptance_criteria": list(request.get("acceptance_criteria") or []),
            "assumptions": list(request.get("assumptions") or []),
            "ambiguities": list(request.get("ambiguities") or []),
            "uncertainty_state": "operator_review_required" if request.get("ambiguities") else "bounded_assumptions_recorded",
            "completion_conditions": [
                "All acceptance criteria have corresponding verification evidence.",
                "The isolated workspace manifest matches the reviewed result.",
                "The selected project source manifest is still fresh at handoff.",
                "No selected-project application has occurred.",
            ],
            "blocker_conditions": [
                "Source snapshot becomes stale or unavailable.",
                "A path escapes project/workspace containment or traverses a link/junction.",
                "Private/runtime data would need to be copied.",
                "A required action needs authority not granted by this contract.",
                "Required verification cannot be run safely or deterministically.",
            ],
            "plan_grants_execution_authority": False,
            "plan_grants_application_authority": False,
            "preparation_capabilities": dict(PREPARATION_CAPABILITIES),
            "selected_project_modified": False,
            "source_modified": False,
            "provider_contacted": False,
            "commands_executed": False,
            "tests_executed": False,
            **AUTHORITY_STATE,
        }
        plan = _sealed(plan, "plan_digest")
        _atomic_json(path, plan)
        return {**plan, "operation_status": "created"}


def load_coding_work_plan(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_plan_path(request_id, runtime_root))
    return record if record and _valid(record, "plan_digest") else {}


def materialize_or_restore_isolated_coding_workspace(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    _validate_request_id(request_id)
    with _proposal_lock(request_id, runtime_root):
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
        plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
        if not request or not inspection or not plan:
            return {"ok": False, "status": "request_inspection_or_plan_missing", "request_id": request_id, **AUTHORITY_STATE}
        if request.get("cancelled"):
            return {"ok": False, "status": "coding_work_request_cancelled", "request_id": request_id, **AUTHORITY_STATE}
        freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
        if not freshness.get("ok"):
            return {"ok": False, "status": freshness.get("status", "stale_source_detected"), "request_id": request_id, **AUTHORITY_STATE}
        record_path = _workspace_record_path(request_id, runtime_root)
        existing = _read_json(record_path)
        if existing:
            if not _valid(existing, "workspace_record_digest"):
                return {"ok": False, "status": "coding_workspace_record_invalid", "request_id": request_id, **AUTHORITY_STATE}
            root = Path(str(existing.get("workspace_path") or ""))
            if _workspace_matches_record(root, existing):
                return {**existing, "operation_status": "restored"}
            return {"ok": False, "status": "coding_workspace_contents_changed", "request_id": request_id, **AUTHORITY_STATE}

        source_root = _resolve_project_root((request.get("target") or {}).get("private_path") or "")
        workspace_root = _workspace_dir(runtime_root) / request_id / str(inspection.get("source_manifest_digest") or "")[:16]
        if workspace_root.exists():
            return {"ok": False, "status": "coding_workspace_collision", "request_id": request_id, **AUTHORITY_STATE}
        workspace_root.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=str(workspace_root.parent)))
        try:
            copied: list[dict[str, Any]] = []
            for row in inspection.get("inventory") or []:
                relative = _safe_relative(str(row.get("relative_path") or ""))
                src = source_root / Path(*PurePosixPath(relative).parts)
                if _is_link_like(src) or not _within(source_root, src) or not src.is_file():
                    return {"ok": False, "status": "source_boundary_changed", "request_id": request_id, **AUTHORITY_STATE}
                if _file_digest(src) != row.get("content_digest"):
                    return {"ok": False, "status": "stale_source_detected", "request_id": request_id, **AUTHORITY_STATE}
                dst = staging / Path(*PurePosixPath(relative).parts)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                if _file_digest(dst) != row.get("content_digest"):
                    return {"ok": False, "status": "workspace_copy_digest_mismatch", "request_id": request_id, **AUTHORITY_STATE}
                copied.append({
                    "relative_path": relative,
                    "relative_path_digest": row.get("relative_path_digest", ""),
                    "content_digest": row.get("content_digest", ""),
                    "size_bytes": int(row.get("size_bytes") or 0),
                })
            os.replace(staging, workspace_root)
            staging = None
            workspace_manifest_digest = _manifest_digest(copied)
            record = {
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "ok": True,
                "status": "isolated_coding_workspace_ready",
                "request_id": request_id,
                "request_digest": request.get("request_digest", ""),
                "inspection_digest": inspection.get("inspection_digest", ""),
                "plan_digest": plan.get("plan_digest", ""),
                "source_manifest_digest": inspection.get("source_manifest_digest", ""),
                "workspace_manifest_digest": workspace_manifest_digest,
                "workspace_path": str(workspace_root),
                "workspace_id": hashlib.sha256(str(workspace_root).encode("utf-8")).hexdigest(),
                "files": copied,
                "file_count": len(copied),
                "total_bytes": sum(int(row.get("size_bytes") or 0) for row in copied),
                "reviewable_result_only": True,
                "workspace_disposable": True,
                "preparation_capabilities": dict(PREPARATION_CAPABILITIES),
                "cleanup_supported": True,
                "selected_project_modified": False,
                "source_modified": False,
                "provider_contacted": False,
                "commands_executed": False,
                "tests_executed": False,
                **AUTHORITY_STATE,
            }
            record = _sealed(record, "workspace_record_digest")
            _atomic_json(record_path, record)
            request["workspace_created"] = True
            request["lifecycle_state"] = "isolated_workspace_ready"
            request = _sealed(request, "record_digest")
            _atomic_json(_request_path(request_id, runtime_root), request)
            return {**record, "operation_status": "created"}
        finally:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)


def _workspace_matches_record(root: Path, record: Mapping[str, Any]) -> bool:
    try:
        if not root.is_dir() or _is_link_like(root):
            return False
        expected = list(record.get("files") or [])
        actual: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                if _is_link_like(path):
                    return False
                continue
            if _is_link_like(path) or not path.is_file() or not _within(root, path):
                return False
            rel = path.relative_to(root).as_posix()
            actual.append({
                "relative_path": rel,
                "relative_path_digest": _path_digest(rel),
                "content_digest": _file_digest(path),
                "size_bytes": path.stat().st_size,
            })
        return actual == expected and _manifest_digest(actual) == record.get("workspace_manifest_digest")
    except (OSError, ValueError):
        return False


def cancel_coding_work_request(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    _validate_request_id(request_id)
    with _proposal_lock(request_id, runtime_root):
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        if not request:
            return {"ok": False, "status": "coding_work_request_missing_or_tampered", "request_id": request_id, **AUTHORITY_STATE}
        workspace_record = _read_json(_workspace_record_path(request_id, runtime_root))
        workspace_path = Path(str(workspace_record.get("workspace_path") or "")) if workspace_record else None
        root = _workspace_dir(runtime_root).resolve()
        cleaned = False
        if workspace_path and str(workspace_path):
            try:
                resolved = workspace_path.resolve(strict=False)
                if resolved == root or root not in resolved.parents:
                    return {"ok": False, "status": "workspace_cleanup_boundary_rejected", "request_id": request_id, **AUTHORITY_STATE}
                if resolved.exists():
                    shutil.rmtree(resolved)
                    cleaned = True
                parent = resolved.parent
                workspace_store = _workspace_dir(runtime_root).resolve()
                if parent != workspace_store and parent.parent == workspace_store:
                    try:
                        parent.rmdir()
                    except OSError:
                        pass
            except OSError:
                return {"ok": False, "status": "workspace_cleanup_failed", "request_id": request_id, **AUTHORITY_STATE}
        request["cancelled"] = True
        request["lifecycle_state"] = "cancelled"
        request["workspace_created"] = False
        request = _sealed(request, "record_digest")
        _atomic_json(_request_path(request_id, runtime_root), request)
        if workspace_record:
            workspace_record["status"] = "isolated_coding_workspace_cleaned"
            workspace_record["workspace_cleaned"] = True
            workspace_record["workspace_path"] = ""
            workspace_record["files"] = []
            workspace_record["workspace_manifest_digest"] = _manifest_digest([])
            workspace_record["file_count"] = 0
            workspace_record["total_bytes"] = 0
            workspace_record = _sealed(workspace_record, "workspace_record_digest")
            _atomic_json(_workspace_record_path(request_id, runtime_root), workspace_record)
        return {
            "ok": True,
            "status": "coding_work_request_cancelled",
            "request_id": request_id,
            "workspace_cleaned": cleaned or not (workspace_path and workspace_path.exists()),
            "selected_project_modified": False,
            "source_modified": False,
            **AUTHORITY_STATE,
        }


def public_coding_work_request(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": record.get("status", ""),
        "request_id": record.get("request_id", ""),
        "request_digest": record.get("request_digest", ""),
        "target_path_digest": (record.get("target") or {}).get("path_digest", ""),
        "requirement_count": len(record.get("requirements") or []),
        "acceptance_criteria_count": len(record.get("acceptance_criteria") or []),
        "constraint_count": len(record.get("constraints") or []),
        "prohibited_action_count": len(record.get("prohibited_actions") or []),
        "ambiguity_count": len(record.get("ambiguities") or []),
        "assumption_count": len(record.get("assumptions") or []),
        "expected_artifact_count": len(record.get("expected_artifacts") or []),
        "verification_item_count": len(record.get("verification") or []),
        "lifecycle_state": record.get("lifecycle_state", ""),
        "private_path_exposed": False,
        "request_text_exposed": False,
        **AUTHORITY_STATE,
    }


def public_coding_project_inspection(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": record.get("status", ""),
        "request_id": record.get("request_id", ""),
        "project_type": record.get("project_type", ""),
        "adapter_id": record.get("adapter_id", ""),
        "source_manifest_digest": record.get("source_manifest_digest", ""),
        "inventory_digest": record.get("inventory_digest", ""),
        "file_count": int(record.get("file_count") or 0),
        "total_bytes": int(record.get("total_bytes") or 0),
        "private_or_excluded_count": int(record.get("private_or_excluded_count") or 0),
        "link_or_boundary_rejection_count": int(record.get("link_or_boundary_rejection_count") or 0),
        "file_path_digests": [str(row.get("relative_path_digest") or "") for row in record.get("inventory") or []],
        "file_content_digests": [str(row.get("content_digest") or "") for row in record.get("inventory") or []],
        "raw_paths_exposed": False,
        "raw_file_contents_exposed": False,
        "private_path_exposed": False,
        **AUTHORITY_STATE,
    }


def public_coding_work_plan(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": record.get("status", ""),
        "request_id": record.get("request_id", ""),
        "project_type": record.get("project_type", ""),
        "adapter_id": record.get("adapter_id", ""),
        "source_manifest_digest": record.get("source_manifest_digest", ""),
        "requirement_link_count": len(record.get("requirement_file_links") or []),
        "implementation_step_count": len(record.get("implementation_steps") or []),
        "verification_item_count": len(record.get("verification_plan") or []),
        "acceptance_criteria_count": len(record.get("acceptance_criteria") or []),
        "ambiguity_count": len(record.get("ambiguities") or []),
        "plan_digest": record.get("plan_digest", ""),
        "plan_grants_execution_authority": False,
        "plan_grants_application_authority": False,
        "private_content_exposed": False,
        **AUTHORITY_STATE,
    }


def public_isolated_coding_workspace(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": record.get("status", ""),
        "request_id": record.get("request_id", ""),
        "workspace_id": record.get("workspace_id", ""),
        "source_manifest_digest": record.get("source_manifest_digest", ""),
        "workspace_manifest_digest": record.get("workspace_manifest_digest", ""),
        "file_count": int(record.get("file_count") or 0),
        "total_bytes": int(record.get("total_bytes") or 0),
        "reviewable_result_only": True,
        "workspace_disposable": True,
        "workspace_path_exposed": False,
        "raw_paths_exposed": False,
        "private_content_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        **AUTHORITY_STATE,
    }


__all__ = [
    "AUTHORITY_STATE",
    "PREPARATION_CAPABILITIES",
    "CONTRACT_VERSION",
    "create_or_restore_coding_work_request",
    "load_coding_work_request",
    "inspect_coding_project",
    "load_coding_project_inspection",
    "check_coding_source_freshness",
    "create_or_restore_coding_work_plan",
    "load_coding_work_plan",
    "materialize_or_restore_isolated_coding_workspace",
    "cancel_coding_work_request",
    "public_coding_work_request",
    "public_coding_project_inspection",
    "public_coding_work_plan",
    "public_isolated_coding_workspace",
]
