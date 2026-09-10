from __future__ import annotations

"""v1273.0-v1273.2 durable ownership and fencing foundations.

The v1273 ownership record sits above the v1272 restart/crash-recovery journal.
It serializes *who may attempt to enter* one bounded external stage, but never
creates the underlying v1265/v1267/v1269 authorization required by that stage.
Expired leases are fenced and require v1272 reconciliation before a successor
owner may execute, because lease expiry is not evidence that the old owner did
nothing.
"""

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _proposal_lock
from self_development_alpha_foundations import _runtime_root
from restart_crash_recovery_foundations import (
    AUTHORITY_FLAGS as RECOVERY_AUTHORITY_FLAGS,
    OPERATION_CODES,
    load_restart_crash_recovery,
    validate_restart_crash_recovery,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1273.2"
DEFAULT_LEASE_SECONDS = 45
MIN_LEASE_SECONDS = 5
MAX_LEASE_SECONDS = 600
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_CLAIMS = 64
MAX_EVENTS = 96
MAX_SUMMARIES = 8

CLAIM_STATES = frozenset({"active", "reconciliation_required", "released", "completed", "blocked", "cancelled"})
TERMINAL_STATES = frozenset({"completed", "cancelled"})
CLAIMANT_KINDS = frozenset({"process", "browser_tab", "queue_worker", "retry_worker", "recovery_worker", "unknown"})
RELEASE_CODES = frozenset({"authorization_required", "no_external_effect", "operator_pause", "operator_cancel"})

AUTHORITY_FLAGS = {
    **RECOVERY_AUTHORITY_FLAGS,
    "ownership_is_execution_authority": False,
    "ownership_is_provider_authority": False,
    "ownership_is_test_authority": False,
    "ownership_is_update_authority": False,
    "ownership_is_application_authority": False,
    "ownership_is_rollback_authority": False,
    "fence_token_is_authorization": False,
    "lease_expiry_proves_no_external_effect": False,
    "expired_owner_result_may_commit": False,
    "automatic_transfer_executes_work": False,
    "late_provider_result_may_expand_authority": False,
}

_OWNERSHIP_ID = re.compile(r"^ownership_[a-f0-9]{24}$")
_SAFE_CODE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,95}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _root(runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "ownership_concurrency"


def _path(ownership_id: str, runtime_root: str | Path | None) -> Path:
    oid = str(ownership_id or "")
    if not _OWNERSHIP_ID.fullmatch(oid):
        raise ValueError("invalid_ownership_concurrency_id")
    return _root(runtime_root) / "records" / f"{oid}.json"


def _lock_name(ownership_id: str) -> str:
    oid = str(ownership_id or "")
    if not _OWNERSHIP_ID.fullmatch(oid):
        raise ValueError("invalid_ownership_concurrency_id")
    return "devc_" + oid.split("_", 1)[1]


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_RECORD_BYTES:
        raise ValueError("ownership_concurrency_record_too_large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ownership_concurrency_record_invalid")
    return value


def _write(path: Path, row: Mapping[str, Any]) -> None:
    data = (json.dumps(dict(row), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("ownership_concurrency_record_too_large")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, suffix=".tmp") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            tmp = Path(handle.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def ownership_id_for_recovery(recovery_id: str, source_manifest_digest: str) -> str:
    seed = f"{recovery_id}:{source_manifest_digest}:v1273"
    return "ownership_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _owner_key(owner_id: str) -> str:
    text = str(owner_id or "")
    if not text or len(text) > 512:
        raise ValueError("invalid_ownership_owner_id")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _claim_key(operation_code: str, target_id: str) -> str:
    return _digest({"operation_code": operation_code, "target_id": target_id})


def _fence_token(ownership_id: str, claim_key: str, epoch: int, owner_key: str, acquired_at: float) -> str:
    return _digest({"ownership_id": ownership_id, "claim_key": claim_key, "epoch": int(epoch), "owner_key": owner_key, "acquired_at": float(acquired_at), "purpose": "v1273-fence"})


def _record_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k not in {"record_digest", "operation_status"}})


def _seal(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["record_digest"] = _record_digest(out)
    return out


def _claim_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k != "claim_digest"})


def _seal_claim(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["claim_digest"] = _claim_digest(out)
    return out


def _event_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k != "event_digest"})


def _seal_event(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["event_digest"] = _event_digest(out)
    return out


def _bounded_codes(values: Iterable[Any], limit: int = 12) -> list[str]:
    rows: list[str] = []
    for value in values or ():
        text = str(value or "").strip().lower()
        if not _SAFE_CODE.fullmatch(text):
            raise ValueError("invalid_ownership_concurrency_code")
        if text not in rows:
            rows.append(text)
    return rows[-limit:]


def _lease_seconds(value: int | float) -> int:
    seconds = int(value)
    if seconds < MIN_LEASE_SECONDS or seconds > MAX_LEASE_SECONDS:
        raise ValueError("ownership_lease_seconds_out_of_bounds")
    return seconds


def _summary(claims: list[Mapping[str, Any]], events: list[Mapping[str, Any]]) -> dict[str, Any]:
    latest: dict[str, Mapping[str, Any]] = {}
    for claim in claims:
        latest[str(claim.get("claim_key") or "")] = claim
    return {
        "summary_version": "1",
        "claim_count_total": len(claims),
        "event_count_total": len(events),
        "active_claim_count": sum(1 for x in latest.values() if x.get("state") == "active"),
        "reconciliation_required_count": sum(1 for x in latest.values() if x.get("state") == "reconciliation_required"),
        "completed_claim_count": sum(1 for x in latest.values() if x.get("state") == "completed"),
        "blocked_claim_count": sum(1 for x in latest.values() if x.get("state") == "blocked"),
        "content_free": True,
    }


def _save_event(row: Mapping[str, Any], *, event_code: str, reason_codes: Iterable[Any] = (), now: float | None = None) -> dict[str, Any]:
    clock = float(time.time() if now is None else now)
    updated = dict(row)
    events = list(updated.get("events") or [])
    events.append(_seal_event({
        "event_code": str(event_code),
        "reason_codes": _bounded_codes(reason_codes),
        "recorded_at": clock,
        "content_free": True,
        "provider_contacted": False,
        "tests_executed": False,
        "update_executed": False,
        "authorization_created": False,
    }))
    events = events[-MAX_EVENTS:]
    summaries = list(updated.get("bounded_summaries") or [])
    summaries.append(_summary(list(updated.get("claims") or []), events))
    updated["events"] = events
    updated["bounded_summaries"] = summaries[-MAX_SUMMARIES:]
    updated["updated_at"] = clock
    return _seal(updated)


def validate_ownership_concurrency(row: Mapping[str, Any]) -> dict[str, Any]:
    supplied = str(row.get("record_digest") or "")
    digest_ok = bool(supplied) and supplied == _record_digest(row)
    claims = list(row.get("claims") or [])
    events = list(row.get("events") or [])
    summaries = list(row.get("bounded_summaries") or [])
    claims_ok = len(claims) <= MAX_CLAIMS and all(
        x.get("claim_digest") == _claim_digest(x)
        and str(x.get("operation_code") or "") in OPERATION_CODES
        and str(x.get("state") or "") in CLAIM_STATES
        and bool(_DIGEST.fullmatch(str(x.get("claim_key") or "")))
        and bool(_DIGEST.fullmatch(str(x.get("owner_key") or "")))
        and bool(_DIGEST.fullmatch(str(x.get("fence_token_digest") or "")))
        and (not str(x.get("durable_lineage_digest") or "") or bool(_DIGEST.fullmatch(str(x.get("durable_lineage_digest") or ""))))
        and int(x.get("epoch") or 0) >= 1
        and str(x.get("claimant_kind") or "") in CLAIMANT_KINDS
        for x in claims
    )
    events_ok = len(events) <= MAX_EVENTS and all(x.get("event_digest") == _event_digest(x) for x in events)
    authority_ok = all(row.get(k) is v for k, v in AUTHORITY_FLAGS.items())
    semantic_ok = (
        bool(_OWNERSHIP_ID.fullmatch(str(row.get("ownership_id") or "")))
        and str(row.get("recovery_id") or "").startswith("recovery_")
        and str(row.get("session_id") or "").startswith("longwork_")
        and str(row.get("campaign_id") or "").startswith("selfalpha_")
        and len(summaries) <= MAX_SUMMARIES
        and row.get("content_free") is True
        and row.get("expired_claim_requires_reconciliation") is True
        and row.get("late_results_are_fenced") is True
        and row.get("active_source_modified") is False
    )
    ok = digest_ok and claims_ok and events_ok and authority_ok and semantic_ok
    return {
        "ok": ok,
        "status": "ownership_concurrency_valid" if ok else "ownership_concurrency_invalid",
        "digest_valid": digest_ok,
        "claims_valid": claims_ok,
        "events_valid": events_ok,
        "authority_contained": authority_ok,
        "semantic_valid": semantic_ok,
    }


def prepare_ownership_concurrency(recovery_id: str, *, runtime_root: str | Path | None, now: float | None = None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    recovery = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    if not recovery or not validate_restart_crash_recovery(recovery).get("ok"):
        raise ValueError("valid_v1272_restart_crash_recovery_required")
    ownership_id = ownership_id_for_recovery(recovery_id, str(recovery.get("source_manifest_digest") or ""))
    path = _path(ownership_id, runtime)
    clock = float(time.time() if now is None else now)
    with _proposal_lock(_lock_name(ownership_id), runtime):
        existing = _read(path)
        if existing:
            if not validate_ownership_concurrency(existing).get("ok"):
                raise ValueError("stored_ownership_concurrency_invalid")
            return {**existing, "operation_status": "restored"}
        row = _seal({
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "ownership_concurrency_prepared",
            "ownership_id": ownership_id,
            "recovery_id": recovery_id,
            "session_id": str(recovery.get("session_id") or ""),
            "campaign_id": str(recovery.get("campaign_id") or ""),
            "source_manifest_digest": str(recovery.get("source_manifest_digest") or ""),
            "recovery_record_digest": str(recovery.get("record_digest") or ""),
            "claims": [],
            "events": [],
            "bounded_summaries": [],
            "created_at": clock,
            "updated_at": clock,
            "content_free": True,
            "exactly_once_stage_claims": True,
            "expired_claim_requires_reconciliation": True,
            "late_results_are_fenced": True,
            "ownership_transfer_is_explicit": True,
            "underlying_exact_authorization_still_required": True,
            "active_source_modified": False,
            **AUTHORITY_FLAGS,
        })
        _write(path, row)
        return {**row, "operation_status": "created"}


def load_ownership_concurrency(ownership_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return _read(_path(ownership_id, runtime_root))


def _latest_claim(claims: list[Mapping[str, Any]], claim_key: str) -> dict[str, Any]:
    return next((dict(x) for x in reversed(claims) if str(x.get("claim_key") or "") == claim_key), {})


def acquire_operation_ownership(
    ownership_id: str,
    *,
    runtime_root: str | Path | None,
    operation_code: str,
    target_id: str,
    owner_id: str,
    claimant_kind: str = "process",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: float | None = None,
) -> dict[str, Any]:
    if operation_code not in OPERATION_CODES:
        raise ValueError("invalid_ownership_operation_code")
    target = str(target_id or "")
    if target and not _SAFE_CODE.fullmatch(target):
        raise ValueError("invalid_ownership_target_id")
    kind = str(claimant_kind or "unknown")
    if kind not in CLAIMANT_KINDS:
        raise ValueError("invalid_ownership_claimant_kind")
    seconds = _lease_seconds(lease_seconds)
    owner_key = _owner_key(owner_id)
    clock = float(time.time() if now is None else now)
    runtime = _runtime_root(runtime_root)
    key = _claim_key(operation_code, target)
    with _proposal_lock(_lock_name(ownership_id), runtime):
        row = load_ownership_concurrency(ownership_id, runtime_root=runtime)
        if not validate_ownership_concurrency(row).get("ok"):
            raise ValueError("valid_ownership_concurrency_required")
        claims = list(row.get("claims") or [])
        latest = _latest_claim(claims, key)
        if latest.get("state") == "completed":
            return {**latest, "operation_status": "already_completed", "execution_allowed": False, "duplicate_execution_suppressed": True}
        if latest.get("state") == "cancelled":
            return {**latest, "operation_status": "cancelled", "execution_allowed": False, "duplicate_execution_suppressed": True}
        if latest.get("state") in {"active", "reconciliation_required"}:
            expires = float(latest.get("lease_expires_at") or 0.0)
            same_owner = str(latest.get("owner_key") or "") == owner_key
            if clock < expires:
                if same_owner:
                    token = _fence_token(ownership_id, key, int(latest.get("epoch") or 0), owner_key, float(latest.get("acquired_at") or 0.0))
                    return {**latest, "operation_status": "ownership_already_held_by_claimant", "fence_token": token, "execution_allowed": False, "duplicate_execution_suppressed": True, "existing_claim_resume_requires_fence": True}
                return {**latest, "operation_status": "owned_elsewhere", "execution_allowed": False, "duplicate_execution_suppressed": True, "owner_key_requested": owner_key}
            # Expiry fences the former owner. The successor gets a new epoch but
            # may not execute until v1272 durable lineage is reconciled.
            epoch = int(latest.get("epoch") or 0) + 1
            state = "reconciliation_required"
            transfer_count = int(latest.get("transfer_count") or 0) + 1
            event_code = "expired_claim_transferred_pending_reconciliation"
        elif latest.get("state") == "blocked":
            epoch = int(latest.get("epoch") or 0) + 1
            state = "reconciliation_required"
            transfer_count = int(latest.get("transfer_count") or 0) + 1
            event_code = "blocked_claim_successor_pending_reconciliation"
        else:
            epoch = int(latest.get("epoch") or 0) + 1 if latest else 1
            state = "active"
            transfer_count = int(latest.get("transfer_count") or 0) if latest else 0
            event_code = "operation_ownership_acquired"
        token = _fence_token(ownership_id, key, epoch, owner_key, clock)
        claim = _seal_claim({
            "claim_key": key,
            "operation_code": operation_code,
            "target_id": target,
            "owner_key": owner_key,
            "claimant_kind": kind,
            "epoch": epoch,
            "state": state,
            "acquired_at": clock,
            "last_heartbeat_at": clock,
            "lease_seconds": seconds,
            "lease_expires_at": clock + seconds,
            "fence_token_digest": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            "transfer_count": transfer_count,
            "completion_code": "",
            "durable_lineage_digest": "",
            "result_digest": "",
            "content_free": True,
        })
        claims.append(claim)
        updated = dict(row)
        updated["claims"] = claims[-MAX_CLAIMS:]
        updated = _save_event(updated, event_code=event_code, reason_codes=[operation_code, state], now=clock)
        _write(_path(ownership_id, runtime), updated)
        return {
            **claim,
            "operation_status": "ownership_acquired" if state == "active" else "ownership_transferred_reconciliation_required",
            "fence_token": token,
            "execution_allowed": state == "active",
            "reconciliation_required": state == "reconciliation_required",
            "duplicate_execution_suppressed": state != "active",
        }


def _match_current_claim(row: Mapping[str, Any], *, operation_code: str, target_id: str, owner_id: str, epoch: int, fence_token: str) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
    key = _claim_key(operation_code, target_id)
    claims = [dict(x) for x in row.get("claims") or []]
    index = next((i for i in range(len(claims) - 1, -1, -1) if str(claims[i].get("claim_key") or "") == key), -1)
    if index < 0:
        raise ValueError("ownership_claim_not_found")
    claim = claims[index]
    token_digest = hashlib.sha256(str(fence_token or "").encode("utf-8")).hexdigest()
    if str(claim.get("owner_key") or "") != _owner_key(owner_id) or int(claim.get("epoch") or 0) != int(epoch) or str(claim.get("fence_token_digest") or "") != token_digest:
        raise ValueError("stale_or_invalid_ownership_fence")
    return claims, index, claim


def renew_operation_ownership(
    ownership_id: str, *, runtime_root: str | Path | None, operation_code: str, target_id: str,
    owner_id: str, epoch: int, fence_token: str, lease_seconds: int = DEFAULT_LEASE_SECONDS, now: float | None = None,
) -> dict[str, Any]:
    seconds = _lease_seconds(lease_seconds)
    clock = float(time.time() if now is None else now)
    runtime = _runtime_root(runtime_root)
    with _proposal_lock(_lock_name(ownership_id), runtime):
        row = load_ownership_concurrency(ownership_id, runtime_root=runtime)
        if not validate_ownership_concurrency(row).get("ok"):
            raise ValueError("valid_ownership_concurrency_required")
        claims, index, claim = _match_current_claim(row, operation_code=operation_code, target_id=target_id, owner_id=owner_id, epoch=epoch, fence_token=fence_token)
        if claim.get("state") != "active":
            return {**claim, "operation_status": "ownership_not_active", "renewed": False}
        if clock >= float(claim.get("lease_expires_at") or 0.0):
            return {**claim, "operation_status": "ownership_lease_expired", "renewed": False, "result_may_commit": False}
        claim.update({"last_heartbeat_at": clock, "lease_seconds": seconds, "lease_expires_at": clock + seconds})
        claim = _seal_claim(claim); claims[index] = claim
        updated = dict(row); updated["claims"] = claims[-MAX_CLAIMS:]
        updated = _save_event(updated, event_code="ownership_heartbeat_renewed", reason_codes=[operation_code], now=clock)
        _write(_path(ownership_id, runtime), updated)
        return {**claim, "operation_status": "ownership_renewed", "renewed": True}


def activate_operation_after_reconciliation(
    ownership_id: str, *, runtime_root: str | Path | None, operation_code: str, target_id: str,
    owner_id: str, epoch: int, fence_token: str, reconciliation_code: str, now: float | None = None,
) -> dict[str, Any]:
    if not _SAFE_CODE.fullmatch(str(reconciliation_code or "")):
        raise ValueError("invalid_ownership_reconciliation_code")
    clock = float(time.time() if now is None else now)
    runtime = _runtime_root(runtime_root)
    with _proposal_lock(_lock_name(ownership_id), runtime):
        row = load_ownership_concurrency(ownership_id, runtime_root=runtime)
        claims, index, claim = _match_current_claim(row, operation_code=operation_code, target_id=target_id, owner_id=owner_id, epoch=epoch, fence_token=fence_token)
        if claim.get("state") != "reconciliation_required":
            return {**claim, "operation_status": "reconciliation_activation_not_required", "execution_allowed": claim.get("state") == "active"}
        claim.update({"state": "active", "last_heartbeat_at": clock, "lease_expires_at": clock + int(claim.get("lease_seconds") or DEFAULT_LEASE_SECONDS)})
        claim = _seal_claim(claim); claims[index] = claim
        updated = dict(row); updated["claims"] = claims[-MAX_CLAIMS:]
        updated = _save_event(updated, event_code="transferred_claim_activated_after_reconciliation", reason_codes=[operation_code, reconciliation_code], now=clock)
        _write(_path(ownership_id, runtime), updated)
        return {**claim, "operation_status": "ownership_activated_after_reconciliation", "execution_allowed": True, "underlying_exact_authorization_still_required": True}


def release_operation_ownership(
    ownership_id: str, *, runtime_root: str | Path | None, operation_code: str, target_id: str,
    owner_id: str, epoch: int, fence_token: str, release_code: str, now: float | None = None,
) -> dict[str, Any]:
    if release_code not in RELEASE_CODES:
        raise ValueError("invalid_ownership_release_code")
    clock = float(time.time() if now is None else now); runtime = _runtime_root(runtime_root)
    with _proposal_lock(_lock_name(ownership_id), runtime):
        row = load_ownership_concurrency(ownership_id, runtime_root=runtime)
        claims, index, claim = _match_current_claim(row, operation_code=operation_code, target_id=target_id, owner_id=owner_id, epoch=epoch, fence_token=fence_token)
        if claim.get("state") in TERMINAL_STATES:
            return {**claim, "operation_status": "ownership_terminal", "released": False}
        claim.update({"state": "cancelled" if release_code == "operator_cancel" else "released", "lease_expires_at": clock, "completion_code": release_code})
        claim = _seal_claim(claim); claims[index] = claim
        updated = dict(row); updated["claims"] = claims[-MAX_CLAIMS:]
        updated = _save_event(updated, event_code="operation_ownership_released", reason_codes=[operation_code, release_code], now=clock)
        _write(_path(ownership_id, runtime), updated)
        return {**claim, "operation_status": "ownership_released", "released": True}


def fence_operation_result(
    ownership_id: str, *, runtime_root: str | Path | None, operation_code: str, target_id: str,
    owner_id: str, epoch: int, fence_token: str, now: float | None = None,
) -> dict[str, Any]:
    clock = float(time.time() if now is None else now); runtime = _runtime_root(runtime_root)
    with _proposal_lock(_lock_name(ownership_id), runtime):
        row = load_ownership_concurrency(ownership_id, runtime_root=runtime)
        if not validate_ownership_concurrency(row).get("ok"):
            return {"ok": False, "status": "ownership_concurrency_invalid", "result_may_commit": False, **AUTHORITY_FLAGS}
        try:
            _, _, claim = _match_current_claim(row, operation_code=operation_code, target_id=target_id, owner_id=owner_id, epoch=epoch, fence_token=fence_token)
        except ValueError:
            return {"ok": False, "status": "stale_owner_result_rejected", "result_may_commit": False, "late_result_fenced": True, **AUTHORITY_FLAGS}
        if claim.get("state") != "active":
            return {"ok": False, "status": "inactive_owner_result_rejected", "result_may_commit": False, "late_result_fenced": True, **AUTHORITY_FLAGS}
        if clock >= float(claim.get("lease_expires_at") or 0.0):
            return {"ok": False, "status": "expired_owner_result_rejected", "result_may_commit": False, "late_result_fenced": True, **AUTHORITY_FLAGS}
        return {"ok": True, "status": "current_owner_result_accepted", "result_may_commit": True, "late_result_fenced": False, "epoch": int(claim.get("epoch") or 0), **AUTHORITY_FLAGS}


def complete_operation_ownership(
    ownership_id: str, *, runtime_root: str | Path | None, operation_code: str, target_id: str,
    owner_id: str, epoch: int, fence_token: str, completion_code: str, durable_lineage_digest: str,
    result_digest: str = "", now: float | None = None, allow_expired_reconciled: bool = False,
) -> dict[str, Any]:
    if not _SAFE_CODE.fullmatch(str(completion_code or "")):
        raise ValueError("invalid_ownership_completion_code")
    if not _DIGEST.fullmatch(str(durable_lineage_digest or "")):
        raise ValueError("ownership_completion_requires_durable_lineage_digest")
    if result_digest and not _DIGEST.fullmatch(str(result_digest)):
        raise ValueError("invalid_ownership_result_digest")
    clock = float(time.time() if now is None else now); runtime = _runtime_root(runtime_root)
    with _proposal_lock(_lock_name(ownership_id), runtime):
        row = load_ownership_concurrency(ownership_id, runtime_root=runtime)
        claims, index, claim = _match_current_claim(row, operation_code=operation_code, target_id=target_id, owner_id=owner_id, epoch=epoch, fence_token=fence_token)
        if claim.get("state") == "completed":
            return {**claim, "operation_status": "already_completed", "completed": True}
        if claim.get("state") not in {"active", "reconciliation_required"}:
            return {**claim, "operation_status": "ownership_not_completable", "completed": False}
        if not allow_expired_reconciled and clock >= float(claim.get("lease_expires_at") or 0.0):
            return {**claim, "operation_status": "ownership_result_fenced", "completed": False, "late_result_fenced": True}
        claim.update({
            "state": "completed", "lease_expires_at": clock, "completion_code": str(completion_code),
            "durable_lineage_digest": str(durable_lineage_digest), "result_digest": str(result_digest or ""),
        })
        claim = _seal_claim(claim); claims[index] = claim
        updated = dict(row); updated["claims"] = claims[-MAX_CLAIMS:]
        updated = _save_event(updated, event_code="operation_ownership_completed", reason_codes=[operation_code, completion_code], now=clock)
        _write(_path(ownership_id, runtime), updated)
        return {**claim, "operation_status": "ownership_completed", "completed": True, "duplicate_execution_suppressed": True}


def block_operation_ownership(
    ownership_id: str, *, runtime_root: str | Path | None, operation_code: str, target_id: str,
    owner_id: str, epoch: int, fence_token: str, reason_code: str, now: float | None = None,
) -> dict[str, Any]:
    if not _SAFE_CODE.fullmatch(str(reason_code or "")):
        raise ValueError("invalid_ownership_block_reason")
    clock = float(time.time() if now is None else now); runtime = _runtime_root(runtime_root)
    with _proposal_lock(_lock_name(ownership_id), runtime):
        row = load_ownership_concurrency(ownership_id, runtime_root=runtime)
        claims, index, claim = _match_current_claim(row, operation_code=operation_code, target_id=target_id, owner_id=owner_id, epoch=epoch, fence_token=fence_token)
        if claim.get("state") == "completed":
            return {**claim, "operation_status": "already_completed", "blocked": False}
        claim.update({"state": "blocked", "lease_expires_at": clock, "completion_code": str(reason_code)})
        claim = _seal_claim(claim); claims[index] = claim
        updated = dict(row); updated["claims"] = claims[-MAX_CLAIMS:]
        updated = _save_event(updated, event_code="operation_ownership_blocked", reason_codes=[operation_code, reason_code], now=clock)
        _write(_path(ownership_id, runtime), updated)
        return {**claim, "operation_status": "ownership_blocked", "blocked": True}


def public_ownership_concurrency(row: Mapping[str, Any], *, now: float | None = None) -> dict[str, Any]:
    clock = float(time.time() if now is None else now)
    claims = list(row.get("claims") or [])
    latest: dict[str, Mapping[str, Any]] = {}
    for claim in claims:
        latest[str(claim.get("claim_key") or "")] = claim
    active = [x for x in latest.values() if x.get("state") == "active" and clock < float(x.get("lease_expires_at") or 0.0)]
    expired = [x for x in latest.values() if x.get("state") in {"active", "reconciliation_required"} and clock >= float(x.get("lease_expires_at") or 0.0)]
    return {
        "ok": validate_ownership_concurrency(row).get("ok") is True,
        "status": "ownership_concurrency_operator_status",
        "ownership_id": row.get("ownership_id"),
        "recovery_id": row.get("recovery_id"),
        "claim_count": len(claims),
        "event_count": len(row.get("events") or []),
        "bounded_summary_count": len(row.get("bounded_summaries") or []),
        "active_claim_count": len(active),
        "expired_or_unreconciled_claim_count": len(expired),
        "completed_claim_count": sum(1 for x in latest.values() if x.get("state") == "completed"),
        "blocked_claim_count": sum(1 for x in latest.values() if x.get("state") == "blocked"),
        "content_free": True,
        "owner_ids_persisted": False,
        "late_results_are_fenced": True,
        "expired_claim_requires_reconciliation": True,
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }


__all__ = [
    "CONTRACT_VERSION", "AUTHORITY_FLAGS", "DEFAULT_LEASE_SECONDS", "MAX_CLAIMS", "MAX_EVENTS", "MAX_SUMMARIES",
    "prepare_ownership_concurrency", "load_ownership_concurrency", "validate_ownership_concurrency", "public_ownership_concurrency",
    "acquire_operation_ownership", "renew_operation_ownership", "activate_operation_after_reconciliation",
    "release_operation_ownership", "fence_operation_result", "complete_operation_ownership", "block_operation_ownership",
    "ownership_id_for_recovery",
]
