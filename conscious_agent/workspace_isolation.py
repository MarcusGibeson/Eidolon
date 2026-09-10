from __future__ import annotations
"""v1333 disposable candidate-workspace creation and deterministic cleanup.

The ordinary-chat surface is inspection-only. Materialization is a separately
invoked operation that requires an active v1302 standing-session grant bound to
the exact selected workspace plus a sealed, satisfied v1332 tool-precondition
record. Filesystem copies live only under the external runtime root. Optional
Git worktrees/branches use argv-only Git calls and explicitly report repository
metadata mutation; they never imply source application or release authority.
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from standing_session_grants import standing_session_allows
from tool_preconditions import load_tool_preconditions

CONTRACT_VERSION = "v1333.8"
ISOLATION_MODES = ("filesystem_copy", "git_worktree", "git_branch_worktree")
RETENTION_RULES = ("discard_on_close", "retain_for_review")
MAX_FILES = 20_000
MAX_SINGLE_FILE_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 512 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 20
EXCLUDED_PARTS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "data", "runtime", "private",
    "secrets", "credentials", "tokens", "cache", "caches", "logs", "backups",
    "conversations", "memories", "provider_payloads", "dist", "build", "coverage", "vendor",
})
EXCLUDED_NAMES = frozenset({".git", ".env", ".env.local", ".env.production", "credentials.json", "secrets.json"})
EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo", ".log", ".pem", ".p12", ".pfx", ".key"})
WORKSPACE_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "tool_execution_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "release_authorized": False,
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase4_workspace_isolation"


def _record_path(workspace_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"iso_[a-f0-9]{24}", str(workspace_id or "")):
        raise ValueError("invalid_workspace_id")
    return _root(runtime_root) / "records" / f"{workspace_id}.json"


def _private_workspace_root(workspace_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "workspaces" / workspace_id


def _is_link_like(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        stat = os.lstat(path)
    except OSError:
        return False
    attrs = int(getattr(stat, "st_file_attributes", 0) or 0)
    reparse = int(getattr(os, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attrs & reparse)


def _resolve_source(source_root: str | Path) -> Path:
    raw = Path(source_root).expanduser()
    if _is_link_like(raw):
        raise ValueError("source_link_or_junction_rejected")
    root = raw.resolve(strict=True)
    if not root.is_dir() or _is_link_like(root):
        raise ValueError("source_workspace_invalid")
    return root


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def _safe_runtime_boundary(source: Path, runtime_root=None) -> Path:
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root else _root(runtime_root).parents[1].resolve()
    # Isolation must be external to the selected source and cannot contain it.
    if runtime == source or _within(source, runtime) or _within(runtime, source):
        raise ValueError("runtime_root_must_be_external_to_source")
    runtime.mkdir(parents=True, exist_ok=True)
    if _is_link_like(runtime):
        raise ValueError("runtime_root_link_or_junction_rejected")
    return runtime


def _allowed_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part.casefold() in EXCLUDED_PARTS for part in rel.parts):
        return False
    name = rel.name.casefold()
    if name in EXCLUDED_NAMES or rel.suffix.casefold() in EXCLUDED_SUFFIXES:
        return False
    return True


def _inventory(root: Path, max_total_bytes: int) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    total = 0
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base_path = Path(base)
        kept_dirs = []
        for name in sorted(dirs):
            p = base_path / name
            if name.casefold() in EXCLUDED_PARTS:
                continue
            if _is_link_like(p):
                raise ValueError("workspace_link_or_junction_rejected")
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in sorted(files):
            path = base_path / name
            if not _allowed_file(path, root):
                continue
            if _is_link_like(path) or not path.is_file() or not _within(root, path):
                raise ValueError("workspace_file_boundary_rejected")
            size = path.stat().st_size
            if size > MAX_SINGLE_FILE_BYTES:
                raise ValueError("workspace_single_file_budget_exceeded")
            total += size
            if len(rows) >= MAX_FILES or total > max_total_bytes:
                raise ValueError("workspace_copy_budget_exceeded")
            rel = path.relative_to(root).as_posix()
            content_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append({
                "relative_path": rel,
                "relative_path_digest": hashlib.sha256(rel.encode()).hexdigest(),
                "content_digest": content_digest,
                "size_bytes": size,
            })
    rows.sort(key=lambda x: x["relative_path"].casefold())
    return rows, total


def _manifest(rows: list[Mapping[str, Any]]) -> str:
    return digest([{k: row.get(k) for k in ("relative_path_digest", "content_digest", "size_bytes")} for row in rows])


def _copy_inventory(source: Path, destination: Path, rows: list[Mapping[str, Any]]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=str(destination.parent)))
    try:
        for row in rows:
            rel = PurePosixPath(str(row["relative_path"]))
            src = source.joinpath(*rel.parts)
            dst = staging.joinpath(*rel.parts)
            if _is_link_like(src) or not src.is_file() or hashlib.sha256(src.read_bytes()).hexdigest() != row["content_digest"]:
                raise ValueError("source_snapshot_changed_during_copy")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            if hashlib.sha256(dst.read_bytes()).hexdigest() != row["content_digest"]:
                raise ValueError("candidate_copy_digest_mismatch")
        if destination.exists():
            raise ValueError("candidate_workspace_collision")
        os.replace(staging, destination)
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)


def _git_run(git: str, source: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [git, "-C", str(source), *args], cwd=str(source), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=GIT_TIMEOUT_SECONDS,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"},
    )


def _git_inventory(source: Path, git: str, max_total_bytes: int) -> tuple[list[dict[str, Any]], int]:
    result = _git_run(git, source, ["ls-files", "-z"])
    if result.returncode:
        raise RuntimeError("git_tracked_inventory_failed")
    rows: list[dict[str, Any]] = []
    total = 0
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        rel_text = raw.decode("utf-8", errors="strict").replace("\\", "/")
        pure = PurePosixPath(rel_text)
        if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
            raise RuntimeError("git_tracked_path_rejected")
        path = source.joinpath(*pure.parts)
        if not _allowed_file(path, source):
            continue
        if _is_link_like(path) or not path.is_file() or not _within(source, path):
            raise RuntimeError("git_tracked_boundary_rejected")
        size = path.stat().st_size
        if size > MAX_SINGLE_FILE_BYTES:
            raise RuntimeError("workspace_single_file_budget_exceeded")
        total += size
        if len(rows) >= MAX_FILES or total > max_total_bytes:
            raise RuntimeError("workspace_copy_budget_exceeded")
        rows.append({"relative_path": pure.as_posix(), "relative_path_digest": hashlib.sha256(pure.as_posix().encode()).hexdigest(), "content_digest": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": size})
    rows.sort(key=lambda x: x["relative_path"].casefold())
    return rows, total


def _validate_active_grant(grant: Mapping[str, Any], source_workspace_digest: str, *, command: bool, now_unix: int | None) -> tuple[bool, str]:
    if str(grant.get("workspace_digest") or "") != str(source_workspace_digest or ""):
        return False, "standing_grant_workspace_mismatch"
    if not standing_session_allows(grant, "file_write", now_unix=now_unix):
        return False, "active_file_write_grant_required"
    if command:
        if not standing_session_allows(grant, "command", now_unix=now_unix):
            return False, "active_command_grant_required"
        classes = set((grant.get("profile_snapshot") or {}).get("command_classes") or [])
        if not ({"git", "git_worktree"} & classes):
            return False, "git_worktree_command_class_required"
    return True, ""


def _validate_preconditions(record_id: str, expected_tool: str, runtime_root=None) -> tuple[bool, dict[str, Any]]:
    row = load_tool_preconditions(str(record_id or ""), runtime_root=runtime_root, include_private=True)
    ok = bool(row and row.get("preconditions_satisfied") is True and row.get("tool_code") == expected_tool and row.get("tool_invoked") is False)
    return ok, row


def plan_workspace_isolation(*, source_workspace_digest: str, mode: str = "filesystem_copy", retention_rule: str = "retain_for_review", active_grant: Mapping[str, Any] | None = None, now_unix: int | None = None) -> dict[str, Any]:
    mode = str(mode or "")
    retention = str(retention_rule or "")
    valid_mode = mode in ISOLATION_MODES
    valid_retention = retention in RETENTION_RULES
    command = mode in {"git_worktree", "git_branch_worktree"}
    grant_ok, reason = _validate_active_grant(active_grant or {}, source_workspace_digest, command=command, now_unix=now_unix) if active_grant else (False, "active_standing_grant_not_supplied")
    return {
        "ok": valid_mode and valid_retention,
        "status": "workspace_isolation_plan_ready" if valid_mode and valid_retention else "workspace_isolation_plan_blocked",
        "contract_version": CONTRACT_VERSION,
        "mode": mode,
        "retention_rule": retention,
        "source_workspace_digest": str(source_workspace_digest or ""),
        "active_grant_currently_satisfies_operation": grant_ok,
        "grant_block_reason": "" if grant_ok else reason,
        "requires_sealed_tool_preconditions": True,
        "required_tool_code": "git" if command else "file_patch",
        "workspace_created": False,
        "action_executed": False,
        "repository_metadata_modified": False,
        "ordinary_chat_mutation_allowed": False,
        **WORKSPACE_DENIED_AUTHORITY,
    }


def create_disposable_workspace(
    *,
    source_root: str | Path,
    source_workspace_digest: str,
    active_grant: Mapping[str, Any],
    precondition_record_id: str,
    mode: str = "filesystem_copy",
    retention_rule: str = "retain_for_review",
    runtime_root=None,
    now_unix: int | None = None,
    git_executable: str | None = None,
) -> dict[str, Any]:
    mode = str(mode or "")
    retention = str(retention_rule or "")
    if mode not in ISOLATION_MODES or retention not in RETENTION_RULES:
        return {"ok": False, "status": "workspace_isolation_contract_invalid", **WORKSPACE_DENIED_AUTHORITY}
    command = mode in {"git_worktree", "git_branch_worktree"}
    grant_ok, reason = _validate_active_grant(active_grant, source_workspace_digest, command=command, now_unix=now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, **WORKSPACE_DENIED_AUTHORITY}
    expected_tool = "git" if command else "file_patch"
    pre_ok, pre = _validate_preconditions(precondition_record_id, expected_tool, runtime_root)
    if not pre_ok:
        return {"ok": False, "status": "sealed_satisfied_tool_preconditions_required", **WORKSPACE_DENIED_AUTHORITY}
    try:
        source = _resolve_source(source_root)
        _safe_runtime_boundary(source, runtime_root)
        max_disk_mb = int(((active_grant.get("profile_snapshot") or {}).get("limits") or {}).get("max_disk_mb") or 512)
        max_total = min(DEFAULT_MAX_TOTAL_BYTES, max(1, max_disk_mb) * 1024 * 1024)
        git = git_executable or shutil.which("git") if command else None
        if command and not git:
            raise RuntimeError("git_unavailable")
        before_rows, before_total = _git_inventory(source, str(git), max_total) if command else _inventory(source, max_total)
    except (OSError, RuntimeError, ValueError, UnicodeError) as exc:
        return {"ok": False, "status": str(exc), **WORKSPACE_DENIED_AUTHORITY}
    before_manifest = _manifest(before_rows)
    identity = {
        "contract": CONTRACT_VERSION,
        "source_workspace_digest": source_workspace_digest,
        "source_manifest_digest": before_manifest,
        "grant_digest": active_grant.get("grant_digest"),
        "precondition_record_id": precondition_record_id,
        "mode": mode,
        "retention": retention,
    }
    workspace_id = "iso_" + digest(identity)[:24]
    record_path = _record_path(workspace_id, runtime_root)
    existing = _read_json(record_path)
    if existing:
        supplied = existing.get("record_digest")
        if supplied == digest({k: v for k, v in existing.items() if k != "record_digest"}):
            return {**public_workspace_isolation(existing), "operation_status": "restored"}
        return {"ok": False, "status": "workspace_isolation_record_invalid", **WORKSPACE_DENIED_AUTHORITY}
    holder = _private_workspace_root(workspace_id, runtime_root)
    candidate = holder / "candidate"
    runtime_data = holder / "runtime_data"
    if holder.exists():
        return {"ok": False, "status": "workspace_isolation_collision", **WORKSPACE_DENIED_AUTHORITY}
    holder.mkdir(parents=True, exist_ok=False)
    repository_metadata_modified = False
    branch_name = ""
    base_commit = ""
    try:
        if mode == "filesystem_copy":
            _copy_inventory(source, candidate, before_rows)
        else:
            assert git
            top = _git_run(str(git), source, ["rev-parse", "--show-toplevel"])
            head = _git_run(str(git), source, ["rev-parse", "HEAD"])
            if top.returncode or head.returncode:
                raise RuntimeError("git_repository_required")
            base_commit = head.stdout.decode(errors="replace").strip()
            repository_metadata_modified = True
            if mode == "git_branch_worktree":
                branch_name = f"eidolon-candidate-{workspace_id[4:16]}"
                result = _git_run(str(git), source, ["worktree", "add", "-b", branch_name, str(candidate), base_commit])
            else:
                result = _git_run(str(git), source, ["worktree", "add", "--detach", str(candidate), base_commit])
            if result.returncode:
                raise RuntimeError("git_worktree_creation_failed")
        runtime_data.mkdir(parents=True, exist_ok=False)
        candidate_rows, candidate_total = _git_inventory(candidate, str(git), max_total) if command else _inventory(candidate, max_total)
        if _manifest(candidate_rows) != before_manifest:
            raise RuntimeError("candidate_manifest_mismatch")
        after_rows, _ = _git_inventory(source, str(git), max_total) if command else _inventory(source, max_total)
        if _manifest(after_rows) != before_manifest:
            raise RuntimeError("source_content_changed_during_isolation")
        record = {
            "contract_version": CONTRACT_VERSION,
            "workspace_id": workspace_id,
            "mode": mode,
            "retention_rule": retention,
            "source_workspace_digest": source_workspace_digest,
            "source_manifest_digest": before_manifest,
            "source_private_path": str(source),
            "candidate_private_path": str(candidate),
            "runtime_data_private_path": str(runtime_data),
            "grant_digest": active_grant.get("grant_digest"),
            "precondition_record_id": precondition_record_id,
            "precondition_digest": pre.get("record_digest"),
            "file_count": len(candidate_rows),
            "total_bytes": candidate_total,
            "candidate_manifest_digest": _manifest(candidate_rows),
            "base_commit_digest": hashlib.sha256(base_commit.encode()).hexdigest() if base_commit else "",
            "branch_name": branch_name,
            "repository_metadata_modified": repository_metadata_modified,
            "source_content_modified": False,
            "runtime_data_root_created": True,
            "cleanup_supported": True,
            "workspace_disposable": True,
            "workspace_created": True,
            "cleaned": False,
            "standing_grant_validated": True,
            "workspace_isolation_operation_authorized": True,
            "tool_invoked": command,
            "action_executed": True,
            "content_free_public_projection": True,
            **WORKSPACE_DENIED_AUTHORITY,
        }
        record["record_digest"] = digest(record)
        _atomic_json(record_path, record)
        return {**public_workspace_isolation(record), "operation_status": "created"}
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        # Best-effort rollback only of the just-created owned holder/worktree.
        if repository_metadata_modified:
            git = git_executable or shutil.which("git")
            if git:
                try:
                    _git_run(git, source, ["worktree", "remove", "--force", str(candidate)])
                    if branch_name:
                        _git_run(git, source, ["branch", "-D", branch_name])
                except Exception:
                    pass
        shutil.rmtree(holder, ignore_errors=True)
        return {"ok": False, "status": str(exc), "workspace_created": False, "rollback_attempted": True, **WORKSPACE_DENIED_AUTHORITY}


def _workspace_changed(record: Mapping[str, Any], max_total: int) -> bool:
    candidate = Path(str(record.get("candidate_private_path") or ""))
    try:
        rows, _ = _inventory(candidate, max_total)
        return _manifest(rows) != record.get("candidate_manifest_digest")
    except (OSError, ValueError):
        return True


def cleanup_disposable_workspace(
    workspace_id: str,
    *,
    active_grant: Mapping[str, Any],
    discard_owned_changes: bool = False,
    runtime_root=None,
    now_unix: int | None = None,
    git_executable: str | None = None,
) -> dict[str, Any]:
    record = _read_json(_record_path(workspace_id, runtime_root))
    if not record or record.get("record_digest") != digest({k: v for k, v in record.items() if k != "record_digest"}):
        return {"ok": False, "status": "workspace_isolation_record_missing_or_invalid", **WORKSPACE_DENIED_AUTHORITY}
    if record.get("cleaned"):
        return {**public_workspace_isolation(record), "operation_status": "already_cleaned"}
    command = record.get("mode") in {"git_worktree", "git_branch_worktree"}
    grant_ok, reason = _validate_active_grant(active_grant, str(record.get("source_workspace_digest") or ""), command=command, now_unix=now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, **WORKSPACE_DENIED_AUTHORITY}
    max_disk_mb = int(((active_grant.get("profile_snapshot") or {}).get("limits") or {}).get("max_disk_mb") or 512)
    max_total = min(DEFAULT_MAX_TOTAL_BYTES, max(1, max_disk_mb) * 1024 * 1024)
    changed = _workspace_changed(record, max_total)
    if changed and record.get("retention_rule") == "retain_for_review" and not discard_owned_changes:
        return {"ok": False, "status": "workspace_has_unreviewed_changes", "owned_changes_detected": True, **WORKSPACE_DENIED_AUTHORITY}
    source = Path(str(record.get("source_private_path") or ""))
    candidate = Path(str(record.get("candidate_private_path") or ""))
    holder = _private_workspace_root(workspace_id, runtime_root)
    try:
        if command:
            git = git_executable or shutil.which("git")
            if not git:
                return {"ok": False, "status": "git_unavailable_for_cleanup", **WORKSPACE_DENIED_AUTHORITY}
            result = _git_run(git, source, ["worktree", "remove", "--force", str(candidate)])
            if result.returncode:
                return {"ok": False, "status": "git_worktree_cleanup_failed", **WORKSPACE_DENIED_AUTHORITY}
            branch = str(record.get("branch_name") or "")
            if branch:
                if not re.fullmatch(r"eidolon-candidate-[a-f0-9]{12}", branch):
                    return {"ok": False, "status": "owned_branch_name_invalid", **WORKSPACE_DENIED_AUTHORITY}
                result = _git_run(git, source, ["branch", "-D", branch])
                if result.returncode:
                    return {"ok": False, "status": "owned_branch_cleanup_failed", **WORKSPACE_DENIED_AUTHORITY}
        shutil.rmtree(holder, ignore_errors=False)
    except OSError:
        return {"ok": False, "status": "workspace_cleanup_failed", **WORKSPACE_DENIED_AUTHORITY}
    record.update({
        "status": "workspace_isolation_cleaned",
        "candidate_private_path": "",
        "runtime_data_private_path": "",
        "workspace_created": False,
        "cleaned": True,
        "owned_changes_discarded": bool(changed and discard_owned_changes),
        "action_executed": True,
    })
    record["record_digest"] = digest({k: v for k, v in record.items() if k != "record_digest"})
    _atomic_json(_record_path(workspace_id, runtime_root), record)
    return {**public_workspace_isolation(record), "operation_status": "cleaned"}


def public_workspace_isolation(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("workspace_created") or record.get("cleaned")),
        "status": record.get("status") or ("workspace_isolation_ready" if record.get("workspace_created") else "workspace_isolation_cleaned"),
        "contract_version": CONTRACT_VERSION,
        "workspace_id": record.get("workspace_id"),
        "mode": record.get("mode"),
        "retention_rule": record.get("retention_rule"),
        "source_workspace_digest": record.get("source_workspace_digest"),
        "source_manifest_digest": record.get("source_manifest_digest"),
        "candidate_manifest_digest": record.get("candidate_manifest_digest"),
        "file_count": int(record.get("file_count") or 0),
        "total_bytes": int(record.get("total_bytes") or 0),
        "repository_metadata_modified": bool(record.get("repository_metadata_modified")),
        "source_content_modified": False,
        "runtime_data_root_created": bool(record.get("runtime_data_root_created")),
        "workspace_disposable": True,
        "workspace_created": bool(record.get("workspace_created")),
        "cleaned": bool(record.get("cleaned")),
        "standing_grant_validated": bool(record.get("standing_grant_validated")),
        "workspace_isolation_operation_authorized": bool(record.get("workspace_isolation_operation_authorized")),
        "private_paths_exposed": False,
        "raw_file_content_exposed": False,
        "action_executed": bool(record.get("action_executed")),
        **WORKSPACE_DENIED_AUTHORITY,
    }


def inspect_workspace_isolation(workspace_id: str, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_record_path(workspace_id, runtime_root))
    if not record or record.get("record_digest") != digest({k: v for k, v in record.items() if k != "record_digest"}):
        return {"ok": False, "status": "workspace_isolation_record_missing_or_invalid", **WORKSPACE_DENIED_AUTHORITY}
    return public_workspace_isolation(record)


def process_workspace_isolation_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show workspace isolation", "inspect workspace isolation", "show candidate workspace"}:
        return {"active": False}
    state = project_state or {}
    workspace_id = str(state.get("workspace_isolation_id") or "")
    if workspace_id:
        return {"active": True, **inspect_workspace_isolation(workspace_id, runtime_root=runtime_root)}
    return {"active": True, **plan_workspace_isolation(
        source_workspace_digest=str(state.get("workspace_digest") or ""),
        mode=str(state.get("workspace_isolation_mode") or "filesystem_copy"),
        retention_rule=str(state.get("workspace_retention_rule") or "retain_for_review"),
        active_grant=state.get("standing_session_grant"),
        now_unix=state.get("now_unix"),
    )}


__all__ = [
    "CONTRACT_VERSION", "ISOLATION_MODES", "RETENTION_RULES", "WORKSPACE_DENIED_AUTHORITY",
    "plan_workspace_isolation", "create_disposable_workspace", "cleanup_disposable_workspace",
    "public_workspace_isolation", "inspect_workspace_isolation", "process_workspace_isolation_control",
]
