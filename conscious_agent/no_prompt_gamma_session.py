from __future__ import annotations

"""v1398 bounded no-prompt Gamma session over an exact active standing grant."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from authority_profiles import PROTECTED_ACTIONS
from cognitive_coding_foundations import digest
from standing_session_grants import standing_session_allows

CONTRACT_VERSION = "v1398.8"
TASK_ID = re.compile(r"^backlog_[a-z0-9_]{3,48}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
DENIED = {
    "external_publish_authorized": False,
    "destructive_system_authorized": False,
    "secret_access_authorized": False,
    "model_management_authorized": False,
    "workspace_expansion_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}


def _d(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _grant_valid(grant: Mapping[str, Any]) -> bool:
    body = {k: v for k, v in dict(grant).items() if k != "grant_digest"}
    return str(grant.get("grant_digest") or "") == digest(body)


def _bounded_int(value: Any, *, minimum: int = 0, maximum: int = 100) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return max(minimum, min(maximum, parsed))


def _normalize_backlog(backlog: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for raw in backlog:
        row = dict(raw)
        tid = str(row.get("task_id") or "")
        if not TASK_ID.fullmatch(tid) or tid in seen:
            continue
        seen.add(tid)
        risk = str(row.get("risk") or "low").lower()
        action = str(row.get("action_class") or "")
        deps = sorted({str(x) for x in row.get("dependencies") or []})
        value = _bounded_int(row.get("value") or 0)
        if value is None:
            continue
        rows.append({
            "task_id": tid,
            "task_digest": _d({"task_id": tid, "kind": row.get("kind"), "action_class": action, "dependencies": deps, "value": value, "risk": risk}),
            "kind": str(row.get("kind") or "bounded_task"),
            "action_class": action,
            "dependencies": deps,
            "value": value,
            "risk": risk,
            "state": str(row.get("state") or "open"),
        })
    return sorted(rows, key=lambda r: (-r["value"], r["task_id"]))


def run_no_prompt_session(
    *,
    grant: Mapping[str, Any],
    backlog: Sequence[Mapping[str, Any]],
    executor: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    now_unix: int,
    max_items: int = 3,
) -> dict[str, Any]:
    if not _grant_valid(grant) or grant.get("state") != "active" or not grant.get("standing_session_active"):
        return {"ok": False, "status": "no_prompt_session_active_grant_required", "action_executed": False, **DENIED}
    if now_unix > int(grant.get("expires_unix") or 0):
        return {"ok": False, "status": "no_prompt_session_grant_expired", "action_executed": False, **DENIED}
    limit = max(1, min(10, int(max_items), int(((grant.get("profile_snapshot") or {}).get("limits") or {}).get("max_commands") or 1)))
    rows = _normalize_backlog(backlog)
    completed: set[str] = {r["task_id"] for r in rows if r["state"] == "complete"}
    results: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    intervention_required = False

    while len([r for r in results if r["status"] == "completed"]) < limit:
        ready = []
        for row in rows:
            if row["task_id"] in completed or any(r["task_id"] == row["task_id"] for r in results):
                continue
            if row["state"] != "open":
                continue
            if not set(row["dependencies"]).issubset(completed):
                continue
            ready.append(row)
        if not ready:
            break
        row = ready[0]
        action = row["action_class"]
        if action in PROTECTED_ACTIONS or row["risk"] not in {"low"} or not standing_session_allows(grant, action, now_unix=now_unix):
            results.append({"task_id": row["task_id"], "task_digest": row["task_digest"], "status": "skipped_boundary", "result_digest": _d({"task": row["task_digest"], "status": "skipped_boundary"})})
            decisions.append({"task_id": row["task_id"], "decision": "skip_boundary", "reason": "authority_or_risk_boundary"})
            continue
        execution_input = {"task_id": row["task_id"], "kind": row["kind"], "action_class": action, "task_digest": row["task_digest"]}
        try:
            outcome = dict(executor(dict(execution_input)) or {})
        except Exception as exc:
            outcome = {"ok": False, "failure_class": type(exc).__name__}
        executor_evidence_digest = str(outcome.get("evidence_digest") or "").lower()
        if not outcome.get("ok") or not DIGEST.fullmatch(executor_evidence_digest):
            failure_class = outcome.get("failure_class") or ("missing_executor_evidence" if outcome.get("ok") else "executor_failed")
            results.append({"task_id": row["task_id"], "task_digest": row["task_digest"], "status": "failed", "result_digest": _d({"task": row["task_digest"], "failure": failure_class})})
            decisions.append({"task_id": row["task_id"], "decision": "stop_for_intervention", "reason": str(failure_class)})
            intervention_required = True
            break
        evidence = {"task": row["task_digest"], "executor_evidence_digest": executor_evidence_digest}
        results.append({"task_id": row["task_id"], "task_digest": row["task_digest"], "status": "completed", "result_digest": _d(evidence)})
        completed.add(row["task_id"])
        decisions.append({"task_id": row["task_id"], "decision": "completed", "reason": "highest_value_ready_allowed"})

    completed_count = sum(r["status"] == "completed" for r in results)
    skipped_count = sum(r["status"] == "skipped_boundary" for r in results)
    core = {
        "contract_version": CONTRACT_VERSION,
        "grant_id_digest": _d(str(grant.get("grant_id") or "")),
        "profile_digest": grant.get("profile_digest"),
        "backlog_digest": _d(rows),
        "selected_task_count": len(results),
        "completed_count": completed_count,
        "skipped_boundary_count": skipped_count,
        "failed_count": sum(r["status"] == "failed" for r in results),
        "prompt_count": 0,
        "clarification_count": 0,
        "operator_intervention_required": intervention_required,
        "results": results,
        "material_decisions": decisions,
        "raw_executor_output_retained": False,
        "private_task_content_retained": False,
        "standing_grant_reused_outside_scope": False,
        "protected_action_executed": False,
        "action_executed": bool(results),
        **DENIED,
    }
    core["session_digest"] = _d(core)
    ok = completed_count >= 2 and not intervention_required
    return {"ok": ok, "status": "no_prompt_session_complete" if ok else "no_prompt_session_incomplete", "no_prompt_session": core, "action_executed": bool(results), **DENIED}


def process_no_prompt_session_control(text: str, *, project_state: Mapping[str, Any] | None = None, **_: Any) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show no prompt session", "inspect no prompt session", "show gamma session"}:
        return {"active": False}
    record = dict((project_state or {}).get("no_prompt_session") or {})
    return {"active": True, "ok": bool(record), "status": "no_prompt_session_found" if record else "no_prompt_session_missing", "no_prompt_session": record, "action_executed": False, **DENIED}


__all__ = ["CONTRACT_VERSION", "run_no_prompt_session", "process_no_prompt_session_control"]
