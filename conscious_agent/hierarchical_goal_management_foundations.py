from __future__ import annotations
"""v1285.0-v1285.2 bounded hierarchical goal-management foundations."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION="v1285.2";MAX_MILESTONES=6;MAX_TASKS_PER_MILESTONE=4;MAX_CODES=16
AUTHORITY_FLAGS={"goal_hierarchy_is_execution_authority":False,"goal_hierarchy_is_provider_authority":False,"goal_hierarchy_is_test_authority":False,"goal_hierarchy_is_update_authority":False,"goal_hierarchy_is_application_authority":False,"goal_hierarchy_is_release_authority":False,"goal_hierarchy_is_schedule_authority":False,"goal_hierarchy_activates_itself":False,"generic_approval_is_authorization":False,"independent_authority_granted":False}
_SAFE=re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$");_HEX=re.compile(r"^[a-f0-9]{64}$")
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _code(v:Any,fallback="unknown"):
 t=re.sub(r"[^a-z0-9_.:-]+","_",str(v or "").strip().lower().replace(" ","_")).strip("_")[:128];return t if t and _SAFE.fullmatch(t) else fallback
def _codes(v:Sequence[Any]):return [_code(x) for x in list(v or [])[:MAX_CODES] if _code(x)!="unknown"]
def build_goal_hierarchy(*,objective_code:str,original_intent_digest:str,milestone_codes:Sequence[str],acceptance_codes:Sequence[str]=(),risk_codes:Sequence[str]=())->dict[str,Any]:
 intent=str(original_intent_digest or "").lower();valid_intent=bool(_HEX.fullmatch(intent));milestones=[]
 for i,m in enumerate(_codes(milestone_codes)[:MAX_MILESTONES]):
  tasks=[f"{m}:inspect",f"{m}:implement",f"{m}:verify"][:MAX_TASKS_PER_MILESTONE];milestones.append({"milestone_code":m,"ordinal":i,"depends_on":[] if i==0 else [milestones[-1]["milestone_code"]],"task_codes":tasks,"test_codes":[f"{m}:focused_test",f"{m}:affected_regression"],"recovery_codes":[f"{m}:reconcile",f"{m}:rollback_candidate"],"completion_codes":[f"{m}:acceptance_met",f"{m}:evidence_sealed"],"original_intent_digest":intent})
 row={"ok":valid_intent and bool(milestones),"contract_version":CONTRACT_VERSION,"status":"hierarchical_goal_plan_ready" if valid_intent and milestones else "hierarchical_goal_plan_blocked","objective_code":_code(objective_code),"original_intent_digest":intent,"milestones":milestones,"milestone_count":len(milestones),"acceptance_codes":_codes(acceptance_codes),"risk_codes":_codes(risk_codes),"hierarchy_depth":4 if milestones else 0,"dependencies_acyclic":True,"original_intent_preserved":valid_intent and all(x["original_intent_digest"]==intent for x in milestones),"raw_operator_request_stored":False,"plan_activated":False,"work_scheduled":False,**AUTHORITY_FLAGS};row["hierarchy_digest"]=_digest(row);return row
def validate_goal_hierarchy(row:Mapping[str,Any])->dict[str,Any]:
 digest=row.get("hierarchy_digest")==_digest({k:v for k,v in row.items() if k!="hierarchy_digest"});intent=str(row.get("original_intent_digest") or "");ms=list(row.get("milestones") or []);intent_ok=bool(_HEX.fullmatch(intent)) and all(x.get("original_intent_digest")==intent for x in ms if isinstance(x,Mapping));bounded=len(ms)<=MAX_MILESTONES and all(len(x.get("task_codes") or [])<=MAX_TASKS_PER_MILESTONE for x in ms if isinstance(x,Mapping));deps=True;seen=set()
 for x in ms:
  if not isinstance(x,Mapping):deps=False;continue
  if any(d not in seen for d in x.get("depends_on") or []):deps=False
  seen.add(x.get("milestone_code"))
 auth=all(row.get(k) is v for k,v in AUTHORITY_FLAGS.items());privacy=row.get("raw_operator_request_stored") is False;ok=digest and row.get("ok") is True and intent_ok and bounded and deps and auth and privacy;return {"ok":ok,"digest_valid":digest,"intent_preserved":intent_ok,"bounded":bounded,"dependencies_acyclic":deps,"authority_contained":auth,"privacy_contained":privacy}
def hierarchy_completion_state(hierarchy:Mapping[str,Any],*,completed_task_codes:Sequence[str],passed_test_codes:Sequence[str],completed_recovery_codes:Sequence[str]=())->dict[str,Any]:
 if not validate_goal_hierarchy(hierarchy).get("ok"):raise ValueError("valid_goal_hierarchy_required")
 done=set(_codes(completed_task_codes));tests=set(_codes(passed_test_codes));recovery=set(_codes(completed_recovery_codes));rows=[]
 for m in hierarchy.get("milestones") or []:
  task_ok=set(m["task_codes"]).issubset(done);test_ok=set(m["test_codes"]).issubset(tests);rows.append({"milestone_code":m["milestone_code"],"tasks_complete":task_ok,"tests_complete":test_ok,"recovery_actions_completed":len(set(m["recovery_codes"]) & recovery),"complete":task_ok and test_ok,"original_intent_digest":hierarchy["original_intent_digest"]})
 result={"ok":True,"status":"hierarchical_goal_progress_ready","milestones":rows,"completed_milestone_count":sum(x["complete"] for x in rows),"all_complete":bool(rows) and all(x["complete"] for x in rows),"original_intent_digest":hierarchy["original_intent_digest"],"completion_does_not_grant_release_authority":True,**AUTHORITY_FLAGS};result["progress_digest"]=_digest(result);return result
__all__=["CONTRACT_VERSION","AUTHORITY_FLAGS","build_goal_hierarchy","validate_goal_hierarchy","hierarchy_completion_state"]
