from __future__ import annotations
"""v1284.0-v1284.2 verified-outcome experiential learning foundations."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION="v1284.2";MAX_TAGS=12;MAX_EVIDENCE=16;MAX_HISTORY=20;LESSON_STATES=("active","stale","contradicted","suspended")
AUTHORITY_FLAGS={"lesson_candidate_is_execution_authority":False,"lesson_candidate_is_provider_authority":False,"lesson_candidate_is_test_authority":False,"lesson_candidate_is_update_authority":False,"lesson_candidate_is_application_authority":False,"lesson_candidate_is_release_authority":False,"lesson_candidate_is_permanent_rule":False,"lesson_candidate_writes_cognition":False,"generic_approval_is_authorization":False,"independent_authority_granted":False}
_SAFE=re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _code(v:Any,fallback="unknown"):
 t=re.sub(r"[^a-z0-9_.:-]+","_",str(v or "").strip().lower().replace(" ","_")).strip("_")[:128];return t if t and _SAFE.fullmatch(t) else fallback
def _codes(v:Sequence[Any],limit:int):return sorted({_code(x) for x in list(v or [])[:limit] if _code(x)!="unknown"})
def build_experiential_lesson(*,lesson_code:str,outcome_code:str,guidance_code:str,applicability_tags:Sequence[str],evidence_codes:Sequence[str],verified_outcome:bool,confidence:int=60,state:str="active",history:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
 st=_code(state);st=st if st in LESSON_STATES else "suspended";verified=bool(verified_outcome);score=max(0,min(95,int(confidence))) if verified else 0;st=st if verified else "suspended";row={"ok":verified,"contract_version":CONTRACT_VERSION,"status":"experiential_lesson_candidate_ready" if verified else "experiential_lesson_candidate_blocked","lesson_code":_code(lesson_code),"outcome_code":_code(outcome_code),"guidance_code":_code(guidance_code),"applicability_tags":_codes(applicability_tags,MAX_TAGS),"evidence_codes":_codes(evidence_codes,MAX_EVIDENCE),"verified_outcome":verified,"confidence":score,"state":st,"history":[dict(x) for x in list(history or [])[-MAX_HISTORY:]],"raw_outcome_content_stored":False,"raw_guidance_content_stored":False,**AUTHORITY_FLAGS};row["lesson_digest"]=_digest(row);return row
def validate_experiential_lesson(row:Mapping[str,Any])->dict[str,Any]:
 digest=row.get("lesson_digest")==_digest({k:v for k,v in row.items() if k!="lesson_digest"});verified=row.get("verified_outcome") is True and row.get("ok") is True;state=row.get("state") in LESSON_STATES;bounded=len(row.get("applicability_tags") or [])<=MAX_TAGS and len(row.get("evidence_codes") or [])<=MAX_EVIDENCE and len(row.get("history") or [])<=MAX_HISTORY;privacy=row.get("raw_outcome_content_stored") is False and row.get("raw_guidance_content_stored") is False;auth=all(row.get(k) is v for k,v in AUTHORITY_FLAGS.items());ok=digest and verified and state and bounded and privacy and auth;return {"ok":ok,"digest_valid":digest,"verified":verified,"state_valid":state,"bounded":bounded,"privacy_contained":privacy,"authority_contained":auth}
def revise_experiential_lesson(lesson:Mapping[str,Any],*,evidence_kind:str,evidence_code:str)->dict[str,Any]:
 if not validate_experiential_lesson(lesson).get("ok"):raise ValueError("valid_verified_lesson_required")
 kind=_code(evidence_kind);ev=_code(evidence_code);state=str(lesson.get("state"));score=int(lesson.get("confidence") or 0);e=list(lesson.get("evidence_codes") or []);duplicate=ev in e
 if not duplicate:
  e.append(ev)
  if kind=="verified_support":score=min(95,score+10);state="active"
  elif kind=="stale_context":score=max(0,score-25);state="stale"
  elif kind=="observed_contradiction":score=max(0,score-50);state="contradicted"
  elif kind=="evidence_retracted":score=max(0,score-35);state="suspended"
 hist=list(lesson.get("history") or [])+[{"evidence_kind":kind,"evidence_code":ev,"duplicate":duplicate,"prior_state":lesson.get("state"),"prior_confidence":lesson.get("confidence")}]
 return build_experiential_lesson(lesson_code=str(lesson.get("lesson_code")),outcome_code=str(lesson.get("outcome_code")),guidance_code=str(lesson.get("guidance_code")),applicability_tags=lesson.get("applicability_tags") or [],evidence_codes=e,verified_outcome=True,confidence=score,state=state,history=hist)
def select_applicable_lessons(*,context_tags:Sequence[str],lessons:Sequence[Mapping[str,Any]],limit:int=6)->dict[str,Any]:
 ctx=set(_codes(context_tags,MAX_TAGS));ranked=[];invalid=0
 for row in list(lessons or []):
  if not isinstance(row,Mapping) or not validate_experiential_lesson(row).get("ok"):invalid+=1;continue
  overlap=len(ctx & set(row.get("applicability_tags") or []));state=row.get("state");score=overlap*25+int(row.get("confidence") or 0)//5
  if overlap==0 or state!="active" or int(row.get("confidence") or 0)<35:continue
  ranked.append((score,str(row.get("lesson_code")),row))
 ranked.sort(key=lambda x:(-x[0],x[1]));selected=[{"lesson_code":r[2]["lesson_code"],"guidance_code":r[2]["guidance_code"],"confidence":r[2]["confidence"],"relevance_score":r[0],"lesson_digest":r[2]["lesson_digest"]} for r in ranked[:max(0,min(6,int(limit)))]];result={"ok":invalid==0,"status":"applicable_experiential_lessons_ready" if invalid==0 else "applicable_experiential_lessons_degraded","selected":selected,"selected_count":len(selected),"stale_contradicted_or_context_inappropriate_excluded":True,"indiscriminate_lesson_dump":False,"raw_content_returned":False,"invalid_lesson_count":invalid,**AUTHORITY_FLAGS};result["selection_digest"]=_digest(result);return result
__all__=["CONTRACT_VERSION","LESSON_STATES","AUTHORITY_FLAGS","build_experiential_lesson","validate_experiential_lesson","revise_experiential_lesson","select_applicable_lessons"]
