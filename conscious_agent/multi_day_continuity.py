from __future__ import annotations
"""v1379 compact, content-free multi-day campaign continuity capsules."""

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1379.8"
DIGEST = re.compile(r"^[a-f0-9]{64}$")
ID = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
STATES = {"active", "paused", "blocked", "completed", "recovery_required"}
DENIED = {
    "work_execution_authorized": False,
    "automatic_resume_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "provider_contact_authorized": False,
    "release_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
}


def _d(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _valid_digest(v: object, *, allow_empty: bool = False) -> bool:
    s = str(v or "")
    return (allow_empty and not s) or bool(DIGEST.fullmatch(s))


def build_continuity_capsule(
    *,
    campaign_id: str,
    campaign_record_digest: str,
    goal_digest: str,
    plan_digest: str,
    budget_digest: str,
    current_step_digest: str,
    source_digest: str,
    workspace_digest: str,
    upstream_digest: str,
    completed_steps: int,
    total_steps: int,
    state: str,
    last_active_unix: int | None = None,
    generation: int = 1,
    prior_capsule_digest: str = "",
    checkpoint_digest: str = "",
    dependency_schedule_digest: str = "",
    partial_result_digests: Sequence[str] = (),
    conflict_assessment_digest: str = "",
    rollback_transaction_digest: str = "",
) -> dict[str, Any]:
    required = [campaign_record_digest, goal_digest, plan_digest, budget_digest, current_step_digest, source_digest, workspace_digest, upstream_digest]
    optional = [prior_capsule_digest, checkpoint_digest, dependency_schedule_digest, conflict_assessment_digest, rollback_transaction_digest]
    if not ID.fullmatch(str(campaign_id or "")) or any(not _valid_digest(x) for x in required):
        return {"ok": False, "status": "continuity_lineage_invalid", "runtime_written": False, **DENIED}
    if any(not _valid_digest(x, allow_empty=True) for x in optional):
        return {"ok": False, "status": "continuity_optional_lineage_invalid", "runtime_written": False, **DENIED}
    try:
        done, total, gen = int(completed_steps), int(total_steps), int(generation)
        last = int(time.time() if last_active_unix is None else last_active_unix)
    except Exception:
        return {"ok": False, "status": "continuity_progress_invalid", "runtime_written": False, **DENIED}
    if total < 1 or done < 0 or done > total or gen < 1 or last < 0 or state not in STATES:
        return {"ok": False, "status": "continuity_progress_invalid", "runtime_written": False, **DENIED}
    if (gen == 1 and prior_capsule_digest) or (gen > 1 and not _valid_digest(prior_capsule_digest)):
        return {"ok": False, "status": "continuity_generation_invalid", "runtime_written": False, **DENIED}
    partials = sorted(set(str(x) for x in partial_result_digests))
    if len(partials) > 256 or any(not _valid_digest(x) for x in partials):
        return {"ok": False, "status": "continuity_partial_result_set_invalid", "runtime_written": False, **DENIED}
    row = {
        "contract_version": CONTRACT_VERSION,
        "campaign_id": campaign_id,
        "generation": gen,
        "prior_capsule_digest": prior_capsule_digest,
        "campaign_record_digest": campaign_record_digest,
        "goal_digest": goal_digest,
        "plan_digest": plan_digest,
        "budget_digest": budget_digest,
        "current_step_digest": current_step_digest,
        "source_digest": source_digest,
        "workspace_digest": workspace_digest,
        "upstream_digest": upstream_digest,
        "checkpoint_digest": checkpoint_digest,
        "dependency_schedule_digest": dependency_schedule_digest,
        "partial_result_set_digest": _d(partials),
        "partial_result_count": len(partials),
        "conflict_assessment_digest": conflict_assessment_digest,
        "rollback_transaction_digest": rollback_transaction_digest,
        "completed_steps": done,
        "total_steps": total,
        "remaining_steps": total - done,
        "state": state,
        "last_active_unix": last,
        "chat_history_required": False,
        "raw_goal_persisted": False,
        "raw_plan_persisted": False,
        "raw_chat_persisted": False,
        "raw_evidence_persisted": False,
        "content_free": True,
        "runtime_written": False,
        **DENIED,
    }
    row["capsule_digest"] = _d(row)
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    if len(encoded) > 8192:
        return {"ok": False, "status": "continuity_capsule_too_large", "runtime_written": False, **DENIED}
    return {"ok": True, "status": "continuity_capsule_ready", "continuity_capsule": row, "capsule_byte_count": len(encoded), "runtime_written": False, **DENIED}


def persist_continuity_capsule(*, runtime_root: str | Path, capsule: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(capsule); supplied = str(row.pop("capsule_digest", "")); valid = _valid_digest(supplied) and supplied == _d(row); row["capsule_digest"] = supplied
    if not valid or row.get("content_free") is not True or row.get("chat_history_required") is not False:
        return {"ok": False, "status": "continuity_capsule_tampered", "runtime_written": False, **DENIED}
    root = Path(runtime_root).expanduser().resolve()
    if root.exists() and root.is_symlink():
        return {"ok": False, "status": "continuity_runtime_root_unsafe", "runtime_written": False, **DENIED}
    path = root / "campaign_continuity" / str(row.get("campaign_id")) / "capsule.json"
    if path.exists():
        try: old = json.loads(path.read_text(encoding="utf-8"))
        except Exception: return {"ok": False, "status": "continuity_existing_capsule_invalid", "runtime_written": False, **DENIED}
        if old.get("capsule_digest") == supplied:
            return {"ok": True, "status": "continuity_capsule_duplicate", "capsule_digest": supplied, "runtime_written": False, **DENIED}
        if int(row.get("generation") or 0) != int(old.get("generation") or 0) + 1 or row.get("prior_capsule_digest") != old.get("capsule_digest"):
            return {"ok": False, "status": "continuity_capsule_stale_generation", "runtime_written": False, **DENIED}
    elif int(row.get("generation") or 0) != 1:
        return {"ok": False, "status": "continuity_prior_capsule_missing", "runtime_written": False, **DENIED}
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
    fd, tmp = tempfile.mkstemp(prefix=".continuity.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as h: h.write(payload); h.flush(); os.fsync(h.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return {"ok": True, "status": "continuity_capsule_stored", "capsule_digest": supplied, "stored_payload_digest": hashlib.sha256(payload).hexdigest(), "runtime_written": True, **DENIED}


def assess_multi_day_resume(
    *,
    runtime_root: str | Path,
    campaign_id: str,
    expected_capsule_digest: str,
    current_source_digest: str,
    current_workspace_digest: str,
    current_upstream_digest: str,
    now_unix: int | None = None,
    max_unreviewed_gap_seconds: int = 7 * 24 * 3600,
) -> dict[str, Any]:
    if not ID.fullmatch(str(campaign_id or "")) or not _valid_digest(expected_capsule_digest) or any(not _valid_digest(x) for x in [current_source_digest, current_workspace_digest, current_upstream_digest]) or max_unreviewed_gap_seconds < 1:
        return {"ok": False, "status": "continuity_resume_request_invalid", "work_resumed": False, **DENIED}
    path = Path(runtime_root).expanduser().resolve() / "campaign_continuity" / campaign_id / "capsule.json"
    try: row = json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {"ok": False, "status": "continuity_capsule_missing", "work_resumed": False, **DENIED}
    supplied = str(row.pop("capsule_digest", "")); valid = supplied == expected_capsule_digest and supplied == _d(row); row["capsule_digest"] = supplied
    if not valid:
        return {"ok": False, "status": "continuity_capsule_tampered_or_stale", "work_resumed": False, **DENIED}
    now = int(time.time() if now_unix is None else now_unix)
    gap = max(0, now - int(row.get("last_active_unix") or 0))
    drift = {
        "source": current_source_digest != row.get("source_digest"),
        "workspace": current_workspace_digest != row.get("workspace_digest"),
        "upstream": current_upstream_digest != row.get("upstream_digest"),
    }
    if row.get("state") == "completed": decision = "campaign_complete"
    elif any(drift.values()): decision = "reconciliation_required"
    elif gap > max_unreviewed_gap_seconds: decision = "operator_review_required_after_long_gap"
    elif row.get("state") in {"blocked", "recovery_required"}: decision = "recovery_review_required"
    else: decision = "resume_ready"
    resume = {
        "contract_version": CONTRACT_VERSION,
        "campaign_id": campaign_id,
        "capsule_digest": supplied,
        "capsule_generation": int(row.get("generation") or 0),
        "current_step_digest": str(row.get("current_step_digest") or ""),
        "completed_steps": int(row.get("completed_steps") or 0),
        "remaining_steps": int(row.get("remaining_steps") or 0),
        "calendar_gap_seconds": gap,
        "long_gap_review_threshold_seconds": max_unreviewed_gap_seconds,
        "source_drift_detected": drift["source"],
        "workspace_drift_detected": drift["workspace"],
        "upstream_drift_detected": drift["upstream"],
        "decision": decision,
        "chat_history_read": False,
        "chat_history_required": False,
        "compact_state_only": True,
        "work_resumed": False,
        "content_free": True,
        **DENIED,
    }
    resume["resume_assessment_digest"] = _d(resume)
    return {"ok": True, "status": "multi_day_resume_assessed", "resume_assessment": resume, "work_resumed": False, **DENIED}


def process_multi_day_continuity_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show campaign continuity", "inspect campaign continuity", "show multi day continuity"}:
        return {"active": False}
    rec = dict((project_state or {}).get("multi_day_continuity") or {})
    return {"active": True, "ok": bool(rec), "status": "multi_day_continuity_found" if rec else "multi_day_continuity_missing", "multi_day_continuity": rec, "action_executed": False, **DENIED}


__all__ = ["CONTRACT_VERSION", "build_continuity_capsule", "persist_continuity_capsule", "assess_multi_day_resume", "process_multi_day_continuity_control"]
