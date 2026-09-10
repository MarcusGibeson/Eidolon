from __future__ import annotations

"""v1272.0-v1272.2 restart/crash-recovery foundations.

This module adds a content-minimized write-ahead recovery journal around the
v1271 long-running session that already wraps the v1270 supervised
self-development campaign.  It records *intent to enter* an external stage
before the stage begins and records completion only after durable lower-stage
lineage exists.  Recovery metadata never grants provider, test, update,
application, rollback, installation, release, or autonomous authority.
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
from self_development_alpha_foundations import (
    _runtime_root,
    load_self_development_alpha_campaign,
    validate_self_development_alpha_campaign,
)
from long_running_work_sessions_foundations import (
    AUTHORITY_FLAGS as LONG_SESSION_AUTHORITY_FLAGS,
    load_long_running_work_session,
    validate_long_running_work_session,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1272.2"
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_OPERATION_JOURNAL = 64
MAX_RECOVERY_RECEIPTS = 48
MAX_RECOVERY_SUMMARIES = 8
MAX_REASON_CODES = 12

RECOVERY_STATES = frozenset({"healthy", "interrupted", "recovery_required", "reconciled", "blocked", "cancelled"})
OPERATION_STATES = frozenset({"started", "authorization_required", "completed", "blocked", "ambiguous", "cancelled"})
OPERATION_CODES = frozenset({"candidate_stage", "verification_stage", "governed_update"})
INTERRUPTION_CODES = frozenset({
    "process_crash", "process_restart", "dashboard_closed", "machine_interruption",
    "provider_outage", "provider_return", "operator_interruption", "unknown",
})

AUTHORITY_FLAGS = {
    **LONG_SESSION_AUTHORITY_FLAGS,
    "recovery_is_execution_authority": False,
    "recovery_is_provider_authority": False,
    "recovery_is_test_authority": False,
    "recovery_is_update_authority": False,
    "recovery_is_application_authority": False,
    "recovery_is_rollback_authority": False,
    "old_authorization_reusable_after_restart": False,
    "automatic_provider_retry_after_restart": False,
    "automatic_test_retry_after_restart": False,
    "automatic_update_retry_after_restart": False,
    "automatic_resume_after_restart": False,
}

_RECOVERY_ID = re.compile(r"^recovery_[a-f0-9]{24}$")
_SAFE_CODE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,95}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _root(runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "restart_crash_recovery"


def _path(recovery_id: str, runtime_root: str | Path | None) -> Path:
    rid = str(recovery_id or "")
    if not _RECOVERY_ID.fullmatch(rid):
        raise ValueError("invalid_restart_crash_recovery_id")
    return _root(runtime_root) / "records" / f"{rid}.json"


def _quarantine_root(runtime_root: str | Path | None) -> Path:
    return _root(runtime_root) / "quarantine"


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_RECORD_BYTES:
        raise ValueError("restart_crash_recovery_record_too_large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("restart_crash_recovery_record_invalid")
    return value


def _write(path: Path, row: Mapping[str, Any]) -> None:
    data = (json.dumps(dict(row), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("restart_crash_recovery_record_too_large")
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


def _record_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k not in {"record_digest", "operation_status"}})


def _seal(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["record_digest"] = _record_digest(out)
    return out


def _entry_digest(entry: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in entry.items() if k != "entry_digest"})


def _seal_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    out["entry_digest"] = _entry_digest(out)
    return out


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in receipt.items() if k != "receipt_digest"})


def _seal_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(receipt)
    out["receipt_digest"] = _receipt_digest(out)
    return out


def _bounded_codes(values: Iterable[Any], limit: int = MAX_REASON_CODES) -> list[str]:
    rows: list[str] = []
    for value in values or ():
        text = str(value or "").strip().lower()
        if not _SAFE_CODE.fullmatch(text):
            raise ValueError("invalid_restart_crash_recovery_code")
        if text not in rows:
            rows.append(text)
    return rows[-limit:]


def _bounded_summary(receipts: list[Mapping[str, Any]], journal: list[Mapping[str, Any]], state: str) -> dict[str, Any]:
    recent = receipts[-8:]
    return {
        "summary_version": "1",
        "state": state,
        "journal_count_total": len(journal),
        "receipt_count_total": len(receipts),
        "recent_receipt_digests": [str(x.get("receipt_digest") or "") for x in recent],
        "completed_operation_count": sum(1 for x in journal if x.get("state") == "completed"),
        "ambiguous_operation_count": sum(1 for x in journal if x.get("state") == "ambiguous"),
        "content_free": True,
    }


def _lock_name(recovery_id: str) -> str:
    return "devc_" + str(recovery_id).split("_", 1)[1]


def recovery_id_for_session(session_id: str, campaign_id: str, source_manifest_digest: str) -> str:
    seed = f"{session_id}:{campaign_id}:{source_manifest_digest}"
    return "recovery_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def validate_restart_crash_recovery(row: Mapping[str, Any]) -> dict[str, Any]:
    supplied = str(row.get("record_digest") or "")
    digest_ok = bool(supplied) and supplied == _record_digest(row)
    journal = list(row.get("operation_journal") or [])
    receipts = list(row.get("recovery_receipts") or [])
    summaries = list(row.get("bounded_recovery_summaries") or [])
    journal_ok = len(journal) <= MAX_OPERATION_JOURNAL and all(
        x.get("entry_digest") == _entry_digest(x)
        and x.get("operation_code") in OPERATION_CODES
        and x.get("state") in OPERATION_STATES
        and (not str(x.get("target_id") or "") or bool(_SAFE_CODE.fullmatch(str(x.get("target_id") or ""))))
        and (not str(x.get("outcome_code") or "") or bool(_SAFE_CODE.fullmatch(str(x.get("outcome_code") or ""))))
        and (
            not str(x.get("durable_lineage_digest") or "")
            or bool(re.fullmatch(r"[a-f0-9]{64}", str(x.get("durable_lineage_digest") or "")))
        )
        for x in journal
    )
    receipts_ok = len(receipts) <= MAX_RECOVERY_RECEIPTS and all(
        x.get("receipt_digest") == _receipt_digest(x) for x in receipts
    )
    authority_ok = all(row.get(k) is v for k, v in AUTHORITY_FLAGS.items())
    semantic_ok = (
        bool(_RECOVERY_ID.fullmatch(str(row.get("recovery_id") or "")))
        and str(row.get("session_id") or "").startswith("longwork_")
        and str(row.get("campaign_id") or "").startswith("selfalpha_")
        and str(row.get("state") or "") in RECOVERY_STATES
        and len(summaries) <= MAX_RECOVERY_SUMMARIES
        and row.get("content_free") is True
        and row.get("active_source_modified") is False
        and row.get("write_ahead_journal_required") is True
        and row.get("completion_requires_durable_lineage") is True
    )
    ok = digest_ok and journal_ok and receipts_ok and authority_ok and semantic_ok
    return {
        "ok": ok,
        "status": "restart_crash_recovery_valid" if ok else "restart_crash_recovery_invalid",
        "digest_valid": digest_ok,
        "journal_valid": journal_ok,
        "receipts_valid": receipts_ok,
        "authority_contained": authority_ok,
        "semantic_valid": semantic_ok,
    }


def prepare_restart_crash_recovery(
    session_id: str,
    *,
    runtime_root: str | Path | None,
    now: float | None = None,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    session = load_long_running_work_session(session_id, runtime_root=runtime)
    if not session or not validate_long_running_work_session(session).get("ok"):
        raise ValueError("valid_v1271_long_running_work_session_required")
    campaign_id = str(session.get("campaign_id") or "")
    alpha = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
    if not alpha or not validate_self_development_alpha_campaign(alpha).get("ok"):
        raise ValueError("valid_v1270_self_development_campaign_required")
    recovery_id = recovery_id_for_session(session_id, campaign_id, str(alpha.get("source_manifest_digest") or ""))
    path = _path(recovery_id, runtime)
    clock = float(time.time() if now is None else now)
    with _proposal_lock(_lock_name(recovery_id), runtime):
        existing = _read(path)
        if existing:
            if not validate_restart_crash_recovery(existing).get("ok"):
                raise ValueError("stored_restart_crash_recovery_invalid")
            return {**existing, "operation_status": "restored"}
        row = _seal({
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "restart_crash_recovery_prepared",
            "recovery_id": recovery_id,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "source_manifest_digest": str(alpha.get("source_manifest_digest") or ""),
            "session_record_digest": str(session.get("record_digest") or ""),
            "campaign_record_digest": str(alpha.get("record_digest") or ""),
            "state": "healthy",
            "restart_generation": 0,
            "last_interruption_code": "",
            "last_interruption_at": 0.0,
            "provider_state": "unknown",
            "operation_journal": [],
            "recovery_receipts": [],
            "bounded_recovery_summaries": [],
            "created_at": clock,
            "updated_at": clock,
            "content_free": True,
            "write_ahead_journal_required": True,
            "completion_requires_durable_lineage": True,
            "ambiguous_external_effects_fail_closed": True,
            "restart_never_creates_authorization": True,
            "active_source_modified": False,
            **AUTHORITY_FLAGS,
        })
        _write(path, row)
        return {**row, "operation_status": "created"}


def load_restart_crash_recovery(recovery_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return _read(_path(recovery_id, runtime_root))


def _save_with_receipt(
    row: Mapping[str, Any],
    *,
    runtime_root: str | Path | None,
    receipt_code: str,
    reason_codes: Iterable[Any] = (),
    state: str | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    clock = float(time.time() if now is None else now)
    updated = dict(row)
    receipts = list(updated.get("recovery_receipts") or [])
    receipt = _seal_receipt({
        "receipt_code": str(receipt_code),
        "restart_generation": int(updated.get("restart_generation") or 0),
        "reason_codes": _bounded_codes(reason_codes),
        "recorded_at": clock,
        "content_free": True,
        "provider_contacted": False,
        "tests_executed": False,
        "update_executed": False,
    })
    receipts.append(receipt)
    receipts = receipts[-MAX_RECOVERY_RECEIPTS:]
    summaries = list(updated.get("bounded_recovery_summaries") or [])
    summaries.append(_bounded_summary(receipts, list(updated.get("operation_journal") or []), state or str(updated.get("state") or "healthy")))
    updated.update({
        "state": state or updated.get("state"),
        "recovery_receipts": receipts,
        "bounded_recovery_summaries": summaries[-MAX_RECOVERY_SUMMARIES:],
        "updated_at": clock,
    })
    return _seal(updated)


def begin_recovery_operation(
    recovery_id: str,
    *,
    runtime_root: str | Path | None,
    operation_code: str,
    target_id: str = "",
    now: float | None = None,
) -> dict[str, Any]:
    if operation_code not in OPERATION_CODES:
        raise ValueError("invalid_restart_crash_recovery_operation_code")
    target = str(target_id or "")
    if target and not _SAFE_CODE.fullmatch(target):
        raise ValueError("invalid_restart_crash_recovery_target_id")
    runtime = _runtime_root(runtime_root)
    clock = float(time.time() if now is None else now)
    with _proposal_lock(_lock_name(recovery_id), runtime):
        row = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
        if not validate_restart_crash_recovery(row).get("ok"):
            raise ValueError("valid_restart_crash_recovery_required")
        journal = list(row.get("operation_journal") or [])
        same = [x for x in journal if x.get("operation_code") == operation_code and x.get("target_id", "") == target]
        terminal = next((x for x in reversed(same) if x.get("state") == "completed"), None)
        if terminal:
            return {**terminal, "operation_status": "already_completed", "duplicate_external_activity_allowed": False}
        active = next((x for x in reversed(same) if x.get("state") in {"started", "ambiguous"}), None)
        if active:
            return {**active, "operation_status": "existing_incomplete", "duplicate_external_activity_allowed": False}
        generation = 1 + max((int(x.get("generation") or 0) for x in same), default=0)
        entry = _seal_entry({
            "operation_code": operation_code,
            "target_id": target,
            "generation": generation,
            "restart_generation": int(row.get("restart_generation") or 0),
            "state": "started",
            "started_at": clock,
            "finished_at": 0.0,
            "outcome_code": "",
            "durable_lineage_digest": "",
            "provider_contacted_by_recovery": False,
            "tests_executed_by_recovery": False,
            "update_executed_by_recovery": False,
            "authorization_created_by_recovery": False,
            "content_free": True,
        })
        journal.append(entry)
        updated = dict(row)
        updated["operation_journal"] = journal[-MAX_OPERATION_JOURNAL:]
        updated = _save_with_receipt(
            updated,
            runtime_root=runtime,
            receipt_code="operation_write_ahead_started",
            reason_codes=[operation_code],
            state=str(updated.get("state") or "healthy"),
            now=clock,
        )
        _write(_path(recovery_id, runtime), updated)
        return {**entry, "operation_status": "started", "duplicate_external_activity_allowed": False}


def finish_recovery_operation(
    recovery_id: str,
    *,
    runtime_root: str | Path | None,
    operation_code: str,
    generation: int,
    state: str,
    outcome_code: str,
    durable_lineage_digest: str = "",
    reason_codes: Iterable[Any] = (),
    now: float | None = None,
) -> dict[str, Any]:
    if operation_code not in OPERATION_CODES or state not in OPERATION_STATES:
        raise ValueError("invalid_restart_crash_recovery_operation_outcome")
    if state == "started":
        raise ValueError("finish_requires_non_started_state")
    if outcome_code and not _SAFE_CODE.fullmatch(str(outcome_code)):
        raise ValueError("invalid_restart_crash_recovery_outcome_code")
    lineage_digest = str(durable_lineage_digest or "")
    if lineage_digest and not re.fullmatch(r"[a-f0-9]{64}", lineage_digest):
        raise ValueError("invalid_restart_crash_recovery_durable_lineage_digest")
    runtime = _runtime_root(runtime_root)
    clock = float(time.time() if now is None else now)
    with _proposal_lock(_lock_name(recovery_id), runtime):
        row = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
        if not validate_restart_crash_recovery(row).get("ok"):
            raise ValueError("valid_restart_crash_recovery_required")
        journal = list(row.get("operation_journal") or [])
        index = next((i for i in range(len(journal) - 1, -1, -1) if journal[i].get("operation_code") == operation_code and int(journal[i].get("generation") or 0) == int(generation)), -1)
        if index < 0:
            raise ValueError("restart_crash_recovery_operation_not_found")
        prior = journal[index]
        if prior.get("state") == "completed":
            return {**prior, "operation_status": "already_completed"}
        entry = dict(prior)
        entry.update({
            "state": state,
            "finished_at": clock,
            "outcome_code": str(outcome_code or ""),
            "durable_lineage_digest": lineage_digest,
        })
        entry = _seal_entry(entry)
        journal[index] = entry
        updated = dict(row)
        updated["operation_journal"] = journal[-MAX_OPERATION_JOURNAL:]
        next_state = "blocked" if state in {"blocked", "ambiguous"} else str(updated.get("state") or "healthy")
        updated = _save_with_receipt(
            updated,
            runtime_root=runtime,
            receipt_code="operation_recovery_outcome_recorded",
            reason_codes=[operation_code, str(outcome_code or state), *_bounded_codes(reason_codes)],
            state=next_state,
            now=clock,
        )
        _write(_path(recovery_id, runtime), updated)
        return {**entry, "operation_status": "recorded"}


def note_recovery_interruption(
    recovery_id: str,
    *,
    runtime_root: str | Path | None,
    interruption_code: str,
    now: float | None = None,
) -> dict[str, Any]:
    code = str(interruption_code or "unknown")
    if code not in INTERRUPTION_CODES:
        raise ValueError("invalid_restart_crash_recovery_interruption_code")
    runtime = _runtime_root(runtime_root)
    clock = float(time.time() if now is None else now)
    with _proposal_lock(_lock_name(recovery_id), runtime):
        row = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
        if not validate_restart_crash_recovery(row).get("ok"):
            raise ValueError("valid_restart_crash_recovery_required")
        updated = dict(row)
        if code in {"process_crash", "process_restart", "machine_interruption"}:
            updated["restart_generation"] = int(updated.get("restart_generation") or 0) + 1
        if code == "provider_outage":
            updated["provider_state"] = "unavailable"
        elif code == "provider_return":
            updated["provider_state"] = "available"
        updated.update({
            "state": "recovery_required" if code != "provider_return" else "interrupted",
            "last_interruption_code": code,
            "last_interruption_at": clock,
        })
        updated = _save_with_receipt(
            updated,
            runtime_root=runtime,
            receipt_code="interruption_recorded",
            reason_codes=[code],
            state=str(updated["state"]),
            now=clock,
        )
        _write(_path(recovery_id, runtime), updated)
        return {**public_restart_crash_recovery(updated), "operation_status": "interruption_recorded"}


def public_restart_crash_recovery(row: Mapping[str, Any]) -> dict[str, Any]:
    journal = list(row.get("operation_journal") or [])
    public = {
        "ok": row.get("ok") is True,
        "status": row.get("status", ""),
        "recovery_id": row.get("recovery_id", ""),
        "session_id": row.get("session_id", ""),
        "campaign_id": row.get("campaign_id", ""),
        "state": row.get("state", ""),
        "restart_generation": int(row.get("restart_generation") or 0),
        "last_interruption_code": row.get("last_interruption_code", ""),
        "provider_state": row.get("provider_state", "unknown"),
        "operation_count": len(journal),
        "completed_operation_codes": [str(x.get("operation_code") or "") for x in journal if x.get("state") == "completed"],
        "incomplete_operation_codes": [str(x.get("operation_code") or "") for x in journal if x.get("state") in {"started", "ambiguous"}],
        "recovery_receipt_count": len(row.get("recovery_receipts") or []),
        "bounded_summary_count": len(row.get("bounded_recovery_summaries") or []),
        "content_free": True,
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }
    public["public_digest"] = _digest(public)
    return public


__all__ = [
    "SCHEMA_VERSION", "CONTRACT_VERSION", "MAX_OPERATION_JOURNAL", "MAX_RECOVERY_RECEIPTS",
    "MAX_RECOVERY_SUMMARIES", "MAX_REASON_CODES", "RECOVERY_STATES", "OPERATION_STATES", "OPERATION_CODES",
    "INTERRUPTION_CODES", "AUTHORITY_FLAGS", "prepare_restart_crash_recovery", "load_restart_crash_recovery",
    "validate_restart_crash_recovery", "begin_recovery_operation", "finish_recovery_operation",
    "note_recovery_interruption", "public_restart_crash_recovery", "recovery_id_for_session",
    "_digest", "_record_digest", "_seal", "_path", "_write", "_read", "_quarantine_root",
]
