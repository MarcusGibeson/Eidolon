from __future__ import annotations

"""Strictly read-only v1224.9 prioritization and scheduling checkpoint."""

import hashlib
import json
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from operator_governed_work_prioritization_scheduling import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, MAX_SCHEDULE_SLOTS, PRIORITY_LEVELS, REVIEW_DECISIONS, SCHEDULE_REVIEW_DECISIONS, SCHEDULABLE_STATES, _rank_items, public_operator_governed_work_prioritization, public_operator_governed_work_schedule

CONTRACT_VERSION = "v1224.9"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    rows=[]
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(rows), len(rows)


def _item(item_id: str, state: str, project: str, *, conflict: bool=False) -> dict[str, Any]:
    return {
        "queue_item_id": item_id,
        "proposal_id": "devc_" + item_id[-24:],
        "project_reference": project,
        "queue_item_digest": hashlib.sha256((item_id+"queue").encode()).hexdigest(),
        "state": state,
        "current_stage": "grounded-planning",
        "pending_operator_decision": "approval" if state == "awaiting_approval" else "none",
        "safe_next_step": "review",
        "history_gap_count": 0,
        "approval_required": True,
        "approval_consumed": False,
        "duplicate_active_conflict": conflict,
    }


def build_operator_governed_work_prioritization_scheduling_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime=Path(runtime_root) if runtime_root is not None else None
    runtime_existed=runtime.exists() if runtime is not None else False
    before,count=_tree_signature(source)
    checks=[]
    check=lambda value: checks.append(bool(value))

    a="work_0123456789abcdef01234567"; b="work_1123456789abcdef01234567"; c="work_2123456789abcdef01234567"
    queue={
        "items":[_item(a,"active","project_0123456789abcd"),_item(b,"awaiting_approval","project_1123456789abcd"),_item(c,"blocked","project_2123456789abcd",conflict=True)]
    }
    overrides={
        b:{"priority_level":"critical","pinned":True,"dependency_item_ids":[a],"generation":1,"operator_governed_work_priority_override_record_digest":hashlib.sha256(b"override").hexdigest()}
    }
    ranked=_rank_items(queue,overrides)
    check(len(ranked)==3)
    check(ranked[0]["queue_item_id"]==b)
    check(ranked[0]["pinned"] is True)
    check(ranked[0]["priority_level"]=="critical")
    check(ranked[0]["dependency_item_ids"]==[a])
    check(ranked[0]["schedule_eligible"] is True)
    blocked=next(x for x in ranked if x["queue_item_id"]==c)
    check(blocked["schedule_eligible"] is False)
    check("duplicate_active_conflict" in blocked["heuristic_reasons"])
    check(all(x["old_authority_reusable"] is False for x in ranked))
    check(all(x["fresh_authority_required"] is True for x in ranked))

    pdigest=hashlib.sha256(b"prioritization").hexdigest()
    synthetic={
        "ok":True,"status":"operator_governed_work_prioritization_ready","generation":1,
        "prioritization_digest":pdigest,"source_queue_generation":1,"source_queue_digest":hashlib.sha256(b"queue").hexdigest(),
        "item_count":3,"eligible_item_count":2,"blocked_item_count":1,
        "recommended_queue_item_id":b,"recommended_project_reference":"project_1123456789abcd","items":ranked,
        "accept_phrase":f"Accept development work prioritization {pdigest}.",
        "reject_phrase":f"Reject development work prioritization {pdigest}.",
        "prepare_schedule_phrase":f"Prepare development work schedule from prioritization {pdigest}.",
    }
    public=public_operator_governed_work_prioritization(synthetic)
    check(public["ok"] is True); check(public["item_count"]==3)
    check(public["recommended_queue_item_id"]==b)
    check(public["content_free"] is True)
    check(public["schedule_is_planning_evidence_only"] is True)
    check(public["operator_review_required"] is True)
    for key in AUTHORITY_FLAGS: check(public.get(key) is False)
    for key in ("provider_contacted","tests_executed","continuation_executed","repair_executed","apply_executed","rollback_executed","project_modified","source_modified","private_request_exposed","private_path_exposed","private_content_exposed","project_name_exposed","raw_provider_output_exposed","raw_test_output_exposed"):
        check(public.get(key) is False)

    sdigest=hashlib.sha256(b"schedule").hexdigest()
    slots=[]
    for index,item_id in enumerate((a,b),1):
        slot={"slot":index,"queue_item_id":item_id,"project_reference":f"project_{index:016x}"[-24:],"priority_rank":index,"priority_level":"high","dependency_item_ids":[] if index==1 else [a],"safe_next_step":"review","fresh_authority_required":True,"execution_authorized":False}
        slot["schedule_slot_digest"]=_digest(slot); slots.append(slot)
    schedule={
        "ok":True,"status":"operator_governed_work_schedule_ready","generation":1,"schedule_digest":sdigest,
        "source_prioritization_digest":pdigest,"planning_horizon_slots":MAX_SCHEDULE_SLOTS,"slot_count":2,
        "unscheduled_eligible_item_ids":[],"slots":slots,"accept_phrase":f"Accept development work schedule {sdigest}.",
        "reject_phrase":f"Reject development work schedule {sdigest}.","revise_phrase":f"Revise development work schedule {sdigest}.",
    }
    ps=public_operator_governed_work_schedule(schedule)
    check(ps["ok"] is True); check(ps["slot_count"]==2)
    check(all(x["execution_authorized"] is False for x in ps["slots"]))
    check(ps["schedule_execution_authorized"] is False)
    check(ps["work_dispatch_authorized"] is False)

    module=(source/"conscious_agent"/"operator_governed_work_prioritization_scheduling.py").read_text(encoding="utf-8")
    ordinary=(source/"conscious_agent"/"ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    check("process_operator_governed_work_prioritization_control" in ordinary)
    check("LocalModelClient" not in module)
    check("schedule_is_planning_evidence_only" in module)
    check("old_authority_reuse_forbidden" in module)
    check(set(PRIORITY_LEVELS)=={"low","normal","high","critical"})
    check(set(REVIEW_DECISIONS)=={"accept","reject"})
    check(set(SCHEDULE_REVIEW_DECISIONS)=={"accept","reject","revise"})
    check(set(SCHEDULABLE_STATES)=={"active","awaiting_approval","resumable"})
    check(RETAINED_CONTRACT_VERSION=="v1224.8")

    registry=inspect_checkpoint_registry(source_root=source)
    descriptor=next((row for row in registry["checkpoints"] if row["checkpoint_id"]=="operator-governed-work-prioritization-scheduling-checkpoint"),None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version")==CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)

    after,after_count=_tree_signature(source)
    check(before==after and count==after_count)
    check(runtime is None or runtime.exists() is runtime_existed)
    return {
        "ok":all(checks),
        "status":"operator_governed_work_prioritization_scheduling_checkpoint_ready" if all(checks) else "operator_governed_work_prioritization_scheduling_checkpoint_failed",
        "contract_version":CONTRACT_VERSION,"read_only":True,"runtime_data_read":False,"source_modified":False,
        "project_modified":False,"authority_granted":False,"provider_contacted":False,"tests_executed":False,
        "schedule_execution_authorized":False,"work_dispatch_authorized":False,"content_free":True,
        "checks":len(checks),"passed":sum(checks),"source_file_count":count,"source_signature":before,
        "checkpoint_digest":_digest({"contract_version":CONTRACT_VERSION,"checks":len(checks),"passed":sum(checks),"source_signature":before}),
    }
