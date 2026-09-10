from __future__ import annotations
"""v1182.6-v1182.8 supervised repair planning foundations.

Turns one exact v1182.5 diagnosis into an operator-reviewed, content-free repair
and retest plan. It does not read source, draft or apply a patch, rerun tests,
or grant authority.
"""
import hashlib, json
from typing import Any, Mapping, Sequence
SCHEMA_VERSION='1'; CONTRACT_VERSION='v1182.8'; MAX_DIAGNOSES=8
_ALLOWED_DECISIONS=frozenset({'confirm','reject','defer'})
_ALLOWED_CODES=frozenset({'python_compile_failure_observed','sandbox_test_timeout_observed','sandbox_test_execution_blocked'})
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def _text(v:Any,n:int=260)->str:return ' '.join(str(v or '').split())[:n]
def _hex(v:Any)->str:
 t=_text(v,64).lower(); return t if len(t)==64 and all(c in '0123456789abcdef' for c in t) else ''
def _receipt_valid(value:Mapping[str,Any], field:str)->bool:
 supplied=_hex(value.get(field))
 if not supplied:return False
 unsigned=dict(value);unsigned.pop(field,None)
 return _digest(unsigned)==supplied
def _base(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'content_free':True,'sandbox_only':True,'production_source_read':False,'production_source_modified':False,'source_modified':False,'patch_created':False,'patch_applied':False,'tests_rerun':False,'shell_invoked':False,'tool_invoked':False,'provider_contacted':False,'model_contacted':False,'approval_granted':False,'repair_authorized':False,'retest_authorized':False,'promotion_authorized':False,'installation_performed':False,'certification_performed':False,'release_authorized':False,'operator_review_required':True}
def review_repair_diagnosis(diagnosis:Mapping[str,Any],decision:str,operator_id:str)->dict[str,Any]:
 b=_base(); dec=_text(decision,16); op=_text(operator_id,80)
 valid=(diagnosis.get('contract_version')=='v1182.5' and diagnosis.get('diagnosis_status')=='complete' and diagnosis.get('content_free') is True and _hex(diagnosis.get('diagnosis_digest')) and _receipt_valid(diagnosis,'diagnosis_receipt_digest') and diagnosis.get('root_cause_proven') is False and diagnosis.get('repair_authorized') is False and diagnosis.get('retest_authorized') is False and dec in _ALLOWED_DECISIONS and bool(op))
 if not valid:r={**b,'review_status':'blocked','block_reason':'invalid_diagnosis_review_binding'}
 else:
  candidates=list(diagnosis.get('diagnosis_candidates') or [])[:MAX_DIAGNOSES]
  if dec=='confirm' and not candidates:r={**b,'review_status':'blocked','block_reason':'no_failure_diagnosis_to_confirm'}
  else:
   structural={'diagnosis_digest':_hex(diagnosis.get('diagnosis_digest')),'decision':dec,'operator_identity_digest':_digest(op),'candidate_count':len(candidates)}
   rd=_digest(structural); status={'confirm':'confirmed_for_repair_planning','reject':'rejected','defer':'deferred'}[dec]
   r={**b,**structural,'review_status':status,'review_id':f'repair-review-{rd[:20]}','review_digest':rd}
 r['review_receipt_digest']=_digest(r); return r
def build_supervised_repair_plan(diagnosis:Mapping[str,Any],review:Mapping[str,Any])->dict[str,Any]:
 b=_base(); valid=(review.get('contract_version')==CONTRACT_VERSION and review.get('review_status')=='confirmed_for_repair_planning' and _hex(review.get('review_digest')) and _hex(review.get('review_receipt_digest')) and _hex(review.get('diagnosis_digest'))==_hex(diagnosis.get('diagnosis_digest')) and diagnosis.get('contract_version')=='v1182.5' and diagnosis.get('diagnosis_status')=='complete')
 if not valid:r={**b,'planning_status':'blocked','block_reason':'invalid_confirmed_diagnosis_binding'}
 else:
  rows=[]
  for raw in list(diagnosis.get('diagnosis_candidates') or [])[:MAX_DIAGNOSES]:
   code=_text(raw.get('diagnosis_code'),64)
   if code not in _ALLOWED_CODES: return {**b,'planning_status':'blocked','block_reason':'unsupported_diagnosis_code','plan_receipt_digest':_digest({**b,'planning_status':'blocked','block_reason':'unsupported_diagnosis_code'})}
   mapping={
    'python_compile_failure_observed':('inspect_compile_failure_in_sandbox','minimal_sandbox_source_correction','rerun_python_compile_and_digest_check'),
    'sandbox_test_timeout_observed':('inspect_timeout_evidence_and_resource_bounds','bounded_timeout_or_code_path_correction','rerun_original_bounded_test_set'),
    'sandbox_test_execution_blocked':('repair_governance_or_binding_precondition','restore_exact_test_preconditions','request_new_test_review_before_retest')}
   inspect,repair,retest=mapping[code]
   rows.append({'diagnosis_code':code,'inspection_step':inspect,'repair_step':repair,'retest_step':retest,'minimal_change_required':True,'sandbox_only_required':True,'rollback_required':True})
  structural={'diagnosis_digest':_hex(diagnosis.get('diagnosis_digest')),'review_digest':_hex(review.get('review_digest')),'repair_steps':rows,'repair_step_count':len(rows),'acceptance_criteria':['original_failure_no_longer_observed','content_digest_matches_reviewed_sandbox_target','no_production_source_change'],'retest_intents':sorted({r['retest_step'] for r in rows}),'root_cause_proven':False,'repair_authorized':False,'retest_authorized':False}
  pd=_digest(structural); r={**b,**structural,'planning_status':'candidate','plan_id':f'supervised-repair-plan-{pd[:20]}','plan_digest':pd}
 r['plan_receipt_digest']=_digest(r); return r
def repair_plan_public_summary(plan:Mapping[str,Any])->dict[str,Any]:
 keys={'schema_version','contract_version','planning_status','block_reason','diagnosis_digest','review_digest','repair_steps','repair_step_count','acceptance_criteria','retest_intents','plan_id','plan_digest','plan_receipt_digest','root_cause_proven','repair_authorized','retest_authorized'}
 out={k:plan[k] for k in keys if k in plan}; out.update(_base()); out['summary_digest']=_digest(out); return out
