from __future__ import annotations

"""Preview-first, digest-bound release-history reconciliation.

Only bounded corrections are supported: exact duplicate removal and safe section
movement. Conflicting claims, malformed headings, and ambiguous version tokens
remain untouched for operator review.
"""

from functools import cmp_to_key
import hashlib
import os
from pathlib import Path
import time
from typing import Any, Callable
import uuid

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_history import ReleaseHistoryEntry, compare_version_tuples, parse_release_history_text
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_history import ReleaseHistoryEntry, compare_version_tuples, parse_release_history_text


def _root(path: str | Path | None) -> Path:
    return Path(path or Path(__file__).resolve().parents[1]).resolve()


def _history_path(root_dir: str | Path | None) -> Path:
    return (_root(root_dir) / "README_RELEASE_HISTORY.md").resolve()


def _runtime_root(path: str | Path | None) -> Path | None:
    if path:
        return Path(path).resolve()
    explicit = os.environ.get("EIDOLON_RUNTIME_ROOT", "").strip()
    if explicit:
        return Path(explicit).resolve()
    data_dir = os.environ.get("EIDOLON_DATA_DIR", "").strip()
    if data_dir:
        candidate = Path(data_dir).resolve()
        return candidate.parent if candidate.name == "data" else candidate
    return None


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _entry_cmp(left: ReleaseHistoryEntry, right: ReleaseHistoryEntry) -> int:
    # Newest entries first. Stable input order breaks equal-version ties.
    result = compare_version_tuples(left.ordering_tuple, right.ordering_tuple)
    return -result if result else (left.index > right.index) - (left.index < right.index)


def _proposal(text: str, parsed: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    entries: list[ReleaseHistoryEntry] = list(parsed.get("entries") or [])
    if not entries:
        return text, []
    lines = text.splitlines(keepends=True)
    preamble = "".join(lines[: entries[0].heading_line - 1])

    exact_duplicate_ids = {
        str(group.get("identity") or "")
        for group in parsed.get("duplicate_groups") or []
        if group.get("exact_duplicate") and not group.get("conflicting_claims")
    }
    retained: list[ReleaseHistoryEntry] = []
    seen_exact: set[str] = set()
    removed: list[ReleaseHistoryEntry] = []
    for entry in entries:
        if entry.identity in exact_duplicate_ids:
            if entry.identity in seen_exact:
                removed.append(entry)
                continue
            seen_exact.add(entry.identity)
        retained.append(entry)

    ordered = sorted(retained, key=cmp_to_key(_entry_cmp))
    actions: list[dict[str, Any]] = []
    if removed:
        actions.append({
            "action": "remove_exact_duplicate_sections",
            "count": len(removed),
            "identities": sorted({entry.identity for entry in removed}),
        })
    if [entry.index for entry in ordered] != [entry.index for entry in retained]:
        actions.append({
            "action": "move_sections_newest_first",
            "count": len(ordered),
        })
    if not actions:
        return text, []
    return preamble + "".join(entry.section_text for entry in ordered), actions


def _preview_token(original_sha256: str, proposed_sha256: str, actions: list[dict[str, Any]]) -> str:
    material = "\n".join((
        "release-history-reconciliation-v1",
        original_sha256,
        proposed_sha256,
        repr(actions),
    ))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def preview_release_history_reconciliation(root_dir: str | Path | None = None) -> dict[str, Any]:
    target = _history_path(root_dir)
    try:
        raw = target.read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        return {
            "ok": False,
            "status": "history_unreadable_preserved",
            "error_type": type(error).__name__,
            "preview_only": True,
            "content_free": True,
        }
    parsed = parse_release_history_text(text)
    original_sha = _digest(raw)
    malformed_count = len(parsed.get("malformed_headings") or [])
    ambiguous_count = len(parsed.get("ambiguous_headings") or [])
    conflicting_count = int(parsed.get("conflicting_duplicate_count") or 0)
    if malformed_count or ambiguous_count or conflicting_count:
        return {
            "ok": False,
            "status": "operator_review_required",
            "history_sha256": original_sha,
            "entry_count": int(parsed.get("entry_count") or 0),
            "malformed_heading_count": malformed_count,
            "ambiguous_heading_count": ambiguous_count,
            "conflicting_duplicate_count": conflicting_count,
            "ordering_violation_count": int(parsed.get("ordering_violation_count") or 0),
            "exact_duplicate_count": sum(bool(group.get("exact_duplicate")) for group in parsed.get("duplicate_groups") or []),
            "correction_available": False,
            "preview_only": True,
            "payload_included": False,
            "absolute_path_included": False,
            "content_free": True,
        }
    proposed_text, actions = _proposal(text, parsed)
    proposed_raw = proposed_text.encode("utf-8")
    proposed_sha = _digest(proposed_raw)
    changed = proposed_sha != original_sha
    return {
        "ok": True,
        "status": "correction_available" if changed else "already_aligned",
        "history_sha256": original_sha,
        "proposed_sha256": proposed_sha,
        "preview_token": _preview_token(original_sha, proposed_sha, actions),
        "entry_count": int(parsed.get("entry_count") or 0),
        "duplicate_version_count": int(parsed.get("duplicate_version_count") or 0),
        "exact_duplicate_count": sum(bool(group.get("exact_duplicate")) and not bool(group.get("conflicting_claims")) for group in parsed.get("duplicate_groups") or []),
        "conflicting_duplicate_count": 0,
        "ordering_violation_count": int(parsed.get("ordering_violation_count") or 0),
        "actions": actions,
        "action_count": len(actions),
        "correction_available": changed,
        "operator_confirmation_required": changed,
        "private_backup_required": changed,
        "changed": changed,
        "preview_only": True,
        "payload_included": False,
        "absolute_path_included": False,
        "content_free": True,
    }


def _atomic_text_replace(
    target: Path,
    payload: bytes,
    *,
    expected_sha256: str,
    fault_hook: Callable[[str], None] | None = None,
) -> None:
    temporary = target.with_name(f".{target.name}.history-{os.getpid()}-{uuid.uuid4().hex}.tmp")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if fault_hook is not None:
        fault_hook("before_replace")
    os.replace(temporary, target)
    if fault_hook is not None:
        fault_hook("after_replace_before_verify")
    if _digest(target.read_bytes()) != expected_sha256:
        raise OSError("release history post-write verification failed")
    try:
        descriptor = os.open(str(target.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def apply_release_history_reconciliation(
    *,
    preview_token: str,
    operator_confirmed: bool,
    root_dir: str | Path | None = None,
    runtime_root: str | Path | None = None,
    fault_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    if operator_confirmed is not True:
        return {"ok": False, "status": "literal_confirmation_required", "content_free": True}
    preview = preview_release_history_reconciliation(root_dir)
    if not preview.get("ok"):
        return preview
    if str(preview_token or "") != str(preview.get("preview_token") or ""):
        return {"ok": False, "status": "stale_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    if not preview.get("changed"):
        return {"ok": True, "status": "already_aligned", "changed": False, "content_free": True}
    private_root = _runtime_root(runtime_root)
    if private_root is None:
        return {"ok": False, "status": "private_runtime_root_required", "content_free": True}

    target = _history_path(root_dir)
    try:
        with metadata_mutation_lock(target, timeout_seconds=5.0):
            current = target.read_bytes()
            if _digest(current) != preview.get("history_sha256"):
                return {"ok": False, "status": "stale_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
            text = current.decode("utf-8-sig")
            parsed = parse_release_history_text(text)
            proposed_text, actions = _proposal(text, parsed)
            proposed = proposed_text.encode("utf-8")
            proposed_sha = _digest(proposed)
            if proposed_sha != preview.get("proposed_sha256") or actions != preview.get("actions"):
                return {"ok": False, "status": "stale_or_mismatched_preview", "stale_confirmation": True, "content_free": True}

            backup_dir = private_root / "data" / "release_history_reconciliation" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = backup_dir / f"README_RELEASE_HISTORY.{preview['history_sha256'][:16]}.{uuid.uuid4().hex[:12]}.bak"
            try:
                with backup.open("xb") as handle:
                    handle.write(current); handle.flush(); os.fsync(handle.fileno())
                if _digest(backup.read_bytes()) != preview.get("history_sha256"):
                    return {"ok": False, "status": "backup_verification_failed", "content_free": True}
                if fault_hook is not None:
                    fault_hook("after_backup")
                _atomic_text_replace(target, proposed, expected_sha256=proposed_sha, fault_hook=fault_hook)
            except Exception as error:
                restored = False
                try:
                    if backup.is_file() and _digest(backup.read_bytes()) == preview.get("history_sha256"):
                        restore_tmp = target.with_name(f".{target.name}.restore-{uuid.uuid4().hex}.tmp")
                        restore_tmp.write_bytes(backup.read_bytes())
                        os.replace(restore_tmp, target)
                        restored = _digest(target.read_bytes()) == preview.get("history_sha256")
                except OSError:
                    restored = False
                return {
                    "ok": False,
                    "status": "write_interrupted_original_restored" if restored else "write_result_uncertain",
                    "original_restored": restored,
                    "uncertain_result": not restored,
                    "error_type": type(error).__name__,
                    "content_free": True,
                }
            final = parse_release_history_text(target.read_text(encoding="utf-8"))
            if (
                _digest(target.read_bytes()) != proposed_sha
                or final.get("duplicate_version_count")
                or final.get("ordering_violation_count")
                or not final.get("ok")
            ):
                try:
                    restore_tmp = target.with_name(f".{target.name}.restore-{uuid.uuid4().hex}.tmp")
                    restore_tmp.write_bytes(backup.read_bytes())
                    os.replace(restore_tmp, target)
                except OSError:
                    pass
                return {"ok": False, "status": "post_write_verification_failed", "uncertain_result": True, "content_free": True}
            return {
                "ok": True,
                "status": "reconciled",
                "changed": True,
                "action_count": len(actions),
                "actions": actions,
                "backup_created": True,
                "backup_verified": True,
                "backup_reference": backup.name,
                "final_sha256": proposed_sha,
                "installed": False,
                "promoted": False,
                "certified": False,
                "content_free": True,
            }
    except MetadataMutationBusy:
        return {"ok": False, "status": "history_mutation_busy", "safe_retry": True, "content_free": True}
