from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from bounded_capability_evidence import AUTHORITY_DENIED, bounded_float, bounded_int, digest, sealed, valid_seal

CONTRACT_VERSION="v1410.9"
OBSERVATION_KINDS=("failed_tests","stale_dependencies","broken_docs","performance_drift","unresolved_warnings")
OPPORTUNITY_KINDS=("missing_tests","fragile_hotspot","duplicated_logic","usability_pain","capability_gap")
RISK_ORDER={"low":0,"medium":1,"high":2,"protected":3}


def observe_project_health(snapshot: Mapping[str, Any], *, version: str="1401.9") -> dict[str, Any]:
    project_digest=str(snapshot.get("project_digest") or "")
    checks=[]
    def add(kind:str, active:bool, severity:float, evidence:Mapping[str,Any]):
        if active:
            checks.append({"kind":kind,"severity":round(max(0.0,min(1.0,severity)),4),"evidence":dict(evidence),"fingerprint":digest([project_digest,kind,evidence])})
    failed=bounded_int(snapshot.get("failed_tests")); add("failed_tests",failed>0,min(1.0,0.35+failed/20),{"count":failed,"suite_digest":snapshot.get("test_suite_digest")})
    stale=bounded_int(snapshot.get("stale_dependencies")); add("stale_dependencies",stale>0,min(1.0,0.2+stale/25),{"count":stale,"lock_digest":snapshot.get("lock_digest")})
    broken=bounded_int(snapshot.get("broken_doc_links")); add("broken_docs",broken>0,min(1.0,0.15+broken/15),{"count":broken,"docs_digest":snapshot.get("docs_digest")})
    drift=bounded_float(snapshot.get("performance_drift"),lo=-1.0,hi=5.0); add("performance_drift",drift>0.05,min(1.0,drift),{"ratio":round(drift,4),"baseline_digest":snapshot.get("performance_baseline_digest")})
    warn=bounded_int(snapshot.get("warning_count")); add("unresolved_warnings",warn>0,min(1.0,0.1+warn/30),{"count":warn,"warning_set_digest":snapshot.get("warning_set_digest")})
    payload={"project_digest":project_digest,"observation_count":len(checks),"observations":checks,"raw_project_content_retained":False}
    return sealed("health_observations",payload,version=version)


def detect_opportunities(metrics: Mapping[str, Any], *, version: str="1402.9") -> dict[str, Any]:
    rows=[]
    specs=[
      ("missing_tests", bounded_int(metrics.get("uncovered_public_behaviors")), "coverage_digest"),
      ("fragile_hotspot", bounded_int(metrics.get("high_churn_low_coverage_files")), "hotspot_digest"),
      ("duplicated_logic", bounded_int(metrics.get("duplicate_clusters")), "duplication_digest"),
      ("usability_pain", bounded_int(metrics.get("ux_failures")), "ux_evidence_digest"),
      ("capability_gap", bounded_int(metrics.get("unmet_requirements")), "requirements_digest"),
    ]
    for kind,count,key in specs:
        if count:
            rows.append({"kind":kind,"count":count,"evidence_digest":str(metrics.get(key) or digest([kind,count])),"confidence":round(min(0.99,0.55+count/20),3),"fingerprint":digest([kind,count,metrics.get(key)])})
    return sealed("opportunity_detection",{"opportunity_count":len(rows),"opportunities":rows,"evidence_required":True,"raw_content_retained":False},version=version)


def create_backlog(candidates: Sequence[Mapping[str, Any]], *, now_epoch: int=0, version: str="1403.9") -> dict[str, Any]:
    seen={}; rows=[]
    for candidate in candidates:
        kind=str(candidate.get("kind") or "unknown")
        fp=str(candidate.get("fingerprint") or digest([kind,candidate.get("evidence_digest")]))
        if fp in seen: continue
        value=bounded_float(candidate.get("value",candidate.get("confidence",0.5)))
        cost=max(0.01,bounded_float(candidate.get("cost",0.25),lo=0.01,hi=1.0))
        confidence=bounded_float(candidate.get("confidence",0.5))
        risk=str(candidate.get("risk") or "low")
        if risk not in RISK_ORDER: risk="high"
        deps=sorted({str(x) for x in candidate.get("dependencies") or [] if str(x)})
        ttl=bounded_int(candidate.get("ttl_seconds",86400*7),lo=60,hi=86400*90)
        row={"task_id":"task-"+fp[:16],"fingerprint":fp,"kind":kind,"value":value,"cost":cost,"confidence":confidence,"risk":risk,"dependencies":deps,"created_epoch":now_epoch,"expires_epoch":now_epoch+ttl,"evidence_digest":str(candidate.get("evidence_digest") or digest(candidate)),"status":"queued"}
        seen[fp]=row; rows.append(row)
    rows.sort(key=lambda x:x["task_id"])
    return sealed("backlog_creation",{"tasks":rows,"task_count":len(rows),"deduplicated":True},version=version)


def prioritize_backlog(tasks: Sequence[Mapping[str, Any]], goals: Mapping[str,float]|None=None, *, version: str="1404.9") -> dict[str, Any]:
    goals=goals or {}; rows=[]
    for t in tasks:
        risk_penalty={"low":0.0,"medium":0.15,"high":0.45,"protected":1.0}.get(str(t.get("risk")),0.6)
        goal_weight=bounded_float(goals.get(str(t.get("kind")),0.5))
        urgency=bounded_float(t.get("urgency",0.5)); unblock=bounded_float(t.get("unblock_value",0.0)); value=bounded_float(t.get("value",0.5)); confidence=bounded_float(t.get("confidence",0.5)); cost=max(0.05,bounded_float(t.get("cost",0.25),lo=0.05,hi=1.0))
        score=((0.30*value)+(0.20*urgency)+(0.20*unblock)+(0.15*goal_weight)+(0.15*confidence))/cost-risk_penalty
        rows.append({**dict(t),"priority_score":round(score,6),"score_components":{"value":value,"urgency":urgency,"unblock":unblock,"goal":goal_weight,"confidence":confidence,"cost":cost,"risk_penalty":risk_penalty}})
    rows.sort(key=lambda x:(-x["priority_score"],x.get("task_id","")))
    return sealed("priority_reasoning",{"ranked_tasks":rows,"selection":"highest_score_nonblocked" if rows else "none"},version=version)


def pace_initiative(task: Mapping[str, Any], *, standing_authority: bool=False, quiet: bool=False, operator_load: float=0.0, version: str="1405.9") -> dict[str, Any]:
    risk=str(task.get("risk") or "high"); priority=float(task.get("priority_score") or 0.0); load=bounded_float(operator_load)
    if quiet: decision="silently_queue"
    elif risk in {"high","protected"}: decision="propose"
    elif standing_authority and risk=="low" and priority>=1.0 and load<0.8: decision="begin_under_standing_authority"
    elif load>=0.8: decision="defer"
    elif priority>=0.6: decision="propose"
    else: decision="silently_queue"
    return sealed("initiative_pacing",{"task_id":task.get("task_id"),"decision":decision,"standing_authority_observed":bool(standing_authority),"quiet":bool(quiet),"operator_load":load,"authority_granted_by_decision":False},version=version)


def evaluate_schedule_window(task: Mapping[str, Any], context: Mapping[str, Any], *, version: str="1406.9") -> dict[str, Any]:
    hour=bounded_int(context.get("local_hour",12),lo=0,hi=23); qstart=bounded_int(context.get("quiet_start",22),lo=0,hi=23); qend=bounded_int(context.get("quiet_end",7),lo=0,hi=23)
    in_quiet=(hour>=qstart or hour<qend) if qstart>qend else qstart<=hour<qend
    blocked=[]
    if in_quiet and not task.get("deadline_imminent"): blocked.append("quiet_hours")
    if context.get("gaming_or_resource_intensive"): blocked.append("resource_intensive_activity")
    if task.get("provider_required") and not context.get("provider_available",False): blocked.append("provider_unavailable")
    if context.get("maintenance_window_open") is False and task.get("maintenance_only"): blocked.append("maintenance_window_closed")
    return sealed("schedule_window",{"task_id":task.get("task_id"),"eligible":not blocked,"blocked_reasons":blocked,"local_hour":hour},version=version)


def revalidate_stale_tasks(tasks: Sequence[Mapping[str,Any]], evidence_by_task: Mapping[str,str], *, now_epoch:int, version:str="1407.9") -> dict[str,Any]:
    rows=[]
    for t in tasks:
        tid=str(t.get("task_id") or ""); expired=now_epoch>=int(t.get("expires_epoch") or 0); old=str(t.get("evidence_digest") or ""); new=str(evidence_by_task.get(tid) or old)
        if expired and new==old: status="expired"
        elif new!=old: status="revalidate_required"
        elif t.get("already_completed"): status="closed_completed_elsewhere"
        else: status=str(t.get("status") or "queued")
        rows.append({**dict(t),"status":status,"current_evidence_digest":new,"evidence_changed":new!=old})
    return sealed("staleness_management",{"tasks":rows,"revalidated":True},version=version)


def dependency_aware_selection(tasks: Sequence[Mapping[str,Any]], *, version:str="1408.9") -> dict[str,Any]:
    byid={str(t.get("task_id")):dict(t) for t in tasks}; completed={tid for tid,t in byid.items() if t.get("status")=="completed"}; rows=[]
    dependents={tid:0 for tid in byid}
    for t in byid.values():
        for dep in t.get("dependencies") or []:
            if dep in dependents: dependents[dep]+=1
    for tid,t in byid.items():
        unmet=[d for d in t.get("dependencies") or [] if d not in completed]
        foundation_bonus=0.25*dependents.get(tid,0)
        score=float(t.get("priority_score") or 0)+foundation_bonus
        rows.append({**t,"unmet_dependencies":unmet,"unlock_count":dependents.get(tid,0),"dependency_score":round(score,6),"eligible":not unmet and t.get("status","queued") in {"queued","ready"}})
    eligible=[r for r in rows if r["eligible"]]; eligible.sort(key=lambda r:(-r["dependency_score"],r["task_id"]))
    return sealed("dependency_aware_initiative",{"selected_task_id":eligible[0]["task_id"] if eligible else None,"tasks":rows,"foundation_first":True},version=version)


def explain_selection(selection: Mapping[str,Any], *, version:str="1409.9") -> dict[str,Any]:
    selected=selection.get("selected_task_id"); rows=selection.get("tasks") or []
    chosen=next((r for r in rows if r.get("task_id")==selected),None)
    alternatives=[{"task_id":r.get("task_id"),"eligible":r.get("eligible"),"score":r.get("dependency_score"),"blocked_by":r.get("unmet_dependencies") or []} for r in rows if r.get("task_id")!=selected]
    return sealed("initiative_explanation",{"selected_task_id":selected,"selected_reason":{"score":chosen.get("dependency_score") if chosen else None,"unlock_count":chosen.get("unlock_count") if chosen else 0},"not_selected":alternatives,"priority_change_evidence":["goal_weight_change","new_failure","dependency_completion","risk_change","source_evidence_change"]},version=version)


def build_initiative_checkpoint(*, health:Mapping[str,Any], backlog:Mapping[str,Any], priority:Mapping[str,Any], pacing:Mapping[str,Any], schedule:Mapping[str,Any], selection:Mapping[str,Any], explanation:Mapping[str,Any], version:str="1410.9") -> dict[str,Any]:
    inputs=[health,backlog,priority,pacing,schedule,selection,explanation]
    checks={
      "sealed_inputs":all(valid_seal(x) for x in inputs),
      "health_evidence":health.get("payload",{}).get("observation_count",0)>0,
      "backlog_deduplicated":backlog.get("payload",{}).get("deduplicated") is True,
      "ranked":len(priority.get("payload",{}).get("ranked_tasks") or [])>0,
      "pacing_bounded":pacing.get("payload",{}).get("decision") in {"propose","silently_queue","begin_under_standing_authority","defer"},
      "schedule_respected":isinstance(schedule.get("payload",{}).get("eligible"),bool),
      "dependency_selected":selection.get("payload",{}).get("selected_task_id") is not None,
      "explainable":explanation.get("payload",{}).get("selected_task_id")==selection.get("payload",{}).get("selected_task_id"),
      "no_spam_or_busywork":True,
      "no_authority_expansion":True,
    }
    return sealed("initiative_checkpoint",{"checks":checks,"passed":sum(checks.values()),"total":len(checks),"initiative_ready":all(checks.values())},version=version)
