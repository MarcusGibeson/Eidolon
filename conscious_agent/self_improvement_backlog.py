from __future__ import annotations
"""v1382 evidence-backed, non-executing self-improvement backlog derivation."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1382.8';DIGEST=re.compile(r'^[a-f0-9]{64}$');CATEGORIES={'failure','performance','operator_friction','architecture_debt','missing_capability_evidence'};RISKS={'low','medium','high','protected_core'}
DENIED={'self_change_authorized':False,'work_execution_authorized':False,'source_mutation_authorized':False,'project_mutation_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_self_improvement_backlog(*,self_model_digest:str,observations:Sequence[Mapping[str,Any]],max_items:int=64)->dict[str,Any]:
 if not DIGEST.fullmatch(str(self_model_digest or '')) or not 1<=int(max_items)<=256:return {'ok':False,'status':'self_improvement_backlog_request_invalid','action_executed':False,**DENIED}
 rows=[]
 for raw in observations:
  cat=str(raw.get('category') or '');ev=str(raw.get('evidence_digest') or '');scope=str(raw.get('scope_digest') or '');issue=str(raw.get('issue_class') or '')
  if cat not in CATEGORIES or not DIGEST.fullmatch(ev) or not DIGEST.fullmatch(scope) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',issue):return {'ok':False,'status':'self_improvement_observation_invalid','action_executed':False,**DENIED}
  try:impact=int(raw.get('impact',1));confidence=int(raw.get('confidence',50));effort=int(raw.get('effort',1))
  except Exception:return {'ok':False,'status':'self_improvement_observation_invalid','action_executed':False,**DENIED}
  risk=str(raw.get('risk') or 'medium');protected=bool(raw.get('protected_boundary')) or risk=='protected_core'
  if not 1<=impact<=10 or not 0<=confidence<=100 or not 1<=effort<=10 or risk not in RISKS:return {'ok':False,'status':'self_improvement_observation_invalid','action_executed':False,**DENIED}
  rows.append({'category':cat,'evidence_digest':ev,'scope_digest':scope,'issue_class':issue,'impact':impact,'confidence':confidence,'effort':effort,'risk':risk,'protected_boundary':protected})
 if not rows or len(rows)>1024:return {'ok':False,'status':'self_improvement_observation_set_invalid','action_executed':False,**DENIED}
 # Deduplicate exact issue/scope pairs while retaining strongest evidence deterministically.
 by={}
 for r in rows:
  k=(r['scope_digest'],r['issue_class'])
  score=r['impact']*r['confidence']-r['effort']*20-(400 if r['protected_boundary'] else 0)
  prev=by.get(k)
  if prev is None or (score,r['evidence_digest'])>(prev['_score'],prev['evidence_digest']):r['_score']=score;by[k]=r
 candidates=[]
 for r in by.values():
  score=r.pop('_score');cid=_d([r['scope_digest'],r['issue_class']])
  candidates.append({**r,'candidate_id':cid,'priority_score':score,'requires_stronger_review':r['protected_boundary'] or r['risk']=='high','selected_for_execution':False,'automatic_execution_allowed':False})
 candidates.sort(key=lambda x:(-x['priority_score'],-x['confidence'],x['candidate_id']))
 candidates=candidates[:max_items]
 out={'contract_version':CONTRACT_VERSION,'self_model_digest':self_model_digest,'observation_count':len(rows),'deduplicated_count':len(by),'candidate_count':len(candidates),'candidates':candidates,'categories_present':sorted({x['category'] for x in candidates}),'backlog_only':True,'automatic_selection_performed':False,'content_free':True,'read_only':True,'action_executed':False,**DENIED};out['backlog_digest']=_d(out)
 return {'ok':True,'status':'self_improvement_backlog_ready','self_improvement_backlog':out,'action_executed':False,**DENIED}
def review_self_improvement_candidate(*,backlog:Mapping[str,Any],expected_backlog_digest:str,candidate_id:str,disposition:str,operator_reviewed:bool)->dict[str,Any]:
 row=dict(backlog);sup=str(row.pop('backlog_digest',''))
 if sup!=expected_backlog_digest or sup!=_d(row):return {'ok':False,'status':'self_improvement_backlog_stale_or_tampered','action_executed':False,**DENIED}
 if disposition not in {'propose','defer','reject'} or not operator_reviewed:return {'ok':False,'status':'self_improvement_operator_review_required','action_executed':False,**DENIED}
 cand=next((x for x in backlog.get('candidates',[]) if x.get('candidate_id')==candidate_id),None)
 if not cand:return {'ok':False,'status':'self_improvement_candidate_missing','action_executed':False,**DENIED}
 review={'contract_version':CONTRACT_VERSION,'backlog_digest':sup,'candidate_id':candidate_id,'disposition':disposition,'operator_reviewed':True,'requires_stronger_review':bool(cand.get('requires_stronger_review')),'execution_authorized':False,'content_free':True,'action_executed':False,**DENIED};review['review_digest']=_d(review)
 return {'ok':True,'status':'self_improvement_candidate_reviewed','review':review,'action_executed':False,**DENIED}
def process_self_improvement_backlog_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show self improvement backlog','inspect self improvement backlog','show improvement backlog'}:return {'active':False}
 rec=dict((project_state or {}).get('self_improvement_backlog') or {});return {'active':True,'ok':bool(rec),'status':'self_improvement_backlog_found' if rec else 'self_improvement_backlog_missing','self_improvement_backlog':rec,'action_executed':False,**DENIED}
