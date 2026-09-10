from __future__ import annotations
"""v1283.0-v1283.2 development-memory relevance foundations."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION="v1283.2";MAX_CANDIDATES=96;MAX_SELECTED=8;MAX_PER_TYPE=2;MAX_TAGS=12
MEMORY_TYPES=("requirement","failure","decision","operator_preference","previous_approach","lesson")
FRESHNESS=("current","recent","historical","stale","unknown")
AUTHORITY_FLAGS={"memory_retrieval_is_execution_authority":False,"memory_retrieval_is_provider_authority":False,"memory_retrieval_is_test_authority":False,"memory_retrieval_is_update_authority":False,"memory_retrieval_is_application_authority":False,"memory_retrieval_is_release_authority":False,"retrieved_preference_is_permanent_authority":False,"generic_approval_is_authorization":False,"independent_authority_granted":False}
_SAFE=re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _code(v:Any,fallback="unknown"):
 t=re.sub(r"[^a-z0-9_.:-]+","_",str(v or "").strip().lower().replace(" ","_")).strip("_")[:128];return t if t and _SAFE.fullmatch(t) else fallback
def _codes(v:Sequence[Any],limit=MAX_TAGS):return sorted({_code(x) for x in list(v or [])[:limit] if _code(x)!="unknown"})
def build_development_memory_record(*,memory_code:str,memory_type:str,relevance_tags:Sequence[str],project_code:str="",semantic_key:str="",confidence:int=50,freshness:str="recent",verification_state:str="unverified",contradicted:bool=False)->dict[str,Any]:
 typ=_code(memory_type);typ=typ if typ in MEMORY_TYPES else "unknown";fresh=_code(freshness);fresh=fresh if fresh in FRESHNESS else "unknown";row={"ok":typ in MEMORY_TYPES,"contract_version":CONTRACT_VERSION,"status":"development_memory_record_ready" if typ in MEMORY_TYPES else "development_memory_record_invalid","memory_code":_code(memory_code),"memory_type":typ,"relevance_tags":_codes(relevance_tags),"project_code":_code(project_code,"") if project_code else "","semantic_key":_code(semantic_key,"") if semantic_key else "","confidence":max(0,min(100,int(confidence))),"freshness":fresh,"verification_state":_code(verification_state),"contradicted":bool(contradicted),"raw_content_stored":False,"private_content_stored":False,**AUTHORITY_FLAGS};row["memory_digest"]=_digest(row);return row
def validate_development_memory_record(row:Mapping[str,Any])->dict[str,Any]:
 digest=row.get("memory_digest")==_digest({k:v for k,v in row.items() if k!="memory_digest"});typ=row.get("memory_type") in MEMORY_TYPES;tags=isinstance(row.get("relevance_tags"),list) and len(row.get("relevance_tags"))<=MAX_TAGS;privacy=row.get("raw_content_stored") is False and row.get("private_content_stored") is False;auth=all(row.get(k) is v for k,v in AUTHORITY_FLAGS.items());ok=digest and typ and tags and privacy and auth;return {"ok":ok,"digest_valid":digest,"type_valid":typ,"tags_bounded":tags,"privacy_contained":privacy,"authority_contained":auth}
def retrieve_relevant_development_memories(*,task_code:str,task_tags:Sequence[str],candidates:Sequence[Mapping[str,Any]],project_code:str="",limit:int=MAX_SELECTED)->dict[str,Any]:
 query=set(_codes(task_tags));project=_code(project_code,"") if project_code else "";rows=[];invalid=0
 for i,raw in enumerate(list(candidates or [])[:MAX_CANDIDATES]):
  if not isinstance(raw,Mapping) or not validate_development_memory_record(raw).get("ok"):invalid+=1;continue
  row=dict(raw);overlap=len(query & set(row.get("relevance_tags") or []));project_match=bool(project and row.get("project_code")==project);fresh={"current":12,"recent":8,"historical":2,"stale":-20,"unknown":-8}.get(row.get("freshness"),-8);verified=8 if row.get("verification_state") in {"verified","observed"} else 0;score=overlap*20+(12 if project_match else 0)+fresh+verified+min(10,int(row.get("confidence") or 0)//10)
  if row.get("contradicted") or overlap==0 or score<20:continue
  rows.append((score,i,row))
 rows.sort(key=lambda x:(-x[0],x[1]));selected=[];seen=set();per_type={}
 for score,_,row in rows:
  key=row.get("semantic_key") or row.get("memory_code");typ=row.get("memory_type")
  if key in seen or per_type.get(typ,0)>=MAX_PER_TYPE or len(selected)>=min(MAX_SELECTED,max(0,int(limit))):continue
  seen.add(key);per_type[typ]=per_type.get(typ,0)+1;selected.append({"memory_code":row["memory_code"],"memory_type":typ,"relevance_score":score,"confidence":row["confidence"],"freshness":row["freshness"],"verification_state":row["verification_state"],"memory_digest":row["memory_digest"]})
 result={"ok":invalid==0,"contract_version":CONTRACT_VERSION,"status":"development_memory_relevance_ready" if invalid==0 else "development_memory_relevance_degraded","task_code":_code(task_code),"candidate_count":min(len(list(candidates or [])),MAX_CANDIDATES),"selected":selected,"selected_count":len(selected),"selection_budget":min(MAX_SELECTED,max(0,int(limit))),"type_counts":per_type,"weak_relevance_may_return_empty":True,"indiscriminate_memory_dump":False,"raw_memory_content_returned":False,"invalid_candidate_count":invalid,**AUTHORITY_FLAGS};result["retrieval_digest"]=_digest(result);return result
__all__=["CONTRACT_VERSION","MEMORY_TYPES","AUTHORITY_FLAGS","build_development_memory_record","validate_development_memory_record","retrieve_relevant_development_memories"]
