from __future__ import annotations

"""Portable v1576-v1599.9 multi-cycle supervised initiative campaign.

A campaign is durable coordination over already-governed initiative evidence.
It can plan, pace, pause, resume, cancel, and select the next still-current
candidate. It never turns campaign membership into proposal, provider,
installation, promotion, model-management, or source-mutation authority.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1599.9"
PLANNING_VERSION = "v1583.9"
PACING_VERSION = "v1591.9"
CHECKPOINT_VERSION = "v1599.9"
MIN_ITEMS = 3
MAX_ITEMS = 5
MAX_CYCLES = 12
MAX_FAILURES = 3

_CONTROL = re.compile(
    r"^(?P<action>show|pause|resume|quiet|wake|cancel) supervised development campaign"
    r"(?: (?P<campaign_id>devcampaign_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{16}))?[.!?]*$",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _runtime_root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()


def _path(runtime_root: str | Path | None = None) -> Path:
    return _runtime_root(runtime_root) / "development_campaigns" / "supervised_initiative_campaign.json"


def _seal(row: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(row)
    value["campaign_digest"] = _digest({k: v for k, v in value.items() if k != "campaign_digest"})
    return value


def _valid(row: Mapping[str, Any]) -> bool:
    digest = str(row.get("campaign_digest") or "")
    return bool(digest) and digest == _digest({k: v for k, v in row.items() if k != "campaign_digest"})


def campaign_planning_contract() -> dict[str, Any]:
    contract = {
        "contract_version": PLANNING_VERSION,
        "initiative_count": {"minimum": MIN_ITEMS, "maximum": MAX_ITEMS},
        "required_item_fields": [
            "candidate_id", "evidence_digest", "success_criteria", "dependency_candidate_ids",
            "priority_score", "expected_benefit", "stop_conditions",
        ],
        "dependency_graph_required": True,
        "revision_rules": [
            "revalidate_candidate_evidence_before_activation",
            "never_silently_replace_active_item",
            "stale_or_missing_items_remain_attributable",
            "new_scope_requires_new_governed_evidence",
        ],
        "resource_estimates_are_advisory": True,
        "campaign_membership_is_execution_authority": False,
        "content_free": True,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


def _item(candidate: Mapping[str, Any]) -> dict[str, Any] | None:
    cid = str(candidate.get("candidate_id") or "")
    evidence = str(candidate.get("evidence_digest") or "")
    if not cid or len(evidence) != 64:
        return None
    deps = sorted({str(v) for v in list(candidate.get("dependency_candidate_ids") or []) if str(v) and str(v) != cid})
    criteria = [str(v) for v in list(candidate.get("acceptance_criteria") or []) if str(v)][:8]
    stable = {
        "candidate_id": cid,
        "evidence_digest": evidence,
        "value_evidence_digest": str(candidate.get("value_evidence_digest") or ""),
        "priority_score": round(max(0.0, min(1.0, float(candidate.get("priority_score") or candidate.get("comparison_score") or 0.0))), 4),
        "expected_benefit": str(candidate.get("practical_benefit") or "bounded supervised development improvement")[:160],
        "success_criteria": criteria or ["focused_verification_passes", "active_source_unchanged", "operator_review_ready"],
        "dependency_candidate_ids": deps,
        "stop_conditions": ["evidence_stale", "scope_expansion_required", "repair_budget_exhausted", "operator_pause_or_cancel"],
        "estimated_effort": str(candidate.get("effort_class") or "bounded"),
        "risk_class": str(candidate.get("risk_class") or candidate.get("risk_classification") or "bounded"),
        "state": "planned",
        "attempt_count": 0,
        "failure_count": 0,
        "proposal_id": "",
        "content_free": True,
    }
    stable["item_digest"] = _digest(stable)
    return stable


def build_campaign_plan(shortlist: Mapping[str, Any], *, source_digest: str, max_items: int = MAX_ITEMS) -> dict[str, Any]:
    if len(str(source_digest or "")) != 64:
        return {"ok": False, "status": "campaign_source_digest_required", "content_free": True}
    cap = max(MIN_ITEMS, min(MAX_ITEMS, int(max_items or MAX_ITEMS)))
    items = []
    seen = set()
    for candidate in list(shortlist.get("shortlist") or [])[:cap]:
        item = _item(candidate)
        if item and item["candidate_id"] not in seen:
            seen.add(item["candidate_id"]); items.append(item)
    if len(items) < MIN_ITEMS:
        return {"ok": False, "status": "campaign_requires_three_meaningful_initiatives", "item_count": len(items), "content_free": True}
    ids = {row["candidate_id"] for row in items}
    # Dependencies outside this bounded campaign are preserved as external gates.
    internal_graph = {row["candidate_id"]: [dep for dep in row["dependency_candidate_ids"] if dep in ids] for row in items}
    # Simple cycle detection keeps a malformed roadmap from creating permanent work.
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(node: str) -> bool:
        if node in visiting: return False
        if node in visited: return True
        visiting.add(node)
        for dep in internal_graph.get(node, []):
            if not visit(dep): return False
        visiting.remove(node); visited.add(node); return True
    if not all(visit(node) for node in internal_graph):
        return {"ok": False, "status": "campaign_dependency_cycle_rejected", "content_free": True}
    stable = {
        "contract_version": CONTRACT_VERSION,
        "source_digest": source_digest,
        "shortlist_digest": str(shortlist.get("shortlist_digest") or ""),
        "items": items,
        "item_count": len(items),
        "dependency_graph": internal_graph,
        "success_criteria": ["meaningful_items_advance_in_priority_order", "dependencies_respected", "operator_boundaries_preserved"],
        "stop_conditions": ["operator_cancel", "unsafe_authority_finding", "source_drift_requires_reconciliation", "failure_budget_exhausted"],
        "budgets": {"maximum_cycles": MAX_CYCLES, "maximum_failures": MAX_FAILURES, "maximum_active_items": 1},
        "revision_rules": campaign_planning_contract()["revision_rules"],
        "content_free": True,
    }
    stable["plan_digest"] = _digest(stable)
    stable["campaign_id"] = f"devcampaign_{stable['plan_digest'][:24]}"
    return {"ok": True, "status": "campaign_plan_ready", **stable}


def _new_state(plan: Mapping[str, Any]) -> dict[str, Any]:
    now = _now()
    return _seal({
        "contract_version": CONTRACT_VERSION,
        "campaign_id": plan["campaign_id"],
        "plan_digest": plan["plan_digest"],
        "source_digest": plan["source_digest"],
        "shortlist_digest": plan.get("shortlist_digest", ""),
        "state": "active",
        "revision": 1,
        "created_at": now,
        "updated_at": now,
        "cycle_count": 0,
        "failure_count": 0,
        "quiet_period": False,
        "active_candidate_id": "",
        "items": deepcopy(plan["items"]),
        "history": [{"event": "campaign_created", "at": now, "content_free": True}],
        "authority_boundary": {
            "proposal_authorized": False, "provider_contact_authorized": False,
            "source_mutation_authorized": False, "installation_authorized": False,
            "promotion_authorized": False, "model_management_authorized": False,
        },
        "content_free": True,
    })


def create_or_reuse_campaign(shortlist: Mapping[str, Any], *, source_digest: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    plan = build_campaign_plan(shortlist, source_digest=source_digest)
    if not plan.get("ok"):
        return plan
    path = _path(runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=10):
        existing = load_json_file(path, {}, expected_type=dict)
        if existing:
            if not _valid(existing):
                return {"ok": False, "status": "stored_campaign_integrity_failed", "content_free": True}
            if existing.get("state") in {"active", "paused"}:
                ready_item, readiness = _ready_item(existing, shortlist)
                replace_stale = (
                    existing.get("state") == "active"
                    and not str(existing.get("active_candidate_id") or "")
                    and ready_item is None
                    and readiness == "no_current_dependency_ready_item"
                    and str(existing.get("shortlist_digest") or "") != str(plan.get("shortlist_digest") or "")
                )
                if not replace_stale:
                    return {"ok": True, "status": "campaign_reused", "campaign": public_campaign(existing), "runtime_mutated": False, "content_free": True}
                state = _new_state(plan)
                state["superseded_campaign_id"] = str(existing.get("campaign_id") or "")
                state["superseded_campaign_digest"] = str(existing.get("campaign_digest") or "")
                state["history"] = (
                    list(state.get("history") or [])
                    + [{
                        "event": "stale_campaign_superseded",
                        "campaign_id": str(existing.get("campaign_id") or ""),
                        "at": _now(),
                        "content_free": True,
                    }]
                )[-80:]
                state = _seal(state)
                write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
                return {"ok": True, "status": "campaign_superseded_stale", "campaign": public_campaign(state), "runtime_mutated": True, "content_free": True}
        state = _new_state(plan)
        write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
        return {"ok": True, "status": "campaign_created", "campaign": public_campaign(state), "runtime_mutated": True, "content_free": True}


def load_campaign(runtime_root: str | Path | None = None) -> dict[str, Any]:
    row = load_json_file(_path(runtime_root), {}, expected_type=dict)
    return row if row and _valid(row) else {}


def public_campaign(row: Mapping[str, Any]) -> dict[str, Any]:
    items = [{k: v for k, v in item.items() if k not in {}} for item in list(row.get("items") or [])]
    return {
        "contract_version": CONTRACT_VERSION,
        "campaign_id": row.get("campaign_id", ""),
        "campaign_digest": row.get("campaign_digest", ""),
        "plan_digest": row.get("plan_digest", ""),
        "state": row.get("state", "missing"),
        "revision": int(row.get("revision") or 0),
        "cycle_count": int(row.get("cycle_count") or 0),
        "failure_count": int(row.get("failure_count") or 0),
        "quiet_period": bool(row.get("quiet_period")),
        "active_candidate_id": row.get("active_candidate_id", ""),
        "superseded_campaign_id": row.get("superseded_campaign_id", ""),
        "superseded_campaign_digest": row.get("superseded_campaign_digest", ""),
        "item_count": len(items),
        "items": items,
        "authority_boundary": deepcopy(row.get("authority_boundary") or {}),
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }


def _ready_item(row: Mapping[str, Any], current_shortlist: Mapping[str, Any] | None = None) -> tuple[dict[str, Any] | None, str]:
    state = str(row.get("state") or "")
    if state == "paused": return None, "campaign_paused"
    if state != "active": return None, "campaign_not_active"
    if bool(row.get("quiet_period")): return None, "campaign_quiet_period"
    if int(row.get("cycle_count") or 0) >= MAX_CYCLES: return None, "campaign_cycle_budget_exhausted"
    if int(row.get("failure_count") or 0) >= MAX_FAILURES: return None, "campaign_failure_budget_exhausted"
    if row.get("active_candidate_id"): return None, "campaign_item_already_active"
    completed = {str(item.get("candidate_id")) for item in row.get("items") or [] if item.get("state") in {"installed", "completed"}}
    current = {str(item.get("candidate_id")): item for item in list((current_shortlist or {}).get("shortlist") or [])}
    for item in sorted(list(row.get("items") or []), key=lambda it: (-float(it.get("priority_score") or 0.0), str(it.get("candidate_id") or ""))):
        if item.get("state") != "planned": continue
        if any(dep not in completed for dep in list(item.get("dependency_candidate_ids") or []) if dep in {str(x.get('candidate_id')) for x in row.get('items') or []}):
            continue
        if current_shortlist is not None:
            fresh = current.get(str(item.get("candidate_id") or ""))
            if not fresh or str(fresh.get("evidence_digest") or "") != str(item.get("evidence_digest") or ""):
                continue
        return dict(item), "ready"
    return None, "no_current_dependency_ready_item"


def select_next_campaign_candidate(*, current_shortlist: Mapping[str, Any] | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    path = _path(runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=10):
        row = load_json_file(path, {}, expected_type=dict)
        if not row or not _valid(row): return {"ok": False, "status": "campaign_missing_or_invalid", "content_free": True}
        item, status = _ready_item(row, current_shortlist)
        if not item: return {"ok": False, "status": status, "campaign": public_campaign(row), "content_free": True}
        now = _now(); updated = dict(row); items = deepcopy(list(row.get("items") or []))
        for stored in items:
            if stored.get("candidate_id") == item["candidate_id"]:
                stored["state"] = "active"; stored["attempt_count"] = int(stored.get("attempt_count") or 0) + 1; stored["item_digest"] = _digest({k:v for k,v in stored.items() if k!='item_digest'})
        updated.update({"items": items, "active_candidate_id": item["candidate_id"], "cycle_count": int(row.get("cycle_count") or 0)+1, "revision": int(row.get("revision") or 0)+1, "updated_at": now})
        updated["history"] = (list(row.get("history") or []) + [{"event":"item_activated","candidate_id":item["candidate_id"],"at":now,"content_free":True}])[-80:]
        updated = _seal(updated); write_json_atomic(path, updated, expected_type=dict, sort_keys=True, coordinate=False)
        return {"ok": True, "status": "campaign_candidate_selected", "candidate": item, "campaign": public_campaign(updated), "runtime_mutated": True, "content_free": True}


def record_campaign_candidate_state(candidate_id: str, evidence_digest: str, state: str, *, proposal_id: str = "", runtime_root: str | Path | None = None) -> dict[str, Any]:
    allowed = {"review_ready", "installed", "blocked", "deferred", "completed"}
    if state not in allowed: return {"ok": False, "status": "campaign_item_state_invalid", "content_free": True}
    path = _path(runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=10):
        row = load_json_file(path, {}, expected_type=dict)
        if not row or not _valid(row): return {"ok": False, "status": "campaign_missing_or_invalid", "content_free": True}
        items = deepcopy(list(row.get("items") or [])); target = next((it for it in items if str(it.get("candidate_id"))==str(candidate_id)),None)
        if not target or str(target.get("evidence_digest") or "") != str(evidence_digest or ""):
            return {"ok": False, "status": "campaign_item_evidence_mismatch", "content_free": True}
        if target.get("state") == state:
            return {"ok": True, "status": "campaign_item_state_reused", "campaign": public_campaign(row), "runtime_mutated": False, "content_free": True}
        if target.get("state") in {"installed", "completed", "deferred"}:
            return {"ok": False, "status": "campaign_item_terminal", "content_free": True}
        target["state"] = state; target["proposal_id"] = str(proposal_id or target.get("proposal_id") or "")
        if state == "blocked": target["failure_count"] = int(target.get("failure_count") or 0)+1
        target["item_digest"] = _digest({k:v for k,v in target.items() if k!='item_digest'})
        now=_now(); updated=dict(row); updated["items"]=items; updated["active_candidate_id"]="" if state in allowed else str(row.get("active_candidate_id") or ""); updated["failure_count"]=int(row.get("failure_count") or 0)+(1 if state=='blocked' else 0); updated["revision"]=int(row.get("revision") or 0)+1; updated["updated_at"]=now; updated["history"]=(list(row.get("history") or [])+[{"event":f"item_{state}","candidate_id":candidate_id,"at":now,"content_free":True}])[-80:]
        if all(it.get("state") in {"installed","completed","deferred"} for it in items): updated["state"]="completed"
        updated=_seal(updated); write_json_atomic(path,updated,expected_type=dict,sort_keys=True,coordinate=False)
        return {"ok":True,"status":f"campaign_item_{state}","campaign":public_campaign(updated),"runtime_mutated":True,"content_free":True}


def pacing_contract() -> dict[str, Any]:
    contract={"contract_version":PACING_VERSION,"budgets":{"maximum_cycles":MAX_CYCLES,"maximum_failures":MAX_FAILURES,"maximum_active_items":1},"controls":["show","pause","resume","quiet","wake","cancel"],"quiet_period_supported":True,"operator_interruption_immediate":True,"one_active_campaign_across_processes":True,"locking":"metadata_mutation_lock","resume_reuses_campaign_not_execution_authority":True,"content_free":True}; contract["contract_digest"]=_digest(contract); return contract


def control_campaign(action: str, campaign_id: str = "", supplied_digest: str = "", *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    action=str(action or "").lower(); path=_path(runtime_root)
    with metadata_mutation_lock(path,timeout_seconds=10):
        row=load_json_file(path,{},expected_type=dict)
        if not row or not _valid(row): return {"active":True,"ok":False,"status":"campaign_missing_or_invalid","conversation_response":"There is no valid supervised development campaign to control.","content_free":True}
        if action=='show': return {"active":True,"ok":True,"status":"campaign_status","campaign":public_campaign(row),"conversation_response":campaign_response(row),"runtime_mutated":False,"content_free":True}
        if str(row.get('campaign_id'))!=str(campaign_id) or str(row.get('campaign_digest') or '')[:16].lower()!=str(supplied_digest or '').lower(): return {"active":True,"ok":False,"status":"campaign_control_digest_mismatch","conversation_response":"That campaign identity or digest is stale. Nothing changed.","runtime_mutated":False,"content_free":True}
        if row.get('state') in {'cancelled','completed'}: return {"active":True,"ok":False,"status":"campaign_terminal","campaign":public_campaign(row),"content_free":True}
        if action in {'quiet','wake'}:
            quiet = action == 'quiet'
            if bool(row.get('quiet_period')) == quiet:
                return {"active":True,"ok":True,"status":"campaign_control_reused","campaign":public_campaign(row),"conversation_response":campaign_response(row),"runtime_mutated":False,"content_free":True}
            now=_now(); updated=dict(row); updated['quiet_period']=quiet; updated['revision']=int(row.get('revision') or 0)+1; updated['updated_at']=now; updated['history']=(list(row.get('history') or [])+[{"event":f"campaign_{action}","at":now,"content_free":True}])[-80:]; updated=_seal(updated); write_json_atomic(path,updated,expected_type=dict,sort_keys=True,coordinate=False); return {"active":True,"ok":True,"status":"campaign_quiet" if quiet else "campaign_awake","campaign":public_campaign(updated),"conversation_response":campaign_response(updated),"runtime_mutated":True,"content_free":True}
        target={'pause':'paused','resume':'active','cancel':'cancelled'}.get(action)
        if not target: return {"active":True,"ok":False,"status":"campaign_control_unsupported","content_free":True}
        if row.get('state')==target: return {"active":True,"ok":True,"status":"campaign_control_reused","campaign":public_campaign(row),"conversation_response":campaign_response(row),"runtime_mutated":False,"content_free":True}
        if action=='resume' and row.get('state')!='paused': return {"active":True,"ok":False,"status":"campaign_not_paused","content_free":True}
        now=_now(); updated=dict(row); updated['state']=target; updated['active_candidate_id']='' if action=='cancel' else row.get('active_candidate_id',''); updated['revision']=int(row.get('revision') or 0)+1; updated['updated_at']=now; updated['history']=(list(row.get('history') or [])+[{"event":f"campaign_{action}","at":now,"content_free":True}])[-80:]; updated=_seal(updated); write_json_atomic(path,updated,expected_type=dict,sort_keys=True,coordinate=False); return {"active":True,"ok":True,"status":f"campaign_{action}d" if action!='pause' else 'campaign_paused',"campaign":public_campaign(updated),"conversation_response":campaign_response(updated),"runtime_mutated":True,"content_free":True}


def is_campaign_control(message: str) -> bool: return _CONTROL.fullmatch(str(message or '').strip()) is not None

def process_campaign_control(message: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    match=_CONTROL.fullmatch(str(message or '').strip())
    if not match: return {"active":False}
    action=match.group('action').lower()
    if action!='show' and (not match.group('campaign_id') or not match.group('digest')):
        return {"active":True,"ok":False,"status":"campaign_exact_control_required","conversation_response":"Pause, resume, quiet, wake, and cancel require the exact campaign id and digest shown by campaign status.","content_free":True}
    return control_campaign(action,match.group('campaign_id') or '',match.group('digest') or '',runtime_root=runtime_root)


def campaign_response(row: Mapping[str, Any]) -> str:
    public=public_campaign(row); states={}
    for item in public['items']: states[item.get('state')]=states.get(item.get('state'),0)+1
    return f"Supervised campaign {public['campaign_id']} is {public['state']} with {public['item_count']} bounded initiatives, {public['cycle_count']} cycles used, and item states {states}. Campaign coordination grants no installation or source authority."


def bind_shortlist_selection(shortlist: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    """Return a shortlist view selecting one exact still-current campaign item."""
    out=deepcopy(dict(shortlist or {})); target=next((dict(row) for row in list(out.get("shortlist") or []) if str(row.get("candidate_id") or "")==str(candidate_id or "")),None)
    if not target:
        return {**out,"ok":False,"status":"campaign_candidate_missing_from_current_shortlist","selection_blocked_by_stale_campaign":True}
    out["selected_candidate_id"]=str(target.get("candidate_id") or ""); out["selected"]=target; out["campaign_bound_selection"]=True; out["campaign_candidate_id"]=out["selected_candidate_id"]; return out

def current_active_campaign_candidate(*, current_shortlist: Mapping[str, Any] | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    row=load_campaign(runtime_root)
    if not row or row.get("state") not in {"active","paused"}: return {"ok":False,"status":"campaign_no_active_candidate","content_free":True}
    cid=str(row.get("active_candidate_id") or "")
    if not cid: return {"ok":False,"status":"campaign_no_active_candidate","content_free":True}
    item=next((dict(it) for it in row.get("items") or [] if str(it.get("candidate_id") or "")==cid),None)
    if not item: return {"ok":False,"status":"campaign_active_candidate_missing","content_free":True}
    if current_shortlist is not None:
        fresh=next((it for it in list(current_shortlist.get("shortlist") or []) if str(it.get("candidate_id") or "")==cid),None)
        if not fresh or str(fresh.get("evidence_digest") or "")!=str(item.get("evidence_digest") or ""):
            return {"ok":False,"status":"campaign_active_candidate_stale","candidate":item,"content_free":True}
    return {"ok":True,"status":"campaign_active_candidate_ready","candidate":item,"campaign":public_campaign(row),"content_free":True}

def checkpoint_contract() -> dict[str, Any]:
    contract={"contract_version":CHECKPOINT_VERSION,"portable_acceptance":["three_to_five_item_campaign","dependency_graph","priority_order","pause_resume_quiet_wake_cancel","restart_persistence","duplicate_control_idempotency","cycle_and_failure_budgets","one_active_item","stale_evidence_revalidation","operator_authority_preserved"],"deferred_local_evidence":["windows_cross_process_lock_race","restart_during_real_provider_failure","native_process_interruption","real_product_defect_repaired_and_installed","user_visible_capability_operator_trial"],"v1600_desktop_gate_required_for_certification":True,"automatic_promotion":False,"content_free":True}; contract['contract_digest']=_digest(contract); return contract

__all__=["CONTRACT_VERSION","MIN_ITEMS","MAX_ITEMS","MAX_CYCLES","MAX_FAILURES","campaign_planning_contract","build_campaign_plan","create_or_reuse_campaign","load_campaign","public_campaign","bind_shortlist_selection","current_active_campaign_candidate","select_next_campaign_candidate","record_campaign_candidate_state","pacing_contract","control_campaign","is_campaign_control","process_campaign_control","campaign_response","checkpoint_contract"]
