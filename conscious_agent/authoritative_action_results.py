from __future__ import annotations

"""Authoritative terminal results for exactly admitted supervised actions.

This module is a separate governed control surface. Conversation cannot invoke it.
It consumes one exact persisted execution admission, calls the existing bounded
supervised executor, and persists only content-free terminal evidence.
"""

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from supervised_action_execution import execute_supervised_action

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1178.8"
MAX_TERMINAL_RESULT_BYTES = 4096
TERMINAL_EXECUTION_STATES = frozenset({
    "execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out"
})


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


def _terminal_state(result_state: str) -> str:
    return {
        "succeeded": "execution_succeeded",
        "cancelled": "execution_cancelled",
        "timed_out": "execution_timed_out",
    }.get(result_state, "execution_failed")


def execute_admitted_action(
    path: Path | str,
    *,
    proposal_id: str,
    proposal_digest: str,
    authorization_digest: str,
    execution_admission_digest: str,
    operation_digest: str,
    admission_receipt_digest: str,
    executor: Callable[[], Mapping[str, Any]],
    cancel_event: threading.Event | None = None,
    timeout_seconds: float = 10.0,
    now: float | None = None,
) -> dict[str, Any]:
    """Execute one exact admitted action and persist a content-free terminal result."""
    now = float(time.time() if now is None else now)
    p = Path(path)
    state = _load(p)
    pid = str(proposal_id or "")[:80]
    pd = _hex64(proposal_digest)
    auth = _hex64(authorization_digest)
    admission = _hex64(execution_admission_digest)
    operation = _hex64(operation_digest)
    admission_receipt = _hex64(admission_receipt_digest)
    row = next((r for r in reversed(state["records"]) if r.get("proposal_id") == pid), None)
    base = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "ok": False,
        "proposal_id": pid,
        "executed": False,
        "terminal": False,
        "executor_invoked": False,
        "raw_output_included": False,
        "raw_arguments_included": False,
        "content_free": True,
        "authority_granted": False,
        "source_modified": False,
        "conversation_can_execute": False,
    }
    if not row:
        return {**base, "state": "missing", "reason": "proposal_not_found"}
    if row.get("state") in TERMINAL_EXECUTION_STATES or row.get("execution_terminal") is True:
        return {**base, "state": "replayed", "terminal": True, "reason": "terminal_result_already_recorded"}
    exact = bool(
        row.get("state") == "execution_admitted"
        and row.get("execution_admitted") is True
        and pd == row.get("proposal_digest")
        and auth == row.get("authorization_digest")
        and admission == row.get("execution_admission_digest")
        and operation == row.get("operation_digest")
        and admission_receipt
        and callable(executor)
    )
    if not exact:
        return {**base, "state": "blocked", "reason": "exact_execution_admission_required"}

    attempt = {
        "proposal_id": pid,
        "proposal_digest": pd,
        "authorization_digest": auth,
        "execution_admission_digest": admission,
        "operation_digest": operation,
        "admission_receipt_digest": admission_receipt,
        "started_at": now,
    }
    attempt_digest = _digest(attempt)
    row["state"] = "execution_in_progress"
    row["execution_in_progress"] = True
    row["execution_started_at"] = now
    row["execution_attempt_digest"] = attempt_digest
    row["updated_at"] = now
    state["contract_version"] = CONTRACT_VERSION
    state["revision"] = int(state.get("revision", 0)) + 1
    _save(p, state)

    projection = {
        "capability_id": row.get("capability_id"),
        "admitted": True,
        "operation_digest": operation,
        "projection_digest": admission,
    }
    result = execute_supervised_action(
        projection,
        executor=executor,
        cancel_event=cancel_event,
        timeout_seconds=timeout_seconds,
    )
    terminal_state = _terminal_state(str(result.get("state") or "failed"))
    terminal = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": pid,
        "proposal_digest": pd,
        "capability_id": str(row.get("capability_id") or "")[:80],
        "authorization_digest": auth,
        "execution_admission_digest": admission,
        "admission_receipt_digest": admission_receipt,
        "operation_digest": operation,
        "execution_attempt_digest": attempt_digest,
        "supervised_result_digest": _hex64(result.get("result_digest")),
        "outcome_digest": _hex64(result.get("outcome_digest")),
        "state": terminal_state,
        "ok": bool(result.get("ok")),
        "executed": bool(result.get("executed")),
        "terminal": True,
        "elapsed_ms": max(0, min(int(result.get("elapsed_ms") or 0), 120000)),
        "error_kind": str(result.get("error_kind") or "")[:80],
        "recorded_at": now,
        "content_free": True,
        "raw_output_included": False,
        "raw_arguments_included": False,
        "authority_granted": False,
        "source_modified": False,
        "replay_safe": True,
    }
    terminal["terminal_result_digest"] = _digest(terminal)
    if len(json.dumps(terminal, sort_keys=True, separators=(",", ":")).encode()) > MAX_TERMINAL_RESULT_BYTES:
        raise ValueError("Authoritative terminal result exceeded bounded size")

    row["state"] = terminal_state
    row["execution_in_progress"] = False
    row["execution_performed"] = bool(result.get("executed"))
    row["execution_terminal"] = True
    row["execution_result_digest"] = terminal["terminal_result_digest"]
    row["supervised_result_digest"] = terminal["supervised_result_digest"]
    row["outcome_digest"] = terminal["outcome_digest"]
    row["execution_error_kind"] = terminal["error_kind"]
    row["execution_elapsed_ms"] = terminal["elapsed_ms"]
    row["updated_at"] = now
    state["contract_version"] = CONTRACT_VERSION
    state["revision"] = int(state.get("revision", 0)) + 1
    _save(p, state)
    return {**base, **terminal, "executor_invoked": True}


def inspect_authoritative_action_results(path: Path | str) -> dict[str, Any]:
    state = _load(Path(path))
    counts: dict[str, int] = {}
    for row in state.get("records", []):
        status = str(row.get("state") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": int(state.get("revision", 0)),
        "record_count": len(state.get("records", [])),
        "terminal_result_count": sum(counts.get(s, 0) for s in TERMINAL_EXECUTION_STATES),
        "state_counts": counts,
        "raw_output_exposed": False,
        "raw_arguments_exposed": False,
        "conversation_can_execute": False,
        "authority_granted": False,
    }
    result["inspection_digest"] = _digest(result)
    return result
