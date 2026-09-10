from __future__ import annotations
"""v1373 deterministic dependency scheduling for durable campaigns."""
import hashlib, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1373.8"
DENIED = {
    "task_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "provider_contact_authorized": False,
    "network_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}

def _d(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()

def build_dependency_schedule(*, campaign_record_digest: str, tasks: Sequence[Mapping[str, Any]], max_ready: int = 8) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{64}", str(campaign_record_digest or "")):
        return {"ok": False, "status": "campaign_lineage_required", "action_executed": False, **DENIED}
    if not tasks or len(tasks) > 512 or not (1 <= int(max_ready) <= 64):
        return {"ok": False, "status": "task_set_invalid", "action_executed": False, **DENIED}
    by_id: dict[str, dict[str, Any]] = {}
    for raw in tasks:
        tid=str(raw.get("task_id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", tid) or tid in by_id:
            return {"ok": False, "status": "task_identity_invalid", "action_executed": False, **DENIED}
        status=str(raw.get("status") or "pending")
        if status not in {"pending","completed","paused"}:
            return {"ok": False, "status": "task_status_invalid", "action_executed": False, **DENIED}
        deps=[str(x) for x in (raw.get("depends_on") or [])]
        if len(deps)!=len(set(deps)) or tid in deps:
            return {"ok": False, "status": "task_dependency_invalid", "action_executed": False, **DENIED}
        work=int(raw.get("work_units",1)); priority=int(raw.get("priority",0))
        if work < 1 or work > 100000 or priority < -1000 or priority > 1000:
            return {"ok": False, "status": "task_weight_invalid", "action_executed": False, **DENIED}
        by_id[tid]={"status":status,"deps":deps,"work":work,"priority":priority}
    for tid,row in by_id.items():
        if any(d not in by_id for d in row["deps"]):
            return {"ok": False, "status": "unknown_dependency", "action_executed": False, **DENIED}
    visiting=set(); done=set(); cycle=False
    def visit(t):
        nonlocal cycle
        if t in visiting: cycle=True; return
        if t in done or cycle: return
        visiting.add(t)
        for d in by_id[t]["deps"]: visit(d)
        visiting.remove(t); done.add(t)
    for t in by_id: visit(t)
    if cycle:
        return {"ok": False, "status": "dependency_cycle_detected", "action_executed": False, **DENIED}
    children={t:[] for t in by_id}
    for t,row in by_id.items():
        for d in row["deps"]: children[d].append(t)
    memo={}
    def critical(t):
        if t in memo:return memo[t]
        own=0 if by_id[t]["status"]=="completed" else by_id[t]["work"]
        nxt=[critical(c) for c in children[t] if by_id[c]["status"]!="completed"]
        memo[t]=own+(max(nxt) if nxt else 0);return memo[t]
    for t in by_id:critical(t)
    ready=[]; held=[]; completed=[]
    for t,row in by_id.items():
        dg=_d(t)
        if row["status"]=="completed":
            completed.append(dg); continue
        incomplete=[d for d in row["deps"] if by_id[d]["status"]!="completed"]
        if row["status"]=="paused": incomplete=["paused"]+incomplete
        entry={"task_id_digest":dg,"critical_path_units":memo[t],"priority":row["priority"],"dependency_count":len(row["deps"])}
        if not incomplete:
            ready.append(entry)
        else:
            entry["blocked_dependency_count"]=len(incomplete)
            entry["blocked_dependency_digests"]=[_d(x) for x in incomplete]
            held.append(entry)
    ready.sort(key=lambda x:(-x["critical_path_units"],-x["priority"],x["task_id_digest"]))
    selected=ready[:max_ready]
    rec={
        "contract_version":CONTRACT_VERSION,
        "campaign_record_digest":campaign_record_digest,
        "task_count":len(by_id),
        "completed_count":len(completed),
        "ready_count":len(ready),
        "held_count":len(held),
        "ready_tasks":ready,
        "selected_ready_tasks":selected,
        "held_tasks":sorted(held,key=lambda x:x["task_id_digest"]),
        "completed_task_digests":sorted(completed),
        "critical_path_units":max(memo.values()) if memo else 0,
        "schedule_exhausted":len(completed)==len(by_id),
        "content_free":True,
        "read_only":True,
        "action_executed":False,
        **DENIED,
    }
    rec["record_digest"]=_d(rec)
    return {"ok":True,"status":"dependency_schedule_ready","dependency_schedule":rec,"action_executed":False,**DENIED}

def process_dependency_schedule_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show dependency schedule","inspect dependency schedule","show campaign schedule"}:
        return {"active":False}
    rec=dict((project_state or {}).get("dependency_schedule") or {})
    return {"active":True,"ok":bool(rec),"status":"dependency_schedule_found" if rec else "dependency_schedule_missing","dependency_schedule":rec,"action_executed":False,**DENIED}
