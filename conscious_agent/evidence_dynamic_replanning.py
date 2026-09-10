from __future__ import annotations
"""v1327 evidence-triggered replanning that preserves completed work."""
from pathlib import Path
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION = "v1327.8"
MAX_STEPS = 64
REPLAN_REASONS = ("new_evidence", "failed_assumption", "source_change", "verification_result", "operator_revision", "dependency_change")


def _path(replan_id: str, runtime_root=None) -> Path:
    return evidence_root("evidence_dynamic_replanning", runtime_root) / "records" / f"{replan_id}.json"


def _step_code(row: Mapping[str, Any]) -> str:
    return str(row.get("step_code") or "").strip()


def _default_pending(previous_pending: Sequence[Mapping[str, Any]], completed: Sequence[str], reason: str) -> list[dict[str, Any]]:
    prior_codes = [_step_code(x) for x in previous_pending if _step_code(x)]
    rows: list[dict[str, Any]] = []
    anchor = completed[-1] if completed else ""
    rows.append({"step_code": "revalidate_changed_evidence", "depends_on": [anchor] if anchor else [], "checkpoint_required": True, "mutation_expected": False})
    previous = "revalidate_changed_evidence"
    for item in previous_pending:
        code = _step_code(item)
        if not code or code in completed or code == "revalidate_changed_evidence":
            continue
        row = dict(item)
        row["depends_on"] = [previous]
        row["replanned_from_previous"] = True
        row["executed"] = False
        rows.append(row)
        previous = code
    if len(rows) == 1:
        rows.append({"step_code": "acceptance_review", "depends_on": [previous], "checkpoint_required": True, "mutation_expected": False, "executed": False})
    return rows[:MAX_STEPS]


def _normalize_replacements(specs: Sequence[Mapping[str, Any]], completed: Sequence[str]) -> list[dict[str, Any]]:
    rows=[]; seen=set(completed)
    for index, raw in enumerate(list(specs)[:MAX_STEPS]):
        code=_step_code(raw)
        if not code or code in seen:
            raise ValueError("replacement_step_duplicate_or_completed")
        deps=[str(x) for x in raw.get("depends_on") or [] if str(x)]
        row={"step_code":code,"depends_on":deps,"checkpoint_required":bool(raw.get("checkpoint_required",True)),"mutation_expected":bool(raw.get("mutation_expected")),"executed":False,"replanned_from_previous":False,"replacement_index":index}
        rows.append(row);seen.add(code)
    known=set(completed)|{x["step_code"] for x in rows}
    if any(dep not in known for row in rows for dep in row["depends_on"]):
        raise ValueError("replacement_dependency_missing")
    return rows


def replan_from_evidence(
    plan: Mapping[str, Any],
    *,
    completed_step_codes: Sequence[str] = (),
    evidence_change: Mapping[str, Any] | None = None,
    reason_code: str = "new_evidence",
    replacement_specs: Sequence[Mapping[str, Any]] = (),
    runtime_root=None,
) -> dict[str, Any]:
    if not plan.get("plan_id") or not plan.get("steps"):
        raise ValueError("constructed_plan_required")
    if any(bool(plan.get(k)) for k in ("execution_authorized","project_mutation_authorized","source_application_authorized","approval_consumed")):
        raise ValueError("authority_bearing_plan_rejected")
    if reason_code not in REPLAN_REASONS:
        raise ValueError("unsupported_replan_reason")
    steps=list(plan.get("steps") or [])
    by_code={_step_code(x):dict(x) for x in steps if _step_code(x)}
    completed=[]
    for code in completed_step_codes:
        code=str(code)
        if code not in by_code: raise ValueError("completed_step_not_in_plan")
        if code not in completed: completed.append(code)
    pending=[x for x in steps if _step_code(x) not in set(completed)]
    change=dict(evidence_change or {})
    change_digests=sorted({str(x) for x in change.get("evidence_digests") or [] if str(x)})[:32]
    previous_manifest=str(plan.get("source_manifest_digest") or "")
    current_manifest=str(change.get("current_source_manifest_digest") or previous_manifest)
    manifest_changed=bool(previous_manifest and current_manifest and previous_manifest != current_manifest)
    meaningful=bool(change_digests or manifest_changed or change.get("assumption_invalidated") or change.get("verification_changed") or replacement_specs)
    if replacement_specs:
        revised_pending=_normalize_replacements(replacement_specs,completed)
    elif meaningful:
        revised_pending=_default_pending(pending,completed,reason_code)
    else:
        revised_pending=[{**dict(x),"executed":False,"replanned_from_previous":False} for x in pending]
    completed_rows=[]
    for code in completed:
        row=dict(by_code[code]);row["preserved_completed_work"]=True;completed_rows.append(row)
    revised_codes=[_step_code(x) for x in revised_pending]
    if set(completed)&set(revised_codes): raise ValueError("completed_work_repeated")
    prior_plan_digest=digest({"plan_id":plan.get("plan_id"),"source_manifest_digest":previous_manifest,"steps":steps})
    replan_id="replan_"+digest({"prior":prior_plan_digest,"completed":completed,"reason":reason_code,"evidence":change_digests,"current_manifest":current_manifest,"pending":revised_codes})[:24]
    row=seal({
        "contract_version":CONTRACT_VERSION,"replan_id":replan_id,"previous_plan_id":plan.get("plan_id"),"previous_plan_digest":prior_plan_digest,"goal_digest":plan.get("goal_digest"),
        "previous_source_manifest_digest":previous_manifest,"current_source_manifest_digest":current_manifest,"source_manifest_changed":manifest_changed,
        "reason_code":reason_code,"changed_evidence_digests":change_digests,"assumption_invalidated":bool(change.get("assumption_invalidated")),"verification_changed":bool(change.get("verification_changed")),
        "meaningful_change":meaningful,"completed_step_codes":completed,"preserved_completed_steps":completed_rows,"revised_pending_steps":revised_pending,
        "completed_step_count":len(completed_rows),"pending_step_count":len(revised_pending),"completed_work_repeated":False,"route_changed":meaningful,
        "replan_explanation_code":"evidence_changed_route_revised" if meaningful else "no_material_change_route_retained","previous_plan_mutated":False,"action_executed":False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(replan_id,runtime_root),row)
    return {"ok":True,"status":"plan_revised" if meaningful else "plan_retained","dynamic_replanning":public_dynamic_replanning(row),"action_executed":False,**PLANNING_DENIED_AUTHORITY}


def public_dynamic_replanning(row: Mapping[str, Any]) -> dict[str, Any]:
    return {"contract_version":CONTRACT_VERSION,"replan_id":row.get("replan_id"),"previous_plan_id":row.get("previous_plan_id"),"previous_plan_digest":row.get("previous_plan_digest"),"goal_digest":row.get("goal_digest"),
            "previous_source_manifest_digest":row.get("previous_source_manifest_digest"),"current_source_manifest_digest":row.get("current_source_manifest_digest"),"source_manifest_changed":bool(row.get("source_manifest_changed")),
            "reason_code":row.get("reason_code"),"changed_evidence_digests":list(row.get("changed_evidence_digests") or []),"meaningful_change":bool(row.get("meaningful_change")),
            "completed_step_codes":list(row.get("completed_step_codes") or []),"completed_step_count":int(row.get("completed_step_count") or 0),
            "revised_pending_steps":[{"step_code":_step_code(x),"depends_on":list(x.get("depends_on") or []),"checkpoint_required":bool(x.get("checkpoint_required")),"mutation_expected":bool(x.get("mutation_expected")),"executed":False} for x in row.get("revised_pending_steps") or []],
            "pending_step_count":int(row.get("pending_step_count") or 0),"completed_work_repeated":False,"route_changed":bool(row.get("route_changed")),"replan_explanation_code":row.get("replan_explanation_code"),
            "previous_plan_mutated":False,"read_only":True,"action_executed":False,**PLANNING_DENIED_AUTHORITY}


def load_dynamic_replanning(replan_id: str, *, runtime_root=None, include_private: bool=False) -> dict[str, Any]:
    row=read_json(_path(str(replan_id),runtime_root))
    if not row or not valid(row): return {}
    return row if include_private else public_dynamic_replanning(row)


def process_dynamic_replanning_control(text: str, *, plan=None, completed_step_codes=(), evidence_change=None, reason_code="new_evidence", replacement_specs=(), runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show dynamic replanning","inspect dynamic replanning","replan from evidence"}: return {"active":False}
    if not plan: return {"active":True,"ok":False,"status":"constructed_plan_required","action_executed":False,**PLANNING_DENIED_AUTHORITY}
    return {"active":True,**replan_from_evidence(plan,completed_step_codes=completed_step_codes,evidence_change=evidence_change,reason_code=reason_code,replacement_specs=replacement_specs,runtime_root=runtime_root)}


__all__=["CONTRACT_VERSION","REPLAN_REASONS","replan_from_evidence","public_dynamic_replanning","load_dynamic_replanning","process_dynamic_replanning_control"]
