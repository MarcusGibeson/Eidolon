from __future__ import annotations

"""Interrupted installation reconciliation, exact resume, and rollback."""

from collections import Counter
from pathlib import Path, PurePosixPath
import secrets
from typing import Any, Iterable, Mapping

try:
    from process_ownership import process_is_alive
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, sha256_file, utc_now
    from release_installation_preview import _safe_relative, _target_inventory
    from release_installation_transaction import _append_event, _apply_remaining, _atomic_copy, _backup_all, _finalize_installation, _public as _transaction_public, _safe_target_path, _save_transaction, _state_digest, _transaction_identity, active_transaction_private, transaction_directory
except ImportError:
    from process_ownership import process_is_alive
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, sha256_file, utc_now
    from release_installation_preview import _safe_relative, _target_inventory
    from release_installation_transaction import (
        _append_event, _apply_remaining, _atomic_copy, _backup_all, _finalize_installation, _public as _transaction_public,
        _safe_target_path, _save_transaction, _state_digest, _transaction_identity,
        active_transaction_private, transaction_directory,
    )

INSTALLATION_RECOVERY_CONTRACT_VERSION = "1"
INSTALLATION_RECOVERY_DIRECTORY = "release_installation_recovery"
RESUME_CONFIRMATION = "RESUME EXACT INSTALLATION TRANSACTION"
ROLLBACK_CONFIRMATION = "ROLL BACK EXACT INSTALLATION TRANSACTION"
RESUME_ACTION = "resume_exact_interrupted_installation"
ROLLBACK_ACTION = "rollback_exact_installation_transaction"


def recovery_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / INSTALLATION_RECOVERY_DIRECTORY


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": k, "count": found[k]} for k in sorted(found)]


def _file_state(root: Path, path: str) -> tuple[str, str]:
    target = _safe_target_path(root, path)
    if not target.exists(): return "missing", ""
    if target.is_symlink() or not target.is_file(): return "special", ""
    return "file", sha256_file(target)


def _effect_state(root: Path, effect: Mapping[str, Any], completed: bool) -> tuple[bool, str]:
    kind = str(effect.get("kind") or "")
    state, sha = _file_state(root, str(effect.get("path") or ""))
    pre = str(effect.get("target_sha256") or "")
    post = str(effect.get("candidate_sha256") or "")
    if completed:
        if kind == "remove": return state == "missing", "post"
        return state == "file" and sha == post, "post"
    if kind == "add": return state == "missing", "pre"
    return state == "file" and sha == pre, "pre"


def _backup_ok(record: Mapping[str, Any], effect: Mapping[str, Any]) -> bool:
    path = str(effect.get("path") or "")
    backup = Path(str(record.get("backup_root_path") or "")).joinpath(*PurePosixPath(_safe_relative(path)).parts)
    expected = str(effect.get("target_sha256") or "")
    return backup.is_file() and not backup.is_symlink() and bool(expected) and sha256_file(backup) == expected


def inspect_installation_transaction(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer, record = active_transaction_private(runtime_root)
    if not record:
        return {"ok": True, "status": "no_transaction", "transaction_present": False, "paths_suppressed": True, "records_external": True, "content_free": True}
    findings: list[dict[str, Any]] = []
    if str(record.get("transaction_identity_sha256") or "") != _transaction_identity(record): findings.append({"kind": "transaction_identity_mismatch"})
    if str(record.get("transaction_state_sha256") or "") != _state_digest(record): findings.append({"kind": "transaction_state_mismatch"})
    if str(pointer.get("transaction_identity_sha256") or "") != str(record.get("transaction_identity_sha256") or ""): findings.append({"kind": "active_transaction_identity_mismatch"})
    target_root = Path(str(record.get("target_root_path") or ""))
    completed = set(str(x) for x in record.get("effects_completed") or [])
    rollback_completed = set(str(x) for x in record.get("rollback_completed") or [])
    backup_completed = set(str(x) for x in record.get("backups_completed") or [])
    current_rows: list[dict[str, Any]] = []
    for effect in record.get("effects", []):
        kind = str(effect.get("kind") or "")
        if kind not in {"add", "replace", "remove"}: continue
        path = str(effect.get("path") or "")
        good, expected_side = _effect_state(target_root, effect, path in completed and path not in rollback_completed)
        if not good: findings.append({"kind": "target_external_change_or_uncertain", "path": path})
        if kind in {"replace", "remove"} and path in backup_completed and not _backup_ok(record, effect): findings.append({"kind": "backup_changed_or_missing", "path": path})
        current_rows.append({"path": path, "expected_side": expected_side, "matches": good})
    owner_alive = False
    if not bool(record.get("owner_released")):
        alive = process_is_alive(int(record.get("owner_pid") or 0), str(record.get("owner_start_identity") or ""))
        if alive is True: owner_alive = True
        elif alive is None: findings.append({"kind": "transaction_owner_uncertain"})
    state = str(record.get("state") or "")
    if owner_alive and state in {"applying", "rolling_back"}: status = "live_owner"
    elif findings: status = "uncertain"
    elif state == "installed_unpromoted": status = "installed_unpromoted"
    elif state == "rolled_back": status = "rolled_back"
    elif state in {"interrupted", "applying"}: status = "rollback_ready" if completed else "resume_ready"
    elif state == "rollback_interrupted": status = "rollback_ready"
    else: status = state or "unknown"
    inventory = _target_inventory(target_root) if target_root.is_dir() else {"ok": False, "digest": ""}
    return {
        "ok": not findings and not owner_alive,
        "status": status,
        "transaction_present": True,
        "transaction_id": str(record.get("transaction_id") or ""),
        "transaction_identity_sha256": str(record.get("transaction_identity_sha256") or ""),
        "transaction_state_sha256": str(record.get("transaction_state_sha256") or ""),
        "generation": int(record.get("generation") or 0),
        "candidate_id": str(record.get("candidate_id") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "current_target_inventory_sha256": str(inventory.get("digest") or ""),
        "completed_effect_count": len(completed), "total_effect_count": int(record.get("total_effect_count") or 0),
        "backup_count": len(backup_completed), "owner_alive": owner_alive,
        "findings": _counts(findings), "finding_count": len(findings),
        "resume_available": state in {"interrupted", "applying"} and not findings and not owner_alive, "rollback_available": state not in {"rolled_back"} and ((bool(completed) or bool(record.get("backups_verified_before_mutation"))) and not findings and not owner_alive or status == "installed_unpromoted"),
        "paths_suppressed": True, "records_external": True, "content_free": True,
        "promoted": False, "certified": False,
    }


def _token_digest(token: str) -> str:
    return digest_payload({"contract": "eidolon-installation-recovery-token-file-v1", "token": token})


def _binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-installation-recovery-authorization-v1",
        "token_id": str(record.get("token_id") or ""), "action": str(record.get("action") or ""),
        "transaction_id": str(record.get("transaction_id") or ""), "generation": int(record.get("generation") or 0),
        "transaction_identity_sha256": str(record.get("transaction_identity_sha256") or ""),
        "transaction_state_sha256": str(record.get("transaction_state_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "current_target_inventory_sha256": str(record.get("current_target_inventory_sha256") or ""),
        "completed_effects_sha256": str(record.get("completed_effects_sha256") or ""),
        "rollback_effects_sha256": str(record.get("rollback_effects_sha256") or ""),
        "nonce": str(record.get("nonce") or ""),
    })


def _preview(action: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    status = inspect_installation_transaction(runtime_root=runtime_root)
    _, record = active_transaction_private(runtime_root)
    allowed = status.get("resume_available") if action == RESUME_ACTION else status.get("rollback_available")
    if not allowed or not record:
        return {"ok": False, "status": "exact_recovery_not_available", "authorization_token": "", "findings": status.get("findings", []), "paths_suppressed": True, "records_external": True, "content_free": True}
    inventory_sha = str(status.get("current_target_inventory_sha256") or "")
    rollback_effects = []
    if action == ROLLBACK_ACTION:
        for effect in reversed(list(record.get("effects") or [])):
            kind = str(effect.get("kind") or "")
            if kind in {"add", "replace", "remove"}:
                rollback_effects.append({"path": str(effect.get("path") or ""), "action": "delete_added" if kind == "add" else "restore_backup", "pre_sha256": str(effect.get("target_sha256") or ""), "post_sha256": str(effect.get("candidate_sha256") or "")})
    nonce = secrets.token_hex(24); token_id = f"installation-recovery-auth-{secrets.token_hex(12)}"
    auth = {
        "schema": "eidolon-installation-recovery-authorization-v1", "token_id": token_id, "created_at": utc_now(), "action": action,
        "transaction_id": str(record.get("transaction_id") or ""), "generation": int(record.get("generation") or 0),
        "transaction_identity_sha256": str(record.get("transaction_identity_sha256") or ""), "transaction_state_sha256": str(record.get("transaction_state_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""), "current_target_inventory_sha256": inventory_sha,
        "completed_effects_sha256": digest_payload({"completed": list(record.get("effects_completed") or [])}),
        "rollback_effects_sha256": digest_payload({"effects": rollback_effects}), "rollback_effects": rollback_effects,
        "literal_confirmation": RESUME_CONFIRMATION if action == RESUME_ACTION else ROLLBACK_CONFIRMATION,
        "nonce": nonce, "content_free": True,
    }
    auth["authorization_binding_sha256"] = _binding(auth)
    token = f"{token_id}.{auth['authorization_binding_sha256']}.{nonce}"
    atomic_json(recovery_directory(runtime_root) / "authorizations" / f"{_token_digest(token)}.json", auth)
    return {
        "ok": True, "status": "resume_preview" if action == RESUME_ACTION else "rollback_preview",
        "authorization_token": token, "authorization_binding_sha256": auth["authorization_binding_sha256"],
        "transaction_id": auth["transaction_id"], "generation": auth["generation"], "target_project_id": auth["target_project_id"],
        "proposed_effect_count": len(rollback_effects) if action == ROLLBACK_ACTION else int(record.get("total_effect_count") or 0) - len(record.get("effects_completed") or []),
        "literal_confirmation": auth["literal_confirmation"], "paths_suppressed": True, "records_external": True, "content_free": True,
    }


def preview_installation_resume(*, runtime_root: str | Path | None = None) -> dict[str, Any]: return _preview(RESUME_ACTION, runtime_root=runtime_root)
def preview_installation_rollback(*, runtime_root: str | Path | None = None) -> dict[str, Any]: return _preview(ROLLBACK_ACTION, runtime_root=runtime_root)


def _load_auth(runtime_root: str | Path | None, token: str) -> dict[str, Any]:
    return read_json(recovery_directory(runtime_root) / "authorizations" / f"{_token_digest(token)}.json")


def _used(runtime_root: str | Path | None, token: str) -> bool:
    return (recovery_directory(runtime_root) / "used" / f"{_token_digest(token)}.json").is_file()


def _mark_used(runtime_root: str | Path | None, token: str, status: str) -> None:
    atomic_json(recovery_directory(runtime_root) / "used" / f"{_token_digest(token)}.json", {"schema": "eidolon-installation-recovery-token-use-v1", "status": status, "used_at": utc_now(), "content_free": True})


def _validate(runtime_root: str | Path | None, token: str, confirm: str, action: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    expected = RESUME_CONFIRMATION if action == RESUME_ACTION else ROLLBACK_CONFIRMATION
    findings: list[dict[str, Any]] = []
    if not isinstance(confirm, str) or confirm != expected: findings.append({"kind": "literal_confirmation_required"})
    if _used(runtime_root, token): findings.append({"kind": "authorization_reused"})
    auth = _load_auth(runtime_root, token)
    if not auth or str(auth.get("authorization_binding_sha256") or "") != _binding(auth): findings.append({"kind": "authorization_missing_or_malformed"})
    parts = token.split(".") if isinstance(token, str) else []
    if auth and (len(parts) != 3 or parts != [str(auth.get("token_id") or ""), str(auth.get("authorization_binding_sha256") or ""), str(auth.get("nonce") or "")]): findings.append({"kind": "authorization_token_mismatch"})
    _, record = active_transaction_private(runtime_root)
    status = inspect_installation_transaction(runtime_root=runtime_root)
    if not record: findings.append({"kind": "transaction_missing"})
    for field in ("transaction_id", "transaction_identity_sha256", "transaction_state_sha256", "target_project_id"):
        if auth and str(auth.get(field) or "") != str(record.get(field) or ""): findings.append({"kind": f"authorization_{field}_mismatch"})
    if auth and int(auth.get("generation") or 0) != int(record.get("generation") or 0): findings.append({"kind": "authorization_generation_mismatch"})
    if auth and str(auth.get("current_target_inventory_sha256") or "") != str(status.get("current_target_inventory_sha256") or ""): findings.append({"kind": "target_changed_after_recovery_preview"})
    if auth and str(auth.get("completed_effects_sha256") or "") != digest_payload({"completed": list(record.get("effects_completed") or [])}): findings.append({"kind": "completed_steps_changed"})
    if auth and str(auth.get("action") or "") != action: findings.append({"kind": "authorization_action_mismatch"})
    if auth and action == ROLLBACK_ACTION:
        rollback_effects = []
        for effect in reversed(list(record.get("effects") or [])):
            kind = str(effect.get("kind") or "")
            if kind in {"add", "replace", "remove"}:
                rollback_effects.append({"path": str(effect.get("path") or ""), "action": "delete_added" if kind == "add" else "restore_backup", "pre_sha256": str(effect.get("target_sha256") or ""), "post_sha256": str(effect.get("candidate_sha256") or "")})
        if str(auth.get("rollback_effects_sha256") or "") != digest_payload({"effects": rollback_effects}): findings.append({"kind": "rollback_effects_changed"})
    return auth, record, findings


def resume_installation_transaction(authorization_token: str, *, confirm: str, runtime_root: str | Path | None = None, _interrupt_at: str = "") -> dict[str, Any]:
    token = authorization_token if isinstance(authorization_token, str) else ""
    auth, record, findings = _validate(runtime_root, token, confirm, RESUME_ACTION)
    status = inspect_installation_transaction(runtime_root=runtime_root)
    if not status.get("resume_available"): findings.append({"kind": "resume_not_available"})
    if findings: return _transaction_public({"status": "resume_rejected", "contradictions": findings})
    _mark_used(runtime_root, token, "resume_started")
    record["state"] = record["status"] = "applying"; record["owner_released"] = False
    _append_event(runtime_root, record["transaction_id"], record, {"kind": "resume_started"}); _save_transaction(runtime_root, record)
    try:
        if not bool(record.get("backups_verified_before_mutation")):
            if not _backup_all(runtime_root, record, interrupt_at=_interrupt_at): return _transaction_public(record)
        if not _apply_remaining(runtime_root, record, interrupt_at=_interrupt_at): return _transaction_public(record)
        return _transaction_public(_finalize_installation(runtime_root, record))
    except Exception as exc:
        record["state"] = record["status"] = "uncertain"; record["owner_released"] = True
        record.setdefault("contradictions", []).append({"kind": str(exc).split(":", 1)[0]})
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "resume_failed", "failure_kind": str(exc).split(":",1)[0]}); _save_transaction(runtime_root, record)
        return _transaction_public(record)


def rollback_installation_transaction(authorization_token: str, *, confirm: str, runtime_root: str | Path | None = None, _interrupt_after: int = 0) -> dict[str, Any]:
    token = authorization_token if isinstance(authorization_token, str) else ""
    auth, record, findings = _validate(runtime_root, token, confirm, ROLLBACK_ACTION)
    status = inspect_installation_transaction(runtime_root=runtime_root)
    if not status.get("rollback_available"): findings.append({"kind": "rollback_not_available"})
    if findings: return _transaction_public({"status": "rollback_rejected", "contradictions": findings})
    _mark_used(runtime_root, token, "rollback_started")
    target_root = Path(record["target_root_path"]); backup_root = Path(record["backup_root_path"])
    record["state"] = record["status"] = "rolling_back"; record["owner_released"] = False
    _append_event(runtime_root, record["transaction_id"], record, {"kind": "rollback_started"}); _save_transaction(runtime_root, record)
    done = set(str(x) for x in record.get("rollback_completed") or [])
    applied = 0
    try:
        for effect in reversed(list(record.get("effects") or [])):
            kind = str(effect.get("kind") or ""); path = str(effect.get("path") or "")
            if kind not in {"add", "replace", "remove"} or path in done: continue
            target = _safe_target_path(target_root, path, create_parents=kind in {"replace", "remove"})
            state, sha = _file_state(target_root, path)
            pre = str(effect.get("target_sha256") or ""); post = str(effect.get("candidate_sha256") or "")
            if kind == "add":
                if state == "missing": pass
                elif state == "file" and sha == post: target.unlink()
                else: raise RuntimeError(f"rollback_external_change:{path}")
            else:
                if state == "file" and sha == pre: pass
                else:
                    expected_post = state == "missing" if kind == "remove" else state == "file" and sha == post
                    if not expected_post: raise RuntimeError(f"rollback_external_change:{path}")
                    backup = backup_root.joinpath(*PurePosixPath(_safe_relative(path)).parts)
                    if not backup.is_file() or sha256_file(backup) != pre: raise RuntimeError(f"rollback_backup_invalid:{path}")
                    _atomic_copy(backup, target, record["transaction_id"])
            state2, sha2 = _file_state(target_root, path)
            if kind == "add": good = state2 == "missing"
            else: good = state2 == "file" and sha2 == pre
            if not good: raise RuntimeError(f"rollback_post_verification_failed:{path}")
            record.setdefault("rollback_completed", []).append(path); applied += 1
            _append_event(runtime_root, record["transaction_id"], record, {"kind": "rollback_effect_applied", "path": path, "original_action": kind})
            record["target_current_inventory_sha256"] = str(_target_inventory(target_root).get("digest") or ""); _save_transaction(runtime_root, record)
            if _interrupt_after and applied >= _interrupt_after:
                record["state"] = record["status"] = "rollback_interrupted"; record["owner_released"] = True
                _append_event(runtime_root, record["transaction_id"], record, {"kind": "rollback_interrupted"}); _save_transaction(runtime_root, record); return _transaction_public(record)
        record["state"] = record["status"] = "rolled_back"; record["rollback_state"] = "rolled_back"; record["owner_released"] = True; record["rolled_back_at"] = utc_now()
        receipt_path = transaction_directory(runtime_root) / "installed_receipts" / f"{record['transaction_id']}.json"
        receipt = read_json(receipt_path)
        if receipt:
            receipt["state"] = "rolled_back"; receipt["rolled_back_at"] = utc_now(); receipt["promoted"] = False; receipt["certified"] = False
            receipt.pop("receipt_sha256", None); receipt["receipt_sha256"] = digest_payload(receipt); atomic_json(receipt_path, receipt)
            atomic_json(transaction_directory(runtime_root) / "active_installed_receipt.json", {"schema": "eidolon-installed-state-receipt-v1", "transaction_id": record["transaction_id"], "receipt_sha256": receipt["receipt_sha256"], "target_project_id": record["target_project_id"], "content_free": True})
            record["installed_receipt_sha256"] = receipt["receipt_sha256"]
        record["target_current_inventory_sha256"] = str(_target_inventory(target_root).get("digest") or "")
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "rollback_finalized", "state": "rolled_back"}); _save_transaction(runtime_root, record)
        return _transaction_public(record)
    except Exception as exc:
        record["state"] = record["status"] = "uncertain"; record["owner_released"] = True
        record.setdefault("contradictions", []).append({"kind": str(exc).split(":", 1)[0]})
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "rollback_failed", "failure_kind": str(exc).split(":",1)[0]}); _save_transaction(runtime_root, record)
        return _transaction_public(record)
