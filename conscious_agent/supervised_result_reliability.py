from __future__ import annotations

"""Reliability and recovery for bounded supervised-action terminal results.

This control surface repairs only stale, explicitly persisted execution attempts.
It never invokes an executor, grants authority, reads conversation content, or
reconstructs raw arguments/output.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1178.8"
MAX_RECOVERY_RECEIPT_BYTES = 4096
DEFAULT_STALE_AFTER_SECONDS = 300.0
_TERMINAL_STATES = {
    "execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out"
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("records"), list):
            return value
    except Exception:
        pass
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "records": []}


def _save(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def recover_stale_execution_attempt(
    path: Path | str,
    *,
    proposal_id: str,
    attempt_digest: str,
    now: float | None = None,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
) -> dict[str, Any]:
    """Terminally fail one exact stale in-progress attempt without re-execution."""
    now = float(time.time() if now is None else now)
    p = Path(path)
    state = _load(p)
    pid = str(proposal_id or "")[:80]
    attempt = _hex64(attempt_digest)
    row = next((r for r in reversed(state.get("records", [])) if r.get("proposal_id") == pid), None)
    base = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": pid,
        "ok": False,
        "recovered": False,
        "terminal": False,
        "executor_invoked": False,
        "execution_performed": False,
        "authority_granted": False,
        "source_modified": False,
        "content_free": True,
        "raw_output_included": False,
        "raw_arguments_included": False,
    }
    if not row:
        return {**base, "state": "missing", "reason": "proposal_not_found"}
    if row.get("state") in _TERMINAL_STATES or row.get("execution_terminal") is True:
        return {**base, "state": "terminal", "terminal": True, "reason": "terminal_result_already_recorded"}
    started_at = float(row.get("execution_started_at") or 0.0)
    exact = bool(
        row.get("state") == "execution_in_progress"
        and row.get("execution_in_progress") is True
        and attempt
        and attempt == row.get("execution_attempt_digest")
    )
    if not exact:
        return {**base, "state": "blocked", "reason": "exact_in_progress_attempt_required"}
    if started_at <= 0 or now - started_at < max(1.0, float(stale_after_seconds)):
        return {**base, "state": "not_stale", "reason": "attempt_still_within_recovery_window"}

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": pid,
        "proposal_digest": _hex64(row.get("proposal_digest")),
        "capability_id": str(row.get("capability_id") or "")[:80],
        "authorization_digest": _hex64(row.get("authorization_digest")),
        "execution_admission_digest": _hex64(row.get("execution_admission_digest")),
        "operation_digest": _hex64(row.get("operation_digest")),
        "execution_attempt_digest": attempt,
        "state": "execution_failed",
        "ok": False,
        "executed": False,
        "terminal": True,
        "elapsed_ms": max(0, min(int((now - started_at) * 1000), 120000)),
        "error_kind": "interrupted_before_terminal_result",
        "recorded_at": now,
        "content_free": True,
        "raw_output_included": False,
        "raw_arguments_included": False,
        "authority_granted": False,
        "source_modified": False,
        "replay_safe": True,
        "recovered_without_execution": True,
    }
    receipt["terminal_result_digest"] = _digest(receipt)
    receipt["supervised_result_digest"] = _digest({"attempt": attempt, "state": receipt["state"]})
    receipt["outcome_digest"] = _digest({"error_kind": receipt["error_kind"], "executed": False})
    if len(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()) > MAX_RECOVERY_RECEIPT_BYTES:
        raise ValueError("Recovery receipt exceeded bounded size")

    row["state"] = "execution_failed"
    row["execution_in_progress"] = False
    row["execution_terminal"] = True
    row["execution_performed"] = False
    row["execution_result_digest"] = receipt["terminal_result_digest"]
    row["supervised_result_digest"] = receipt["supervised_result_digest"]
    row["outcome_digest"] = receipt["outcome_digest"]
    row["execution_error_kind"] = receipt["error_kind"]
    row["execution_elapsed_ms"] = receipt["elapsed_ms"]
    row["execution_recovered"] = True
    row["updated_at"] = now
    state["contract_version"] = CONTRACT_VERSION
    state["revision"] = int(state.get("revision", 0)) + 1
    _save(p, state)
    return {**base, **receipt, "ok": True, "recovered": True}


def inspect_result_reliability(path: Path | str, *, now: float | None = None) -> dict[str, Any]:
    """Return bounded content-free reliability counts without mutating state."""
    now = float(time.time() if now is None else now)
    state = _load(Path(path))
    counts = {"in_progress": 0, "stale_in_progress": 0, "terminal": 0, "malformed_terminal": 0}
    for row in state.get("records", []):
        status = str(row.get("state") or "")
        if status == "execution_in_progress":
            counts["in_progress"] += 1
            started = float(row.get("execution_started_at") or 0.0)
            if started > 0 and now - started >= DEFAULT_STALE_AFTER_SECONDS:
                counts["stale_in_progress"] += 1
        if status in _TERMINAL_STATES:
            counts["terminal"] += 1
            if not _hex64(row.get("execution_result_digest")):
                counts["malformed_terminal"] += 1
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "record_count": len(state.get("records", [])),
        **counts,
        "executor_invoked": False,
        "authority_granted": False,
        "raw_output_exposed": False,
        "raw_arguments_exposed": False,
        "content_free": True,
    }
    result["inspection_digest"] = _digest(result)
    return result
