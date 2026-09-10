from __future__ import annotations
"""v1378 exact-authorized rollback of campaign-owned workspace mutations.

Rollback records are private runtime artifacts. Public receipts expose only
content-free digests. Execution touches only paths named by the exact transaction
and fails closed if any owned path changed after the transaction, preserving
operator or other-session edits rather than overwriting them.
"""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1378.8"
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
KINDS = {"created", "modified", "deleted"}
ABSENT_DIGEST = hashlib.sha256(b"eidolon:v1378:absent").hexdigest()
DENIED = {
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}


def _d(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _b(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _store(runtime_root: str | Path | None, campaign_digest: str, transaction_id: str) -> Path:
    root = Path(runtime_root or "data").expanduser().resolve() / "campaign_rollbacks" / campaign_digest / transaction_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".rollback.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as h:
            h.write(data); h.flush(); os.fsync(h.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_bytes(path, (json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode())


def _safe_target(workspace_root: str | Path, relative_path: str) -> tuple[Path, Path] | None:
    root = Path(workspace_root).expanduser().resolve(strict=True)
    posix = PurePosixPath(str(relative_path or ""))
    if not relative_path or posix.is_absolute() or ".." in posix.parts or "." in posix.parts or "" in posix.parts:
        return None
    target = root.joinpath(*posix.parts)
    try:
        resolved = target.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    probe = root
    for part in posix.parts[:-1]:
        probe = probe / part
        if probe.exists() and probe.is_symlink():
            return None
    if target.exists() and target.is_symlink():
        return None
    return root, target


def record_campaign_mutation_transaction(
    *,
    campaign_record_digest: str,
    transaction_id: str,
    workspace_root: str | Path,
    operations: Sequence[Mapping[str, Any]],
    recording_authorized: bool,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Persist rollback material for a transaction whose mutation already occurred.

    Each operation contains ``relative_path``, ``kind``, ``after_digest`` and for
    modified/deleted paths ``before_bytes``. Created paths have no before bytes.
    The current workspace must exactly match each claimed after-state.
    """
    if not recording_authorized:
        return {"ok": False, "status": "rollback_recording_authority_required", "action_executed": False, **DENIED}
    if not DIGEST_RE.fullmatch(str(campaign_record_digest or "")) or not ID_RE.fullmatch(str(transaction_id or "")):
        return {"ok": False, "status": "rollback_transaction_identity_invalid", "action_executed": False, **DENIED}
    if not operations or len(operations) > 1024:
        return {"ok": False, "status": "rollback_operation_set_invalid", "action_executed": False, **DENIED}
    try:
        workspace = Path(workspace_root).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return {"ok": False, "status": "rollback_workspace_unavailable", "action_executed": False, **DENIED}
    if not workspace.is_dir() or workspace.is_symlink():
        return {"ok": False, "status": "rollback_workspace_unsafe", "action_executed": False, **DENIED}

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    private_before: dict[str, bytes] = {}
    for raw in operations:
        rel = str(raw.get("relative_path") or "").replace("\\", "/")
        kind = str(raw.get("kind") or "")
        after_digest = str(raw.get("after_digest") or "")
        safe = _safe_target(workspace, rel)
        if safe is None or kind not in KINDS or not DIGEST_RE.fullmatch(after_digest) or rel in seen:
            return {"ok": False, "status": "rollback_operation_invalid", "action_executed": False, **DENIED}
        seen.add(rel); _, target = safe
        before = raw.get("before_bytes", None)
        if kind in {"modified", "deleted"}:
            if not isinstance(before, (bytes, bytearray)):
                return {"ok": False, "status": "rollback_before_image_required", "action_executed": False, **DENIED}
            before_bytes = bytes(before)
            before_digest = _b(before_bytes)
            private_before[_d(rel)] = before_bytes
        else:
            if before not in (None, b""):
                return {"ok": False, "status": "created_path_before_image_forbidden", "action_executed": False, **DENIED}
            before_digest = ABSENT_DIGEST
        if kind == "deleted":
            if target.exists() or after_digest != ABSENT_DIGEST:
                return {"ok": False, "status": "rollback_after_state_mismatch", "action_executed": False, **DENIED}
        else:
            if not target.is_file() or _b(target.read_bytes()) != after_digest:
                return {"ok": False, "status": "rollback_after_state_mismatch", "action_executed": False, **DENIED}
        normalized.append({
            "relative_path": rel,
            "path_digest": _d(rel),
            "kind": kind,
            "before_digest": before_digest,
            "after_digest": after_digest,
        })

    directory = _store(runtime_root, campaign_record_digest, transaction_id)
    manifest_path = directory / "transaction.json"
    if manifest_path.exists():
        try: prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return {"ok": False, "status": "rollback_existing_transaction_invalid", "action_executed": False, **DENIED}
        public = public_rollback_transaction(prior)
        return {"ok": True, "status": "rollback_transaction_duplicate", "transaction": public, "action_executed": False, **DENIED}

    manifest = {
        "contract_version": CONTRACT_VERSION,
        "campaign_record_digest": campaign_record_digest,
        "transaction_id": transaction_id,
        "workspace_root_digest": _d(str(workspace)),
        "operation_count": len(normalized),
        "operations": normalized,
        "transaction_state": "recorded",
        "content_free_public_projection": True,
    }
    manifest["transaction_digest"] = _d(manifest)
    for row in normalized:
        before = private_before.get(row["path_digest"])
        if before is not None:
            _atomic_bytes(directory / "before" / f"{row['path_digest']}.bin", before)
    _atomic_json(manifest_path, manifest)
    return {"ok": True, "status": "rollback_transaction_recorded", "transaction": public_rollback_transaction(manifest), "action_executed": False, **DENIED}


def _load_private_transaction(runtime_root: str | Path | None, campaign_digest: str, transaction_id: str, expected_digest: str) -> tuple[Path, dict[str, Any]] | None:
    directory = _store(runtime_root, campaign_digest, transaction_id)
    path = directory / "transaction.json"
    try: row = json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None
    supplied = str(row.get("transaction_digest") or ""); base = dict(row); base.pop("transaction_digest", None)
    if supplied != expected_digest or supplied != _d(base): return None
    return directory, row


def prepare_campaign_rollback(
    *,
    campaign_record_digest: str,
    transaction_id: str,
    expected_transaction_digest: str,
    workspace_root: str | Path,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    loaded = _load_private_transaction(runtime_root, campaign_record_digest, transaction_id, expected_transaction_digest)
    if loaded is None:
        return {"ok": False, "status": "rollback_transaction_missing_or_stale", "action_executed": False, **DENIED}
    directory, tx = loaded
    try: workspace = Path(workspace_root).expanduser().resolve(strict=True)
    except (OSError, RuntimeError): return {"ok": False, "status": "rollback_workspace_unavailable", "action_executed": False, **DENIED}
    if _d(str(workspace)) != tx.get("workspace_root_digest"):
        return {"ok": False, "status": "rollback_workspace_mismatch", "action_executed": False, **DENIED}
    conflicts: list[str] = []
    for row in tx.get("operations") or []:
        safe = _safe_target(workspace, str(row.get("relative_path") or ""))
        if safe is None:
            conflicts.append(str(row.get("path_digest") or "")); continue
        _, target = safe
        if row.get("kind") == "deleted":
            matches = not target.exists()
        else:
            matches = target.is_file() and _b(target.read_bytes()) == row.get("after_digest")
        if not matches: conflicts.append(str(row.get("path_digest") or ""))
    plan = {
        "contract_version": CONTRACT_VERSION,
        "campaign_record_digest": campaign_record_digest,
        "transaction_id_digest": _d(transaction_id),
        "transaction_digest": expected_transaction_digest,
        "operation_count": int(tx.get("operation_count") or 0),
        "conflict_count": len(conflicts),
        "conflicting_path_digests": sorted(conflicts),
        "rollback_ready": not conflicts,
        "unrelated_paths_touched": False,
        "content_free": True,
        "action_executed": False,
        **DENIED,
    }
    plan["rollback_plan_digest"] = _d(plan)
    phrase = f"ROLLBACK CAMPAIGN TRANSACTION {transaction_id} PLAN {plan['rollback_plan_digest']}"
    return {"ok": True, "status": "campaign_rollback_ready" if not conflicts else "campaign_rollback_blocked_by_external_changes", "rollback_plan": plan, "authorization_phrase": phrase if not conflicts else None, "action_executed": False, **DENIED}


def execute_campaign_rollback(
    *,
    campaign_record_digest: str,
    transaction_id: str,
    expected_transaction_digest: str,
    expected_rollback_plan_digest: str,
    authorization_phrase: str,
    workspace_root: str | Path,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    prepared = prepare_campaign_rollback(campaign_record_digest=campaign_record_digest, transaction_id=transaction_id, expected_transaction_digest=expected_transaction_digest, workspace_root=workspace_root, runtime_root=runtime_root)
    if not prepared.get("ok") or not (prepared.get("rollback_plan") or {}).get("rollback_ready"):
        return {"ok": False, "status": "campaign_rollback_not_ready", "action_executed": False, **DENIED}
    plan = dict(prepared["rollback_plan"])
    if plan.get("rollback_plan_digest") != expected_rollback_plan_digest:
        return {"ok": False, "status": "rollback_plan_stale", "action_executed": False, **DENIED}
    phrase = f"ROLLBACK CAMPAIGN TRANSACTION {transaction_id} PLAN {expected_rollback_plan_digest}"
    if str(authorization_phrase or "").strip() != phrase:
        return {"ok": False, "status": "exact_rollback_authorization_required", "action_executed": False, **DENIED}
    loaded = _load_private_transaction(runtime_root, campaign_record_digest, transaction_id, expected_transaction_digest)
    if loaded is None:
        return {"ok": False, "status": "rollback_transaction_missing_or_stale", "action_executed": False, **DENIED}
    directory, tx = loaded
    workspace = Path(workspace_root).expanduser().resolve(strict=True)
    restored: list[str] = []
    # Re-check immediately before each mutation so late operator edits fail closed.
    for row in tx.get("operations") or []:
        safe = _safe_target(workspace, str(row.get("relative_path") or ""))
        if safe is None:
            return {"ok": False, "status": "rollback_path_became_unsafe", "action_executed": bool(restored), **DENIED}
        _, target = safe
        kind = row.get("kind")
        if kind == "deleted":
            current_matches = not target.exists()
        else:
            current_matches = target.is_file() and _b(target.read_bytes()) == row.get("after_digest")
        if not current_matches:
            return {"ok": False, "status": "rollback_conflict_detected_during_execution", "action_executed": bool(restored), "restored_count": len(restored), **DENIED}
        if kind == "created":
            target.unlink()
        else:
            before_path = directory / "before" / f"{row['path_digest']}.bin"
            try: before = before_path.read_bytes()
            except OSError:
                return {"ok": False, "status": "rollback_before_image_missing", "action_executed": bool(restored), "restored_count": len(restored), **DENIED}
            if _b(before) != row.get("before_digest"):
                return {"ok": False, "status": "rollback_before_image_tampered", "action_executed": bool(restored), "restored_count": len(restored), **DENIED}
            _atomic_bytes(target, before)
        restored.append(str(row.get("path_digest") or ""))
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "campaign_record_digest": campaign_record_digest,
        "transaction_digest": expected_transaction_digest,
        "rollback_plan_digest": expected_rollback_plan_digest,
        "restored_count": len(restored),
        "restored_path_digests": sorted(restored),
        "rollback_executed": True,
        "unrelated_paths_touched": False,
        "content_free": True,
        "release_authorized": False,
        "independent_authority_granted": False,
    }
    receipt["rollback_receipt_digest"] = _d(receipt)
    _atomic_json(directory / "rollback_receipt.json", receipt)
    return {"ok": True, "status": "campaign_rollback_completed", "rollback_receipt": receipt, "action_executed": True, "project_mutation_authorized": True, "source_mutation_authorized": False, "release_authorized": False, "independent_authority_granted": False}


def public_rollback_transaction(tx: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": str(tx.get("contract_version") or CONTRACT_VERSION),
        "campaign_record_digest": str(tx.get("campaign_record_digest") or ""),
        "transaction_id_digest": _d(str(tx.get("transaction_id") or "")),
        "workspace_root_digest": str(tx.get("workspace_root_digest") or ""),
        "operation_count": int(tx.get("operation_count") or 0),
        "owned_path_digests": sorted(str(row.get("path_digest") or "") for row in (tx.get("operations") or [])),
        "transaction_digest": str(tx.get("transaction_digest") or ""),
        "raw_paths_exposed": False,
        "before_images_exposed": False,
        "content_free": True,
    }


def process_campaign_rollback_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show campaign rollback", "inspect campaign rollback", "show rollback plan"}:
        return {"active": False}
    rec = dict((project_state or {}).get("campaign_rollback") or {})
    return {"active": True, "ok": bool(rec), "status": "campaign_rollback_found" if rec else "campaign_rollback_missing", "campaign_rollback": rec, "action_executed": False, **DENIED}


__all__ = [
    "CONTRACT_VERSION", "ABSENT_DIGEST", "record_campaign_mutation_transaction", "prepare_campaign_rollback",
    "execute_campaign_rollback", "public_rollback_transaction", "process_campaign_rollback_control",
]
