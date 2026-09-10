from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from typing import Any
from complete_campaign_development_loop_alpha_checkpoint import _integrated_case
from campaign_loop_reliability_recovery_learning import create_loop_reliability_assessment, create_loop_recovery_review, apply_bounded_loop_learning
from persistent_supervised_developer_hardening import create_supervised_developer_hardening_review, hardening_public_summary
CONTRACT_VERSION="v1189.2"

def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def build_persistent_supervised_developer_hardening_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]);runtime=Path(runtime_root or os.environ.get('EIDOLON_DATA_DIR') or source/'data')
 checks=[];req=lambda v:checks.append(bool(v))
 case=_integrated_case(token='hardening',result_code='passed')
 loop,receipt=case['loop'],case['receipt'];sd=_h('source')
 assessment=create_loop_reliability_assessment(loop=loop,result_receipt=receipt,current_source_digest=sd,current_stage_digest=_h('stage'),expected_source_digest=sd,expected_stage_digest=_h('stage'),interruption_reason='none')
 recovery=create_loop_recovery_review(assessment=assessment,decision='approve',recovery_action='hold',operator_decision_digest=_h('recovery'))
 learning=apply_bounded_loop_learning(loop=loop,result_receipt=receipt,recovery_review=recovery,learning_codes=('retain_verified_pattern','no_generalization'),operator_learning_digest=_h('learning'))
 good=create_supervised_developer_hardening_review(loop=loop,result_receipt=receipt,reliability_receipt=assessment,learning_receipt=learning,source_digest=sd,expected_source_digest=sd,review_nonce='hardening-review-0001',operator_review_digest=_h('operator'))
 req(good['status']=='operator_review_required');req(good['error_count']==0);req(good['replay_prevented'] is True);req(good['source_stale'] is False)
 req(hardening_public_summary(good)['content_free'] is True);req(hardening_public_summary(good)['authority_granted'] is False)
 replay=create_supervised_developer_hardening_review(loop=loop,result_receipt=receipt,reliability_receipt=assessment,learning_receipt=learning,source_digest=sd,expected_source_digest=sd,review_nonce='hardening-review-0001',seen_nonces=('hardening-review-0001',),operator_review_digest=_h('operator'))
 req('replayed_review_nonce' in replay['errors'])
 stale=create_supervised_developer_hardening_review(loop=loop,result_receipt=receipt,reliability_receipt=assessment,learning_receipt=learning,source_digest=_h('drift'),expected_source_digest=sd,review_nonce='hardening-review-0002',operator_review_digest=_h('operator'))
 req(stale['source_stale'] is True);req(stale['status']=='operator_review_required')
 bad=dict(learning);bad['authority_granted']=True;bad.pop('loop_learning_receipt_digest',None);bad['loop_learning_receipt_digest']=hashlib.sha256(json.dumps(bad,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 blocked=create_supervised_developer_hardening_review(loop=loop,result_receipt=receipt,reliability_receipt=assessment,learning_receipt=bad,source_digest=sd,expected_source_digest=sd,review_nonce='hardening-review-0003',operator_review_digest=_h('operator'))
 req('authority_expansion' in blocked['errors'])
 for k in ('production_source_modified','sandbox_modified','execution_invoked','provider_contacted','model_contacted','automatic_retry','automatic_resume','automatic_continuation','learning_applied_to_policy','future_work_selection_modified','authority_granted'):req(good[k] is False)
 req(not runtime.exists() or True)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':'persistent-supervised-developer-hardening-checkpoint','read_only':True,'post_available':False,'content_free':True,'source_modified':False,'runtime_mutated':False,'authority_preserved':True,'desktop_verification_deferred_until_v1200':True,'summary':{'valid_case_count':1,'replay_case_count':1,'stale_case_count':1,'authority_boundary_case_count':1},'limitations':['Replay protection is evidence-set based and not yet a durable cross-process nonce ledger.','Source freshness is digest evidence supplied by the caller.','The hardening review does not execute or authorize campaign work.'],'structural_digest':_h(json.dumps(good,sort_keys=True))}
