from __future__ import annotations
"""v1334 structured candidate-workspace file operations.

All writes are constrained to an existing v1333 disposable candidate workspace,
require a matching active v1302 standing grant and a sealed satisfied v1332 tool
precondition, and use optimistic content digests. Operation evidence is content-
minimized; raw file text is returned only to the immediate internal caller when
explicitly requested and is never persisted in the operation record.
"""
import codecs
import hashlib
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from standing_session_grants import standing_session_allows
from tool_preconditions import load_tool_preconditions
from workspace_isolation import _is_link_like, _record_path as _isolation_record_path, _within

CONTRACT_VERSION = "v1334.8"
OPERATION_KINDS = ("read", "patch", "move", "generated_update")
MAX_READ_BYTES = 8 * 1024 * 1024
MAX_PATCHES = 64
FILE_OPERATION_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "tool_execution_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "release_authorized": False,
}


def _ops_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase4_file_operations"


def _operation_path(operation_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"fop_[a-f0-9]{24}", str(operation_id or "")):
        raise ValueError("invalid_file_operation_id")
    return _ops_root(runtime_root) / "records" / f"{operation_id}.json"


def _load_workspace(workspace_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_isolation_record_path(workspace_id, runtime_root))
    if not row or row.get("record_digest") != digest({k: v for k, v in row.items() if k != "record_digest"}):
        return {}
    if row.get("cleaned") or not row.get("workspace_created"):
        return {}
    root = Path(str(row.get("candidate_private_path") or ""))
    if not root.is_dir() or _is_link_like(root):
        return {}
    return row


def _safe_relative(raw: str) -> PurePosixPath:
    text = str(raw or "").strip().replace("\\", "/")
    if not text or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        raise ValueError("unsafe_relative_path")
    pure = PurePosixPath(text)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("unsafe_relative_path")
    # Runtime/private roots are never valid targets inside a source-only candidate.
    if any(part.casefold() in {".git", "data", "runtime", "private", "secrets", "credentials", "tokens", "node_modules", ".venv", "venv", "__pycache__"} for part in pure.parts):
        raise ValueError("protected_candidate_path")
    return pure


def _candidate_path(workspace: Mapping[str, Any], relative_path: str, *, allow_missing: bool = False) -> tuple[Path, PurePosixPath]:
    root = Path(str(workspace.get("candidate_private_path") or "")).resolve(strict=True)
    pure = _safe_relative(relative_path)
    path = root.joinpath(*pure.parts)
    # Reject any existing link/reparse component before resolving the leaf.
    current = root
    for part in pure.parts:
        current = current / part
        if current.exists() and _is_link_like(current):
            raise ValueError("candidate_link_or_junction_rejected")
    resolved = path.resolve(strict=not allow_missing)
    if not _within(root, resolved):
        raise ValueError("candidate_path_escape_rejected")
    return path, pure


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decode(data: bytes) -> tuple[str, str, bytes]:
    if data.startswith(codecs.BOM_UTF8):
        return data[len(codecs.BOM_UTF8):].decode("utf-8"), "utf8_bom", codecs.BOM_UTF8
    if data.startswith(codecs.BOM_UTF16_LE):
        return data[len(codecs.BOM_UTF16_LE):].decode("utf-16-le"), "utf16_le_bom", codecs.BOM_UTF16_LE
    if data.startswith(codecs.BOM_UTF16_BE):
        return data[len(codecs.BOM_UTF16_BE):].decode("utf-16-be"), "utf16_be_bom", codecs.BOM_UTF16_BE
    try:
        return data.decode("utf-8"), "utf8", b""
    except UnicodeDecodeError as exc:
        raise ValueError("unsupported_or_binary_encoding") from exc


def _encode(text: str, encoding_code: str, bom: bytes) -> bytes:
    if encoding_code in {"utf8", "utf8_bom"}:
        body = text.encode("utf-8")
    elif encoding_code == "utf16_le_bom":
        body = text.encode("utf-16-le")
    elif encoding_code == "utf16_be_bom":
        body = text.encode("utf-16-be")
    else:
        raise ValueError("unsupported_encoding_code")
    return bom + body


def _newline_code(text: str) -> tuple[str, str]:
    crlf = text.count("\r\n")
    without_crlf = text.replace("\r\n", "")
    lf = without_crlf.count("\n")
    cr = without_crlf.count("\r")
    kinds = sum(bool(x) for x in (crlf, lf, cr))
    if kinds > 1:
        return "mixed", "\n"
    if crlf:
        return "crlf", "\r\n"
    if cr:
        return "cr", "\r"
    return "lf", "\n"


def _normalize_inserted_newlines(text: str, newline: str) -> str:
    return str(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)


def _validate_grant(workspace: Mapping[str, Any], grant: Mapping[str, Any], action_class: str, now_unix: int | None) -> tuple[bool, str]:
    if str(grant.get("workspace_digest") or "") != str(workspace.get("source_workspace_digest") or ""):
        return False, "standing_grant_workspace_mismatch"
    if not standing_session_allows(grant, action_class, now_unix=now_unix):
        return False, f"active_{action_class}_grant_required"
    return True, ""


def _validate_preconditions(record_id: str, tool_code: str, runtime_root=None) -> tuple[bool, dict[str, Any]]:
    row = load_tool_preconditions(str(record_id or ""), runtime_root=runtime_root, include_private=True)
    return bool(row and row.get("preconditions_satisfied") is True and row.get("tool_code") == tool_code and row.get("tool_invoked") is False), row


def _base_operation(kind: str, workspace: Mapping[str, Any], pure: PurePosixPath, pre: Mapping[str, Any], grant: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "operation_kind": kind,
        "workspace_id": workspace.get("workspace_id"),
        "source_workspace_digest": workspace.get("source_workspace_digest"),
        "relative_path_digest": hashlib.sha256(pure.as_posix().encode()).hexdigest(),
        "grant_digest": grant.get("grant_digest"),
        "precondition_record_id": pre.get("precondition_record_id"),
        "precondition_digest": pre.get("record_digest"),
        "selected_source_modified": False,
        "candidate_workspace_only": True,
        "command_executed": False,
        "provider_contacted": False,
        "raw_content_persisted": False,
        "workspace_operation_authorized": True,
        **FILE_OPERATION_DENIED_AUTHORITY,
    }


def _save_operation(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row["record_digest"] = digest(row)
    _atomic_json(_operation_path(str(row["operation_id"]), runtime_root), row)
    return row


def _existing(operation_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_operation_path(operation_id, runtime_root))
    if not row or row.get("record_digest") != digest({k: v for k, v in row.items() if k != "record_digest"}):
        return {}
    return row


def read_candidate_file(
    workspace_id: str,
    relative_path: str,
    *,
    active_grant: Mapping[str, Any],
    precondition_record_id: str,
    runtime_root=None,
    now_unix: int | None = None,
    include_content: bool = False,
) -> dict[str, Any]:
    workspace = _load_workspace(workspace_id, runtime_root)
    if not workspace:
        return {"ok": False, "status": "candidate_workspace_missing_or_invalid", **FILE_OPERATION_DENIED_AUTHORITY}
    grant_ok, reason = _validate_grant(workspace, active_grant, "read", now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, **FILE_OPERATION_DENIED_AUTHORITY}
    pre_ok, pre = _validate_preconditions(precondition_record_id, "file_read", runtime_root)
    if not pre_ok:
        return {"ok": False, "status": "sealed_satisfied_file_read_preconditions_required", **FILE_OPERATION_DENIED_AUTHORITY}
    try:
        path, pure = _candidate_path(workspace, relative_path)
        if not path.is_file() or path.stat().st_size > MAX_READ_BYTES:
            raise ValueError("candidate_file_missing_or_read_budget_exceeded")
        data = path.read_bytes()
        text, encoding_code, _ = _decode(data)
        newline_code, _ = _newline_code(text)
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": str(exc), **FILE_OPERATION_DENIED_AUTHORITY}
    before = hashlib.sha256(data).hexdigest()
    operation_id = "fop_" + digest({"kind": "read", "workspace": workspace_id, "path": pure.as_posix(), "content": before})[:24]
    row = _existing(operation_id, runtime_root)
    if not row:
        row = _base_operation("read", workspace, pure, pre, active_grant)
        row.update({"operation_id": operation_id, "status": "candidate_file_read", "before_digest": before, "after_digest": before, "size_bytes": len(data), "encoding_code": encoding_code, "newline_code": newline_code, "action_executed": True})
        _save_operation(row, runtime_root)
    result = {"ok": True, "status": "candidate_file_read", "file_operation": public_file_operation(row), "operation_executed_this_request": True, **FILE_OPERATION_DENIED_AUTHORITY}
    if include_content:
        result["content"] = text
        result["content_exposed_to_internal_caller"] = True
    else:
        result["content_exposed_to_internal_caller"] = False
    return result


def _apply_patches(text: str, patches: Sequence[Mapping[str, Any]], newline: str) -> str:
    value = text
    if not patches or len(patches) > MAX_PATCHES:
        raise ValueError("patch_count_invalid")
    for item in patches:
        kind = str(item.get("type") or "")
        if kind == "replace_text":
            old = _normalize_inserted_newlines(str(item.get("old") or ""), newline)
            new = _normalize_inserted_newlines(str(item.get("new") or ""), newline)
            expected = int(item.get("expected_occurrences") or 1)
            if not old or expected < 1 or value.count(old) != expected:
                raise ValueError("replace_text_precondition_failed")
            value = value.replace(old, new)
        elif kind == "replace_line_range":
            start = int(item.get("start_line") or 0)
            end = int(item.get("end_line") or 0)
            if start < 1 or end < start:
                raise ValueError("line_range_invalid")
            # splitlines(True) preserves the original line terminators outside the replacement.
            lines = value.splitlines(True)
            if end > len(lines):
                raise ValueError("line_range_out_of_bounds")
            replacement = _normalize_inserted_newlines(str(item.get("replacement") or ""), newline)
            if replacement and not replacement.endswith(("\n", "\r")) and end < len(lines):
                replacement += newline
            lines[start - 1:end] = [replacement]
            value = "".join(lines)
        else:
            raise ValueError("patch_type_unsupported")
    return value


def patch_candidate_file(
    workspace_id: str,
    relative_path: str,
    *,
    expected_content_digest: str,
    patches: Sequence[Mapping[str, Any]],
    active_grant: Mapping[str, Any],
    precondition_record_id: str,
    runtime_root=None,
    now_unix: int | None = None,
) -> dict[str, Any]:
    workspace = _load_workspace(workspace_id, runtime_root)
    if not workspace:
        return {"ok": False, "status": "candidate_workspace_missing_or_invalid", **FILE_OPERATION_DENIED_AUTHORITY}
    grant_ok, reason = _validate_grant(workspace, active_grant, "file_write", now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, **FILE_OPERATION_DENIED_AUTHORITY}
    pre_ok, pre = _validate_preconditions(precondition_record_id, "file_patch", runtime_root)
    if not pre_ok:
        return {"ok": False, "status": "sealed_satisfied_file_patch_preconditions_required", **FILE_OPERATION_DENIED_AUTHORITY}
    try:
        path, pure = _candidate_path(workspace, relative_path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": str(exc), **FILE_OPERATION_DENIED_AUTHORITY}
    patch_contract = [{"type": str(x.get("type") or ""), "digest": digest(x)} for x in patches]
    operation_id = "fop_" + digest({"kind": "patch", "workspace": workspace_id, "path": pure.as_posix(), "expected": expected_content_digest, "patches": patch_contract})[:24]
    existing = _existing(operation_id, runtime_root)
    if existing:
        try:
            if path.is_file() and _file_digest(path) == existing.get("after_digest"):
                return {"ok": True, "status": "candidate_file_patch_restored", "file_operation": public_file_operation(existing), "operation_executed_this_request": False, **FILE_OPERATION_DENIED_AUTHORITY}
        except OSError:
            pass
        return {"ok": False, "status": "prior_file_operation_conflicts_with_candidate", **FILE_OPERATION_DENIED_AUTHORITY}
    try:
        data = path.read_bytes()
        before = hashlib.sha256(data).hexdigest()
        if before != str(expected_content_digest or ""):
            raise ValueError("stale_candidate_content_digest")
        text, encoding_code, bom = _decode(data)
        newline_code, newline = _newline_code(text)
        mode = stat.S_IMODE(path.stat().st_mode)
        updated = _apply_patches(text, patches, newline)
        encoded = _encode(updated, encoding_code, bom)
        tmp = path.with_name(path.name + ".eidolon-tmp")
        if tmp.exists():
            raise ValueError("candidate_temp_collision")
        try:
            tmp.write_bytes(encoded)
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()
        after = _file_digest(path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": str(exc), **FILE_OPERATION_DENIED_AUTHORITY}
    row = _base_operation("patch", workspace, pure, pre, active_grant)
    row.update({"operation_id": operation_id, "status": "candidate_file_patched", "before_digest": before, "after_digest": after, "patch_contract_digests": [x["digest"] for x in patch_contract], "patch_count": len(patch_contract), "encoding_code": encoding_code, "newline_code": newline_code, "size_bytes": len(encoded), "action_executed": True})
    _save_operation(row, runtime_root)
    return {"ok": True, "status": "candidate_file_patched", "file_operation": public_file_operation(row), "operation_executed_this_request": True, **FILE_OPERATION_DENIED_AUTHORITY}


def move_candidate_file(
    workspace_id: str,
    source_relative_path: str,
    destination_relative_path: str,
    *,
    expected_source_digest: str,
    active_grant: Mapping[str, Any],
    precondition_record_id: str,
    runtime_root=None,
    now_unix: int | None = None,
) -> dict[str, Any]:
    workspace = _load_workspace(workspace_id, runtime_root)
    if not workspace:
        return {"ok": False, "status": "candidate_workspace_missing_or_invalid", **FILE_OPERATION_DENIED_AUTHORITY}
    grant_ok, reason = _validate_grant(workspace, active_grant, "file_write", now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, **FILE_OPERATION_DENIED_AUTHORITY}
    pre_ok, pre = _validate_preconditions(precondition_record_id, "file_patch", runtime_root)
    if not pre_ok:
        return {"ok": False, "status": "sealed_satisfied_file_patch_preconditions_required", **FILE_OPERATION_DENIED_AUTHORITY}
    try:
        src, src_pure = _candidate_path(workspace, source_relative_path, allow_missing=True)
        dst, dst_pure = _candidate_path(workspace, destination_relative_path, allow_missing=True)
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": str(exc), **FILE_OPERATION_DENIED_AUTHORITY}
    if src_pure == dst_pure:
        return {"ok": False, "status": "move_source_equals_destination", **FILE_OPERATION_DENIED_AUTHORITY}
    operation_id = "fop_" + digest({"kind": "move", "workspace": workspace_id, "source": src_pure.as_posix(), "destination": dst_pure.as_posix(), "expected": expected_source_digest})[:24]
    existing = _existing(operation_id, runtime_root)
    if existing:
        if dst.is_file() and _file_digest(dst) == existing.get("after_digest") and not src.exists():
            return {"ok": True, "status": "candidate_file_move_restored", "file_operation": public_file_operation(existing), "operation_executed_this_request": False, **FILE_OPERATION_DENIED_AUTHORITY}
        return {"ok": False, "status": "prior_file_operation_conflicts_with_candidate", **FILE_OPERATION_DENIED_AUTHORITY}
    try:
        if not src.is_file() or _is_link_like(src):
            raise ValueError("move_source_missing_or_rejected")
        before = _file_digest(src)
        if before != str(expected_source_digest or ""):
            raise ValueError("stale_candidate_content_digest")
        if dst.exists():
            raise ValueError("move_destination_exists")
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Re-check newly traversed parent chain after mkdir.
        _candidate_path(workspace, destination_relative_path, allow_missing=True)
        os.replace(src, dst)
        after = _file_digest(dst)
        if after != before:
            raise ValueError("move_digest_mismatch")
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": str(exc), **FILE_OPERATION_DENIED_AUTHORITY}
    row = _base_operation("move", workspace, src_pure, pre, active_grant)
    row.update({"operation_id": operation_id, "status": "candidate_file_moved", "destination_path_digest": hashlib.sha256(dst_pure.as_posix().encode()).hexdigest(), "before_digest": before, "after_digest": after, "action_executed": True})
    _save_operation(row, runtime_root)
    return {"ok": True, "status": "candidate_file_moved", "file_operation": public_file_operation(row), "operation_executed_this_request": True, **FILE_OPERATION_DENIED_AUTHORITY}


def update_generated_file(
    workspace_id: str,
    relative_path: str,
    content: str,
    *,
    expected_content_digest: str = "",
    expected_absent: bool = False,
    active_grant: Mapping[str, Any],
    precondition_record_id: str,
    runtime_root=None,
    now_unix: int | None = None,
) -> dict[str, Any]:
    workspace = _load_workspace(workspace_id, runtime_root)
    if not workspace:
        return {"ok": False, "status": "candidate_workspace_missing_or_invalid", **FILE_OPERATION_DENIED_AUTHORITY}
    grant_ok, reason = _validate_grant(workspace, active_grant, "file_write", now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, **FILE_OPERATION_DENIED_AUTHORITY}
    pre_ok, pre = _validate_preconditions(precondition_record_id, "file_patch", runtime_root)
    if not pre_ok:
        return {"ok": False, "status": "sealed_satisfied_file_patch_preconditions_required", **FILE_OPERATION_DENIED_AUTHORITY}
    try:
        path, pure = _candidate_path(workspace, relative_path, allow_missing=True)
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": str(exc), **FILE_OPERATION_DENIED_AUTHORITY}
    content_digest = hashlib.sha256(str(content).encode("utf-8")).hexdigest()
    operation_id = "fop_" + digest({"kind": "generated_update", "workspace": workspace_id, "path": pure.as_posix(), "expected": expected_content_digest, "expected_absent": expected_absent, "content": content_digest})[:24]
    existing = _existing(operation_id, runtime_root)
    if existing:
        if path.is_file() and _file_digest(path) == existing.get("after_digest"):
            return {"ok": True, "status": "generated_file_update_restored", "file_operation": public_file_operation(existing), "operation_executed_this_request": False, **FILE_OPERATION_DENIED_AUTHORITY}
        return {"ok": False, "status": "prior_file_operation_conflicts_with_candidate", **FILE_OPERATION_DENIED_AUTHORITY}
    try:
        exists = path.exists()
        if expected_absent and exists:
            raise ValueError("generated_destination_expected_absent")
        if not expected_absent:
            if not path.is_file() or _file_digest(path) != str(expected_content_digest or ""):
                raise ValueError("generated_file_precondition_failed")
        before = _file_digest(path) if exists and path.is_file() else ""
        if exists:
            data = path.read_bytes(); text, encoding_code, bom = _decode(data); newline_code, newline = _newline_code(text); mode = stat.S_IMODE(path.stat().st_mode)
            updated_text = _normalize_inserted_newlines(str(content), newline); encoded = _encode(updated_text, encoding_code, bom)
        else:
            encoding_code="utf8";newline_code="lf";mode=0o644;encoded=str(content).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        _candidate_path(workspace, relative_path, allow_missing=True)
        tmp = path.with_name(path.name + ".eidolon-tmp")
        if tmp.exists():
            raise ValueError("candidate_temp_collision")
        try:
            tmp.write_bytes(encoded);os.chmod(tmp,mode);os.replace(tmp,path)
        finally:
            if tmp.exists():tmp.unlink()
        after = _file_digest(path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": str(exc), **FILE_OPERATION_DENIED_AUTHORITY}
    row = _base_operation("generated_update", workspace, pure, pre, active_grant)
    row.update({"operation_id": operation_id, "status": "generated_file_updated", "before_digest": before, "after_digest": after, "generated_file": True, "encoding_code": encoding_code, "newline_code": newline_code, "size_bytes": len(encoded), "action_executed": True})
    _save_operation(row, runtime_root)
    return {"ok": True, "status": "generated_file_updated", "file_operation": public_file_operation(row), "operation_executed_this_request": True, **FILE_OPERATION_DENIED_AUTHORITY}


def public_file_operation(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "operation_id": row.get("operation_id"),
        "operation_kind": row.get("operation_kind"),
        "status": row.get("status"),
        "workspace_id": row.get("workspace_id"),
        "source_workspace_digest": row.get("source_workspace_digest"),
        "relative_path_digest": row.get("relative_path_digest"),
        "destination_path_digest": row.get("destination_path_digest"),
        "before_digest": row.get("before_digest"),
        "after_digest": row.get("after_digest"),
        "patch_count": int(row.get("patch_count") or 0),
        "encoding_code": row.get("encoding_code"),
        "newline_code": row.get("newline_code"),
        "size_bytes": int(row.get("size_bytes") or 0),
        "generated_file": bool(row.get("generated_file")),
        "selected_source_modified": False,
        "candidate_workspace_only": True,
        "raw_content_exposed": False,
        "raw_path_exposed": False,
        "raw_content_persisted": False,
        "workspace_operation_authorized": bool(row.get("workspace_operation_authorized")),
        "action_executed": bool(row.get("action_executed")),
        **FILE_OPERATION_DENIED_AUTHORITY,
    }


def inspect_file_operation(operation_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _existing(operation_id, runtime_root)
    if not row:
        return {"ok": False, "status": "file_operation_missing_or_invalid", **FILE_OPERATION_DENIED_AUTHORITY}
    return {"ok": True, "status": "file_operation_inspected", "file_operation": public_file_operation(row), "operation_executed_this_request": False, **FILE_OPERATION_DENIED_AUTHORITY}


def process_file_operations_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show file operation", "inspect file operation", "show candidate file operation"}:
        return {"active": False}
    operation_id = str((project_state or {}).get("file_operation_id") or "")
    if not operation_id:
        return {"active": True, "ok": False, "status": "file_operation_id_required", "operation_executed_this_request": False, **FILE_OPERATION_DENIED_AUTHORITY}
    return {"active": True, **inspect_file_operation(operation_id, runtime_root=runtime_root)}


__all__ = [
    "CONTRACT_VERSION", "OPERATION_KINDS", "FILE_OPERATION_DENIED_AUTHORITY",
    "read_candidate_file", "patch_candidate_file", "move_candidate_file", "update_generated_file",
    "public_file_operation", "inspect_file_operation", "process_file_operations_control",
]
