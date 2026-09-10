from __future__ import annotations

"""Non-fatal capture finalization, sanitation, and visible failure receipts."""

import time
from pathlib import Path
from typing import Any, Mapping

from model_training.training_record import _atomic_json, _digest, _training_root
from model_training.training_sanitizer import sanitize_stored_training_record

CONTRACT_VERSION = "v2503.4.32"


def persist_capture_failure(
    *, runtime_root: str | Path | None, capability: str, status: str, failure_class: str = ""
) -> dict[str, Any]:
    created = time.time_ns()
    payload = {
        "contract_version": CONTRACT_VERSION,
        "status": str(status or "training_capture_failed")[:120],
        "capability": str(capability or "other")[:80],
        "failure_class": str(failure_class or "")[:80],
        "created_at_ns": created,
        "underlying_task_preserved": True,
        "runtime_only": True,
        "approved_for_training": False,
        "model_training_authorized": False,
        "model_promotion_authorized": False,
    }
    payload["failure_receipt_digest"] = _digest(payload)
    path = _training_root(runtime_root) / "capture_failures" / f"capture-failure-{created}-{payload['failure_receipt_digest'][:12]}.json"
    _atomic_json(path, payload)
    return {"ok": False, **payload, "runtime_path": str(path)}


def finalize_capture_result(
    result: Mapping[str, Any], *, runtime_root: str | Path | None, capability: str, auto_sanitize: bool
) -> dict[str, Any]:
    row = dict(result or {})
    if row.get("ok") is not True:
        return persist_capture_failure(
            runtime_root=runtime_root,
            capability=capability,
            status=str(row.get("status") or "training_capture_failed"),
            failure_class=str(row.get("failure_class") or ""),
        )
    record = dict(row.get("record") or {})
    record_id = str(record.get("record_id") or "")
    row["auto_sanitize_enabled"] = bool(auto_sanitize)
    row["approved_for_training"] = False
    if not auto_sanitize or not record_id:
        return row
    try:
        sanitized = sanitize_stored_training_record(record_id, runtime_root=runtime_root)
    except Exception as exc:
        failure = persist_capture_failure(
            runtime_root=runtime_root,
            capability=capability,
            status="training_auto_sanitize_failed",
            failure_class=type(exc).__name__,
        )
        return {**row, "ok": True, "sanitization_ok": False, "capture_failure": failure}
    row["sanitization_ok"] = sanitized.get("ok") is True
    row["sanitization_status"] = str(sanitized.get("status") or "")
    if sanitized.get("ok") is not True:
        row["capture_failure"] = persist_capture_failure(
            runtime_root=runtime_root,
            capability=capability,
            status=str(sanitized.get("status") or "training_auto_sanitize_failed"),
        )
    return row

