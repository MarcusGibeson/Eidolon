from __future__ import annotations

"""Post-commit continuity for bounded multi-step deliberation.

Continuity is structural and external-runtime only. It never resolves a conflict,
creates a goal, approves a plan, or executes an action.
"""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from multi_step_deliberation import build_multi_step_deliberation
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from multi_step_deliberation import build_multi_step_deliberation

CONTRACT_VERSION = "v1153.8"
SCHEMA_VERSION = 1
MAX_SESSIONS = 64
MAX_GOALS = 3
MAX_TEXT = 220
MAX_PENDING = 64
STALE_AFTER_DAYS = 7


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _terms(value: str) -> set[str]:
    return {t for t in "".join(c.lower() if c.isalnum() else " " for c in str(value)).split() if len(t) >= 3}


def _clean(value: Any, limit: int = MAX_TEXT) -> str:
    return " ".join(str(value or "").split())[:limit]


def _safe_count(value: Any, maximum: int = 9999) -> tuple[int, bool]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0, False
    return max(0, min(maximum, number)), 0 <= number <= maximum


def _load_status(
    path: Path,
    default: dict[str, Any],
    *,
    required_list_fields: tuple[str, ...] = (),
) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return deepcopy(default), False
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return deepcopy(default), True
    if not isinstance(value, dict):
        return deepcopy(default), True
    if any(field in value and not isinstance(value.get(field), list) for field in required_list_fields):
        return deepcopy(default), True
    return value, False


def _is_stale(record: Mapping[str, Any], *, now: datetime | None = None) -> bool:
    stamp = str(record.get("recorded_at") or "")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    current = now or datetime.now(timezone.utc)
    return current - parsed > timedelta(days=STALE_AFTER_DAYS)


def _paths(runtime_root: str | Path) -> tuple[Path, Path]:
    root = Path(runtime_root).expanduser().resolve()
    return root / "deliberation_continuity.json", root.parent / "goals.json"


def _goal_context(goals_path: Path, user_message: str) -> tuple[list[dict[str, Any]], int]:
    state, malformed = _load_status(goals_path, {"goals": []}, required_list_fields=("goals",))
    message_terms = _terms(user_message)
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for row in state.get("goals") or []:
        if not isinstance(row, Mapping) or str(row.get("status") or "") not in {"planned", "active", "blocked", "paused"}:
            continue
        title = _clean(row.get("title"))
        description = _clean(row.get("description"))
        overlap = len(message_terms & _terms(title + " " + description))
        active = 2 if str(row.get("status")) == "active" else 0
        if overlap or active:
            ranked.append((overlap * 4 + active, str(row.get("id") or ""), {
                "goal_id": _clean(row.get("id"), 120),
                "title": title,
                "status": _clean(row.get("status"), 40),
                "priority": _clean(row.get("priority"), 40),
                "blocker_count": len(row.get("blockers") or []),
                "next_action_count": len(row.get("next_actions") or []),
                "authority": "context_only",
            }))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [row for _, _, row in ranked[:MAX_GOALS]], int(malformed)


def record_deliberation_continuity(
    *, runtime_root: str | Path, operation_id: str, session_id: str, user_message: str
) -> dict[str, Any]:
    """Persist one idempotent post-commit snapshot with recoverable pending state."""
    path, goals_path = _paths(runtime_root)
    pending_id = "pending-" + _digest([operation_id, session_id])[:24]
    with metadata_mutation_lock(path):
        state = load_json_file(path, {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "sessions": [], "pending": []}, expected_type=dict)
        sessions = [r for r in (state.get("sessions") or []) if isinstance(r, dict)]
        existing = next((r for r in sessions if str(r.get("operation_id") or "") == str(operation_id)), None)
        if existing:
            return deepcopy(existing)
        pending = [r for r in (state.get("pending") or []) if isinstance(r, dict)]
        if not any(str(r.get("operation_id") or "") == str(operation_id) for r in pending):
            pending.append({"pending_id": pending_id, "operation_id": str(operation_id)[:180], "session_id": str(session_id)[:180], "started_at": _now(), "content_stored": False})
            state.update({"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "sessions": sessions[-MAX_SESSIONS:], "pending": pending[-MAX_PENDING:], "updated_at": _now()})
            write_json_atomic(path, state)

    deliberation = build_multi_step_deliberation(user_message, runtime_root=Path(runtime_root))
    goals, malformed_goal_count = _goal_context(goals_path, user_message)
    cases = [{
        "case_digest": str(case.get("case_digest") or "")[:64],
        "step_count": len(case.get("steps") or []),
        "completed_step_count": sum(1 for step in (case.get("steps") or []) if step.get("complete")),
        "outcome": str((case.get("comparison") or {}).get("outcome") or "")[:80],
        "resolution_permitted": False,
        "decision_created": False,
    } for case in (deliberation.get("cases") or [])]
    record = {
        "continuity_id": "delib-" + _digest([operation_id, session_id])[:24],
        "operation_id": str(operation_id)[:180], "session_id": str(session_id)[:180], "recorded_at": _now(),
        "case_count": len(cases), "cases": cases, "goal_context": goals, "goal_context_count": len(goals),
        "malformed_goal_store_count": malformed_goal_count, "user_content_stored": False, "belief_content_stored": False,
        "resolution_permitted": False, "decision_created": False, "action_executed": False,
        "operator_authority_required_for_action": True,
    }
    with metadata_mutation_lock(path):
        state = load_json_file(path, {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "sessions": [], "pending": []}, expected_type=dict)
        sessions = [r for r in (state.get("sessions") or []) if isinstance(r, dict)]
        existing = next((r for r in sessions if str(r.get("operation_id") or "") == str(operation_id)), None)
        if existing:
            return deepcopy(existing)
        sessions.append(record)
        pending = [r for r in (state.get("pending") or []) if isinstance(r, dict) and str(r.get("operation_id") or "") != str(operation_id)]
        state.update({"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "sessions": sessions[-MAX_SESSIONS:], "pending": pending[-MAX_PENDING:], "updated_at": _now()})
        write_json_atomic(path, state)
    return deepcopy(record)


def build_deliberation_continuity_context(
    user_message: str, *, runtime_root: str | Path, session_id: str
) -> dict[str, Any]:
    """Read bounded, non-stale continuity and goal constraints without mutation."""
    path, goals_path = _paths(runtime_root)
    state, malformed_ledger = _load_status(
        path, {"sessions": [], "pending": []}, required_list_fields=("sessions", "pending")
    )
    sessions = [r for r in (state.get("sessions") or []) if isinstance(r, dict) and str(r.get("session_id") or "") == str(session_id)]
    prior_any = sessions[-1] if sessions else None
    stale = bool(prior_any and _is_stale(prior_any))
    prior = None if stale else prior_any
    goals, malformed_goal_count = _goal_context(goals_path, user_message)
    return {
        "contract_version": CONTRACT_VERSION, "type": "deliberation_continuity",
        "prior_session_present": bool(prior), "prior_session_stale": stale,
        "prior_case_count": int((prior or {}).get("case_count") or 0),
        "prior_outcomes": [str(c.get("outcome") or "")[:80] for c in ((prior or {}).get("cases") or [])[:2]],
        "goal_context": goals, "goal_context_count": len(goals),
        "malformed_continuity_store": bool(malformed_ledger), "malformed_goal_store_count": malformed_goal_count,
        "pending_recovery_count": len([r for r in (state.get("pending") or []) if isinstance(r, dict)]),
        "read_only": True, "runtime_mutated": False, "resolution_permitted": False,
        "decision_created": False, "action_executed": False, "authority_broadened": False,
    }


def inspect_deliberation_continuity(runtime_root: str | Path) -> dict[str, Any]:
    path, _ = _paths(runtime_root)
    state, malformed = _load_status(
        path, {"sessions": [], "pending": []}, required_list_fields=("sessions", "pending")
    )
    raw_rows = state.get("sessions") or []
    raw_pending = state.get("pending") or []
    rows = [r for r in raw_rows if isinstance(r, dict)]
    pending = [r for r in raw_pending if isinstance(r, dict)]
    malformed_record_count = len(raw_rows) - len(rows) + len(raw_pending) - len(pending)
    recent = []
    for row in rows[-20:]:
        cases_raw = row.get("cases") or []
        cases = [case for case in cases_raw if isinstance(case, Mapping)] if isinstance(cases_raw, list) else []
        case_count, case_count_valid = _safe_count(row.get("case_count") or 0, 2)
        goal_count, goal_count_valid = _safe_count(row.get("goal_context_count") or 0, MAX_GOALS)
        completed = 0
        completed_valid = isinstance(cases_raw, list)
        for case in cases:
            value, valid = _safe_count(case.get("completed_step_count") or 0, 4)
            completed += value
            completed_valid = completed_valid and valid
        if not case_count_valid or not goal_count_valid or not completed_valid:
            malformed_record_count += 1
        recent.append({
            "record_digest": _digest([row.get("operation_id"), row.get("session_id"), row.get("recorded_at")])[:24],
            "case_count": case_count,
            "completed_step_count": completed,
            "goal_context_count": goal_count,
            "stale": _is_stale(row),
            "content_free": not bool(row.get("user_content_stored")) and not bool(row.get("belief_content_stored")),
            "authority_preserved": not bool(row.get("resolution_permitted"))
            and not bool(row.get("decision_created"))
            and not bool(row.get("action_executed")),
        })
    return {
        "contract_version": CONTRACT_VERSION,
        "session_count": len(rows),
        "pending_count": len(pending),
        "malformed_store": malformed,
        "malformed_record_count": malformed_record_count,
        "stale_count": sum(1 for row in rows if _is_stale(row)),
        "all_content_free": all(not r.get("user_content_stored") and not r.get("belief_content_stored") for r in rows),
        "authority_preserved": all(not r.get("resolution_permitted") and not r.get("decision_created") and not r.get("action_executed") for r in rows),
        "recent": recent,
        "raw_continuity_exposed": False,
        "raw_goal_context_exposed": False,
    }
