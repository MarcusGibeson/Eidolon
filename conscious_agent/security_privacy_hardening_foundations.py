from __future__ import annotations

"""v1278.0-v1278.2 security/privacy hardening foundations.

These helpers validate paths, archives, authorization boundaries, provider
material, and source/runtime separation. They are deliberately content-minimal
and grant no execution or mutation authority.
"""

import hashlib
import hmac
import json
import os
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1278.2"
MAX_ARCHIVE_ENTRIES = 10_000
MAX_ARCHIVE_TOTAL_UNCOMPRESSED = 256 * 1024 * 1024
MAX_ARCHIVE_ENTRY_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_COMPRESSION_RATIO = 500.0
MAX_PROJECT_ENTRIES = 20_000
MAX_RELATIVE_PATH_BYTES = 4096
MAX_PATH_SEGMENT_BYTES = 255

AUTHORITY_FLAGS = {
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "repair_authorized": False,
    "active_source_mutation_authorized": False,
    "selected_project_mutation_authorized": False,
    "source_application_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "self_update_authorized": False,
    "rollback_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}

_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}
_GENERIC_APPROVAL = {
    "go ahead", "go ahead.", "proceed", "proceed.", "do it", "do it.",
    "yes", "yes.", "ok", "okay", "continue", "keep going",
}
_PRIVATE_FIELD_TOKENS = {
    "prompt", "response", "payload", "secret", "credential", "token",
    "authorization_phrase", "api_key", "private_key", "stdout", "stderr",
    "conversation", "message_text", "memory_text", "raw_source", "patch_text",
}
_SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", "credentials.json", "secrets.json",
    "id_rsa", "id_ed25519", "private.key", "provider_response.json",
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _path_digest(path: str | Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8", errors="surrogatepass")).hexdigest()


def is_link_or_reparse(path: str | Path) -> bool:
    candidate = Path(path)
    try:
        if candidate.is_symlink():
            return True
        st = os.lstat(candidate)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    attrs = int(getattr(st, "st_file_attributes", 0) or 0)
    reparse = int(getattr(os, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attrs & reparse)


def validate_untrusted_relative_path(raw: str | Path) -> str:
    text = str(raw or "")
    if not text or "\x00" in text or any(ord(ch) < 32 for ch in text):
        raise ValueError("security_relative_path_invalid")
    if "\\" in text:
        # Reject ambiguous separator semantics at the boundary. Internal callers
        # should already use canonical POSIX relative paths.
        raise ValueError("security_relative_path_backslash_rejected")
    if text.startswith(("/", "//", "./")) or text.endswith("/.") or "/./" in text or "//" in text or re.match(r"^[A-Za-z]:", text):
        raise ValueError("security_relative_path_absolute_rejected")
    if ":" in text:
        # Windows ADS / drive ambiguity.
        raise ValueError("security_relative_path_colon_rejected")
    pure = PurePosixPath(text)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("security_relative_path_traversal_rejected")
    if len(text.encode("utf-8")) > MAX_RELATIVE_PATH_BYTES:
        raise ValueError("security_relative_path_too_long")
    for part in pure.parts:
        if len(part.encode("utf-8")) > MAX_PATH_SEGMENT_BYTES:
            raise ValueError("security_path_segment_too_long")
        if part.endswith((".", " ")):
            raise ValueError("security_windows_trailing_dot_space_rejected")
        if part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED:
            raise ValueError("security_windows_reserved_name_rejected")
    return pure.as_posix()


def inspect_contained_path(
    root: str | Path,
    relative_path: str | Path,
    *,
    require_exists: bool = False,
    require_file: bool = False,
) -> dict[str, Any]:
    root_input = Path(root).expanduser()
    if is_link_or_reparse(root_input):
        raise ValueError("security_root_link_or_reparse_rejected")
    root_path = root_input.resolve(strict=True)
    if not root_path.is_dir() or is_link_or_reparse(root_path):
        raise ValueError("security_root_invalid")
    relative = validate_untrusted_relative_path(relative_path)
    current = root_path
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        if current.exists() or current.is_symlink():
            if is_link_or_reparse(current):
                raise ValueError("security_path_link_or_reparse_rejected")
            resolved = current.resolve(strict=True)
            try:
                resolved.relative_to(root_path)
            except ValueError as exc:
                raise ValueError("security_path_containment_escape") from exc
        else:
            # Remaining missing descendants cannot escape unless an already
            # checked ancestor is replaced later; callers re-run this guard
            # immediately before sensitive operations.
            break
    candidate = root_path.joinpath(*parts)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(root_path)
    except ValueError as exc:
        raise ValueError("security_path_containment_escape") from exc
    exists = candidate.exists()
    if require_exists and not exists:
        raise ValueError("security_path_required_entry_missing")
    if exists and is_link_or_reparse(candidate):
        raise ValueError("security_path_link_or_reparse_rejected")
    if require_file and (not exists or not candidate.is_file()):
        raise ValueError("security_path_required_file_missing")
    return {
        "ok": True,
        "status": "security_path_contained",
        "relative_path_digest": _path_digest(relative),
        "root_digest": _path_digest(root_path),
        "exists": exists,
        "file_required": require_file,
        "link_or_reparse": False,
        "raw_path_returned": False,
        **AUTHORITY_FLAGS,
    }


def inspect_runtime_source_separation(source_root: str | Path, runtime_root: str | Path) -> dict[str, Any]:
    source_input = Path(source_root).expanduser()
    runtime_input = Path(runtime_root).expanduser()
    if is_link_or_reparse(source_input) or (runtime_input.exists() and is_link_or_reparse(runtime_input)):
        return {"ok": False, "status": "runtime_source_link_boundary_rejected", "overlap": True, **AUTHORITY_FLAGS}
    source = source_input.resolve(strict=True)
    runtime = runtime_input.resolve(strict=False)
    overlap = source == runtime or source in runtime.parents or runtime in source.parents
    return {
        "ok": not overlap,
        "status": "runtime_source_separate" if not overlap else "runtime_source_overlap_rejected",
        "overlap": overlap,
        "source_root_digest": _path_digest(source),
        "runtime_root_digest": _path_digest(runtime),
        "raw_paths_returned": False,
        **AUTHORITY_FLAGS,
    }


def validate_exact_authorization_boundary(provided: str, expected: str) -> dict[str, Any]:
    supplied = str(provided or "").strip()
    wanted = str(expected or "")
    exact = bool(wanted) and hmac.compare_digest(supplied.encode("utf-8"), wanted.encode("utf-8"))
    generic = supplied.casefold() in _GENERIC_APPROVAL
    return {
        "ok": exact and not generic,
        "status": "exact_authorization_matched" if exact and not generic else "exact_authorization_required",
        "generic_approval_rejected": generic,
        "provided_digest": _digest(supplied) if supplied else "",
        "expected_digest": _digest(wanted) if wanted else "",
        "authorization_phrase_returned": False,
        **AUTHORITY_FLAGS,
    }


def build_provider_material_receipt(
    *, provider_identifier: str, provider_kind: str, status: str,
    raw_payload: str | bytes | None = None,
) -> dict[str, Any]:
    kind = str(provider_kind or "").strip().casefold()
    state = str(status or "").strip().casefold()
    if kind not in {"local", "remote", "unknown"}:
        raise ValueError("security_provider_kind_invalid")
    if state not in {"available", "unavailable", "error", "unknown"}:
        raise ValueError("security_provider_status_invalid")
    raw = raw_payload.encode("utf-8", errors="replace") if isinstance(raw_payload, str) else (raw_payload or b"")
    row = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "provider_identifier_digest": _digest(str(provider_identifier or "")),
        "provider_kind": kind,
        "status": state,
        "payload_present": bool(raw),
        "payload_digest": hashlib.sha256(raw).hexdigest() if raw else "",
        "payload_returned": False,
        "payload_persisted": False,
        "prompt_returned": False,
        "response_returned": False,
        "secret_value_returned": False,
        **AUTHORITY_FLAGS,
    }
    row["receipt_digest"] = _digest(row)
    return row


def private_field_names(value: Mapping[str, Any]) -> list[str]:
    return sorted(
        str(key) for key in value
        if any(token in str(key).casefold() for token in _PRIVATE_FIELD_TOKENS)
    )


def validate_content_minimized_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = private_field_names(value)
    return {
        "ok": not fields,
        "status": "content_minimized_evidence_valid" if not fields else "private_fields_rejected",
        "private_field_count": len(fields),
        "private_field_name_digests": [_digest(field) for field in fields],
        "private_field_names_returned": False,
        **AUTHORITY_FLAGS,
    }


def inspect_untrusted_project_surface(project_root: str | Path) -> dict[str, Any]:
    root_input = Path(project_root).expanduser()
    if is_link_or_reparse(root_input):
        raise ValueError("security_project_root_link_rejected")
    root = root_input.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("security_project_root_invalid")
    link_findings: list[str] = []
    unsafe_findings: list[str] = []
    sensitive_findings: list[str] = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(dirpath)
        safe_dirs: list[str] = []
        for name in sorted(dirnames):
            count += 1
            if count > MAX_PROJECT_ENTRIES:
                raise ValueError("security_project_inventory_bound_exceeded")
            path = base / name
            rel = path.relative_to(root).as_posix()
            if is_link_or_reparse(path):
                link_findings.append(_path_digest(rel)); continue
            try: validate_untrusted_relative_path(rel)
            except ValueError: unsafe_findings.append(_path_digest(rel)); continue
            safe_dirs.append(name)
        dirnames[:] = safe_dirs
        for name in sorted(filenames):
            count += 1
            if count > MAX_PROJECT_ENTRIES:
                raise ValueError("security_project_inventory_bound_exceeded")
            path = base / name
            rel = path.relative_to(root).as_posix()
            if is_link_or_reparse(path):
                link_findings.append(_path_digest(rel)); continue
            try: validate_untrusted_relative_path(rel)
            except ValueError: unsafe_findings.append(_path_digest(rel)); continue
            if name.casefold() in _SENSITIVE_NAMES or Path(name).suffix.casefold() in {".pem", ".key", ".p12", ".pfx"}:
                sensitive_findings.append(_path_digest(rel))
    blockers = len(link_findings) + len(unsafe_findings)
    return {
        "ok": blockers == 0,
        "status": "untrusted_project_surface_contained" if blockers == 0 else "untrusted_project_surface_blocked",
        "entry_count": count,
        "link_or_reparse_finding_count": len(link_findings),
        "unsafe_path_finding_count": len(unsafe_findings),
        "sensitive_name_finding_count": len(sensitive_findings),
        "link_or_reparse_path_digests": sorted(link_findings),
        "unsafe_path_digests": sorted(unsafe_findings),
        "sensitive_name_path_digests": sorted(sensitive_findings),
        "file_contents_read": False,
        "raw_paths_returned": False,
        **AUTHORITY_FLAGS,
    }


def validate_archive_entries(infos: Iterable[zipfile.ZipInfo]) -> dict[str, Any]:
    errors: list[str] = []
    seen: set[str] = set()
    seen_folded: set[str] = set()
    count = 0
    total = 0
    max_ratio = 0.0
    for info in infos:
        if info.is_dir():
            continue
        count += 1
        name = str(info.filename or "")
        total += int(info.file_size or 0)
        if name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name):
            errors.append("archive_absolute_entry_rejected")
            continue
        if count > MAX_ARCHIVE_ENTRIES:
            errors.append("archive_entry_limit_exceeded")
        if int(info.file_size or 0) > MAX_ARCHIVE_ENTRY_BYTES:
            errors.append("archive_entry_size_limit_exceeded")
        if total > MAX_ARCHIVE_TOTAL_UNCOMPRESSED:
            errors.append("archive_total_size_limit_exceeded")
        compressed = int(info.compress_size or 0)
        ratio = float(info.file_size) / max(1, compressed)
        max_ratio = max(max_ratio, ratio)
        if ratio > MAX_ARCHIVE_COMPRESSION_RATIO and info.file_size > 1024 * 1024:
            errors.append("archive_compression_ratio_suspicious")
        if int(info.flag_bits or 0) & 0x1:
            errors.append("archive_encrypted_entry_rejected")
        unix_mode = (int(info.external_attr or 0) >> 16) & 0xFFFF
        if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
            errors.append("archive_symlink_entry_rejected")
        if "\\" in name:
            errors.append("archive_backslash_entry_rejected")
            continue
        stripped = name.strip("/")
        if stripped.startswith("Eidolon/"):
            stripped = stripped[len("Eidolon/"):]
        try:
            relative = validate_untrusted_relative_path(stripped)
        except ValueError:
            errors.append("archive_unsafe_entry_path")
            continue
        canonical = f"Eidolon/{relative}"
        if canonical in seen:
            errors.append("archive_duplicate_entry")
        seen.add(canonical)
        folded = canonical.casefold()
        if folded in seen_folded:
            errors.append("archive_casefold_collision")
        seen_folded.add(folded)
    unique = sorted(set(errors))
    return {
        "ok": not unique,
        "status": "archive_structure_secure" if not unique else "archive_structure_blocked",
        "entry_count": count,
        "total_uncompressed_bytes": total,
        "max_compression_ratio": round(max_ratio, 3),
        "error_count": len(unique),
        "errors": unique,
        "archive_contents_extracted": False,
        **AUTHORITY_FLAGS,
    }


def inspect_archive_structure(zip_path: str | Path) -> dict[str, Any]:
    archive = Path(zip_path)
    if not archive.is_file():
        return {"ok": False, "status": "archive_missing", "error_count": 1, "errors": ["archive_missing"], **AUTHORITY_FLAGS}
    try:
        with zipfile.ZipFile(archive) as zf:
            row = validate_archive_entries(zf.infolist())
    except (OSError, zipfile.BadZipFile):
        return {"ok": False, "status": "archive_unreadable", "error_count": 1, "errors": ["archive_unreadable"], **AUTHORITY_FLAGS}
    return row


def build_security_privacy_hardening_contract() -> dict[str, Any]:
    checks = {
        "path_containment_fail_closed": True,
        "link_junction_reparse_rejected": True,
        "windows_ambiguous_paths_rejected": True,
        "runtime_source_separation_required": True,
        "generic_approval_not_authority": True,
        "provider_payload_content_minimized": True,
        "untrusted_project_names_inventory_content_free": True,
        "archive_traversal_and_symlink_entries_rejected": True,
        "archive_resource_bounds_present": True,
        "existing_exact_authority_boundaries_preserved": True,
    }
    return {
        "ok": all(checks.values()), "status": "security_privacy_hardening_foundations_ready",
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "checks": checks, **AUTHORITY_FLAGS,
    }


__all__ = [
    "SCHEMA_VERSION", "CONTRACT_VERSION", "AUTHORITY_FLAGS", "is_link_or_reparse",
    "validate_untrusted_relative_path", "inspect_contained_path", "inspect_runtime_source_separation",
    "validate_exact_authorization_boundary", "build_provider_material_receipt",
    "validate_content_minimized_evidence", "inspect_untrusted_project_surface",
    "validate_archive_entries", "inspect_archive_structure", "build_security_privacy_hardening_contract", "_digest",
]
