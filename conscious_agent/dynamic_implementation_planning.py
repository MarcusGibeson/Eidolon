from __future__ import annotations

"""v1493 evidence-bound implementation planning for an operator-selected candidate.

Planning remains read-only: no workspace creation, provider call, source change,
approval, install, promotion, or certification happens here.
"""

import hashlib, json
from typing import Any, Mapping, Sequence

from development_authority import validate_operator_authorization

CONTRACT_VERSION='v1493.9'


def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def build_evidence_bound_plan(candidate:Mapping[str,Any],*,operator_selection_receipt:Mapping[str,Any]|None,available_test_files:Sequence[str]=())->dict[str,Any]:
 cid=str(candidate.get('candidate_id') or '')
 candidate_digest=str(candidate.get('eligibility_digest') or candidate.get('evidence_digest') or '')
 authorization=validate_operator_authorization(operator_selection_receipt,stage='candidate_selection',subject_id=cid,subject_digest=candidate_digest)
 if not cid or not authorization['ok']:
  return {'contract_version':CONTRACT_VERSION,'status':'planning_blocked','reason':'exact_operator_candidate_selection_required','candidate_id':cid,'plan_created':False,'workspace_prepared':False,'provider_contacted':False,'source_modified':False,'authority_granted':False,'content_free':True}
 if not bool(candidate.get('eligible_for_quality_comparison',True)):
  return {'contract_version':CONTRACT_VERSION,'status':'planning_blocked','reason':'candidate_not_eligible','candidate_id':cid,'plan_created':False,'workspace_prepared':False,'provider_contacted':False,'source_modified':False,'authority_granted':False,'content_free':True}
 source_module=str(candidate.get('source_module') or '')
 destination=str(candidate.get('proposed_destination_module') or '')
 symbols=[str(x) for x in candidate.get('source_symbols') or () if str(x)]
 if not source_module.endswith('.py') or not destination.endswith('.py') or not symbols:
  return {'contract_version':CONTRACT_VERSION,'status':'planning_blocked','reason':'candidate_evidence_incomplete','candidate_id':cid,'plan_created':False,'workspace_prepared':False,'provider_contacted':False,'source_modified':False,'authority_granted':False,'content_free':True}
 tests=sorted({str(x).replace('\\','/') for x in available_test_files if str(x).endswith('.py')})[:16]
 plan={
  'contract_version':CONTRACT_VERSION,'status':'plan_ready_for_operator_review','candidate_id':cid,
  'candidate_evidence_digest':str(candidate.get('evidence_digest') or ''),'candidate_eligibility_digest':str(candidate.get('eligibility_digest') or ''),
  'source_module':source_module,'destination_module':destination,'source_symbols':symbols,
  'requirements':[
   'preserve public behavior of retained source entry points','move only the exact selected symbols and required bounded imports','keep active source untouched until separately authorized installation','retain rollback by exact source manifest and candidate digest'],
  'assumptions':['destination module name remains unused at implementation time'],
  'uncertainties':['implementation may reveal additional import dependencies','native platform verification may still be required'],
  'prerequisites':['fresh source digest still matches candidate evidence','operator authorizes isolated workspace before implementation'],
  'implementation_steps':['revalidate exact source/evidence digest','prepare isolated workspace only after authorization','apply bounded source/destination edits inside workspace','run focused attributable tests','run retained regression set','produce review packet and rollback evidence'],
  'test_files':tests,'rollback_strategy':'restore authoritative source; discard isolated candidate workspace','reversibility':str(candidate.get('reversibility_classification') or 'unknown'),
   'operator_selected':True,'operator_selection_authorization_id':authorization['authorization_id'],'operator_selection_receipt_digest':authorization['receipt_digest'],'plan_created':True,'workspace_prepared':False,'provider_contacted':False,'source_modified':False,'approval_granted':False,'installation_authorized':False,'promotion_authorized':False,'content_free':True,
 }
 plan['plan_digest']=_digest({k:v for k,v in plan.items() if k!='plan_digest'})
 return plan


def revise_plan_from_evidence(plan:Mapping[str,Any],*,failed_reason:str='',new_prerequisite:str='')->dict[str,Any]:
 row=dict(plan or {})
 if row.get('status')!='plan_ready_for_operator_review':return row
 revisions=list(row.get('revisions') or ())
 if failed_reason or new_prerequisite:
  revisions.append({'failure_class':str(failed_reason)[:80],'new_prerequisite':str(new_prerequisite)[:120],'content_free':True})
  if new_prerequisite:
   row['prerequisites']=list(row.get('prerequisites') or ())+[str(new_prerequisite)[:160]]
 row['revisions']=revisions;row['plan_digest']=_digest({k:v for k,v in row.items() if k!='plan_digest'});return row

__all__=['CONTRACT_VERSION','build_evidence_bound_plan','revise_plan_from_evidence']
