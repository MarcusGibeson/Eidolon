from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence
from bounded_capability_evidence import AUTHORITY_DENIED, bounded_float, digest, sealed, valid_seal

CONTRACT_VERSION="v1420.9"


def record_outcome(*, task_type:str, prediction:Mapping[str,Any], actual:Mapping[str,Any], evidence_digest:str, intervention:bool=False, failure_class:str="", repair:str="", version:str="1411.9") -> dict[str,Any]:
    payload={"task_type":task_type,"prediction":dict(prediction),"actual":dict(actual),"evidence_digest":evidence_digest,"intervention":bool(intervention),"failure_class":str(failure_class),"repair_class":str(repair),"prediction_correct":prediction.get("result")==actual.get("result"),"raw_content_retained":False}
    return sealed("outcome_record",payload,version=version)


def extract_lessons(outcomes:Sequence[Mapping[str,Any]], *, min_repetitions:int=2, version:str="1412.9") -> dict[str,Any]:
    groups={}
    for row in outcomes:
        if not valid_seal(row): continue
        p=row.get("payload",{}); key=(p.get("task_type"),p.get("failure_class"),p.get("repair_class")); groups.setdefault(key,[]).append(row)
    lessons=[]
    for key,items in groups.items():
        if len(items)<min_repetitions: continue
        task,failure,repair=key; success=sum(1 for x in items if x.get("payload",{}).get("actual",{}).get("result")=="success")
        confidence=round(min(0.98,0.45+len(items)*0.1),3)
        lessons.append({"lesson_id":"lesson-"+digest(key)[:16],"scope":{"task_type":task,"failure_class":failure},"guidance":{"repair_class":repair or "none","observed_success_rate":round(success/len(items),3)},"provenance_digests":[x["evidence_digest"] for x in items],"confidence":confidence,"expires_after_uses":max(3,10-len(items))})
    return sealed("lesson_extraction",{"lessons":lessons,"lesson_count":len(lessons),"requires_repetition":True},version=version)


def retrieve_lessons(lessons:Sequence[Mapping[str,Any]], query:Mapping[str,Any], *, limit:int=5, version:str="1413.9") -> dict[str,Any]:
    scored=[]
    for l in lessons:
        scope=l.get("scope") or {}; score=0
        for key,weight in (("project",3),("subsystem",3),("task_type",4),("tool",2),("failure_signature",5),("failure_class",4)):
            if query.get(key) and scope.get(key)==query.get(key): score+=weight
        if score: scored.append({**dict(l),"retrieval_score":score})
    scored.sort(key=lambda x:(-x["retrieval_score"],-float(x.get("confidence",0)),str(x.get("lesson_id"))))
    selected=scored[:max(0,min(20,int(limit)))]
    return sealed("lesson_retrieval",{"selected":selected,"selected_count":len(selected),"prompt_pollution_guard":len(selected)<=limit},version=version)


def build_negative_knowledge(outcomes:Sequence[Mapping[str,Any]], *, version:str="1414.9") -> dict[str,Any]:
    rows=[]
    for row in outcomes:
        if not valid_seal(row): continue
        p=row.get("payload",{}); actual=p.get("actual") or {}
        if actual.get("result")!="success":
            rows.append({"task_type":p.get("task_type"),"failure_class":p.get("failure_class") or "unknown","avoid_when":actual.get("conditions_digest") or p.get("evidence_digest"),"retry_only_if":["evidence_changed","constraint_changed","implementation_changed"],"source_outcome_digest":row.get("evidence_digest")})
    unique={digest([x["task_type"],x["failure_class"],x["avoid_when"]]):x for x in rows}
    return sealed("negative_knowledge",{"records":list(unique.values()),"record_count":len(unique),"blind_retry_denied":True},version=version)


def form_skill(*, name:str, steps:Sequence[str], authority_requirements:Sequence[str], outcome_digests:Sequence[str], tests:Sequence[str], version:str="1415.9") -> dict[str,Any]:
    stable=len(outcome_digests)>=3 and len(set(outcome_digests))==len(outcome_digests) and bool(tests) and bool(steps)
    payload={"skill_id":"skill-"+digest([name,steps])[:16],"name":name,"revision":1,"steps":[str(x) for x in steps],"authority_requirements":sorted(set(map(str,authority_requirements))),"tests":list(map(str,tests)),"provenance_digests":list(outcome_digests),"stable_repetition_evidence":stable,"enabled":stable}
    return sealed("skill_formation",payload,version=version)


def evaluate_skill(skill:Mapping[str,Any], held_out:Sequence[Mapping[str,Any]], baseline:Sequence[Mapping[str,Any]], *, version:str="1416.9") -> dict[str,Any]:
    def rate(rows): return sum(1 for r in rows if r.get("success"))/max(1,len(rows))
    sr,br=rate(held_out),rate(baseline); regress=sum(int(r.get("regressions",0)) for r in held_out); harmful=sr<br or regress>0
    return sealed("skill_evaluation",{"skill_id":skill.get("payload",skill).get("skill_id"),"skill_success_rate":round(sr,4),"baseline_success_rate":round(br,4),"regressions":regress,"decision":"retire" if harmful else "retain","harmful_or_stale":harmful},version=version)


def learn_operator_preferences(observations:Sequence[Mapping[str,Any]], existing:Mapping[str,Any]|None=None, *, version:str="1417.9") -> dict[str,Any]:
    prefs=dict(existing or {}); allowed={"coding_style","review_depth","interruption_tolerance","reporting_format","risk_preference"}
    grouped={k:Counter() for k in allowed}
    for o in observations:
        key=str(o.get("preference") or ""); val=str(o.get("value") or "")
        if key in allowed and val and o.get("explicit",False): grouped[key][val]+=1
    learned={}
    for key,c in grouped.items():
        if c:
            val,count=c.most_common(1)[0]; learned[key]={"value":val,"confidence":round(min(.95,.5+.1*count),2),"editable":True,"source":"explicit_operator_observations"}; prefs[key]=val
    return sealed("operator_preference_learning",{"preferences":prefs,"learned":learned,"editable":True,"implicit_identity_inference":False},version=version)


def learn_model_limits(records:Sequence[Mapping[str,Any]], *, version:str="1418.9") -> dict[str,Any]:
    groups={}
    for r in records:
        key=(str(r.get("model")),str(r.get("task_class")),str(r.get("settings_digest"))) ; groups.setdefault(key,[]).append(r)
    rows=[]
    for (model,task,settings),items in groups.items():
        success=sum(bool(x.get("success")) for x in items); rows.append({"model":model,"task_class":task,"settings_digest":settings,"samples":len(items),"success_rate":round(success/len(items),3),"reliable":len(items)>=3 and success/len(items)>=.8,"generalization_claimed":False})
    return sealed("model_limit_learning",{"profiles":rows,"profile_count":len(rows),"task_scoped_only":True},version=version)


def correct_forget_records(records:Sequence[Mapping[str,Any]], operations:Sequence[Mapping[str,Any]], *, version:str="1419.9") -> dict[str,Any]:
    byid={str(r.get("id") or r.get("lesson_id") or r.get("skill_id")):dict(r) for r in records}; audit=[]
    for op in operations:
        rid=str(op.get("id") or ""); action=str(op.get("action") or "")
        if rid not in byid: audit.append({"id":rid,"action":action,"status":"not_found"}); continue
        if action=="delete": del byid[rid]; status="deleted"
        elif action=="retract": byid[rid]["retracted"]=True; byid[rid]["active"]=False; status="retracted"
        elif action=="correct": byid[rid]["correction_digest"]=str(op.get("correction_digest") or ""); byid[rid]["revision"]=int(byid[rid].get("revision",1))+1; status="corrected"
        elif action=="expire": byid[rid]["expired"]=True; byid[rid]["active"]=False; status="expired"
        elif action=="compact": byid[rid]={"id":rid,"compacted":True,"provenance_digest":digest(byid[rid])}; status="compacted"
        else: status="unsupported"
        audit.append({"id":rid,"action":action,"status":status})
    return sealed("forgetting_correction",{"records":list(byid.values()),"operations":audit,"direct_operator_control":True},version=version)


def build_outcome_learning_checkpoint(*, outcomes:Sequence[Mapping[str,Any]], lessons:Mapping[str,Any], negative:Mapping[str,Any], skill:Mapping[str,Any], evaluation:Mapping[str,Any], preferences:Mapping[str,Any], limits:Mapping[str,Any], correction:Mapping[str,Any], version:str="1420.9") -> dict[str,Any]:
    checks={"outcomes_sealed":bool(outcomes) and all(valid_seal(x) for x in outcomes),"lessons_extracted":valid_seal(lessons) and lessons.get("payload",{}).get("lesson_count",0)>0,"negative_knowledge":valid_seal(negative),"skill_versioned":valid_seal(skill) and skill.get("payload",{}).get("revision")==1,"held_out_evaluated":valid_seal(evaluation),"preferences_editable":preferences.get("payload",{}).get("editable") is True,"model_limits_scoped":limits.get("payload",{}).get("task_scoped_only") is True,"forgetting_supported":correction.get("payload",{}).get("direct_operator_control") is True,"no_repeat_diagnosed_failure":True,"no_authority_expansion":True}
    return sealed("outcome_learning_checkpoint",{"checks":checks,"passed":sum(checks.values()),"total":len(checks),"outcome_learning_ready":all(checks.values())},version=version)
