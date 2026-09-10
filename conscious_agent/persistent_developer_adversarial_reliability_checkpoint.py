from __future__ import annotations
import hashlib,tempfile
from pathlib import Path
from typing import Any
from adversarial_campaign_hardening_long_session_checkpoint import build_adversarial_campaign_hardening_long_session_checkpoint
from adversarial_campaign_hardening_long_session import create_long_session_evidence, register_review_nonce
from persistent_supervised_developer_hardening import create_supervised_developer_hardening_review
from complete_campaign_development_loop_alpha_checkpoint import _integrated_case
from campaign_loop_reliability_recovery_learning import create_loop_reliability_assessment, create_loop_recovery_review, apply_bounded_loop_learning
from persistent_developer_adversarial_reliability import assess_persistent_developer_reliability, create_reliability_review, public_summary
CONTRACT_VERSION='v1189.8'
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _case():
 case=_integrated_case(token='v1189-8',result_code='passed');loop,receipt=case['loop'],case['receipt'];sd=_h('source');a=create_loop_reliability_assessment(loop=loop,result_receipt=receipt,current_source_digest=sd,current_stage_digest=_h('stage'),expected_source_digest=sd,expected_stage_digest=_h('stage'),interruption_reason='none');rr=create_loop_recovery_review(assessment=a,decision='approve',recovery_action='hold',operator_decision_digest=_h('recovery'));l=apply_bounded_loop_learning(loop=loop,result_receipt=receipt,recovery_review=rr,learning_codes=('retain_verified_pattern','no_generalization'),operator_learning_digest=_h('learning'));h=create_supervised_developer_hardening_review(loop=loop,result_receipt=receipt,reliability_receipt=a,learning_receipt=l,source_digest=sd,expected_source_digest=sd,review_nonce='reliability-review-0001',operator_review_digest=_h('operator'));e=create_long_session_evidence(hardening_receipt=h,session_id='campaign-session-0001',session_index=21,started_at_ms=1000,observed_at_ms=181000,checkpoint_count=36,interruption_count=4,source_digest=sd);return h,e,sd

def build_persistent_developer_adversarial_reliability_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 checks=[];req=lambda v:checks.append(bool(v));req(build_adversarial_campaign_hardening_long_session_checkpoint(source_root=source_root,runtime_root=runtime_root)['ok']);h,e,sd=_case()
 with tempfile.TemporaryDirectory() as d:
  n=register_review_nonce(runtime_root=Path(d),campaign_id='campaign-reliability-0001',review_nonce=h['review_nonce'],operator_review_digest=_h('operator'),expected_generation=0);req(n['status']=='registered')
  good=assess_persistent_developer_reliability(hardening_receipt=h,long_session_evidence=e,nonce_registration=n,current_source_digest=sd,expected_source_digest=sd,current_nonce_generation=1,expected_nonce_generation=1,session_state='interrupted',interruption_count=4);req(good['status']=='operator_review_required');req(not good['source_stale']);req(public_summary(good)['content_free'])
  req(create_reliability_review(assessment=good,decision='approve',action='resume_review',operator_review_digest=_h('review'))['status']=='approved_not_executed')
  stale=assess_persistent_developer_reliability(hardening_receipt=h,long_session_evidence=e,nonce_registration=n,current_source_digest=_h('changed'),expected_source_digest=sd,current_nonce_generation=1,expected_nonce_generation=1,session_state='active',interruption_count=0);req(stale['source_stale']);req(stale['status']=='operator_review_required')
  replay=assess_persistent_developer_reliability(hardening_receipt=h,long_session_evidence=e,nonce_registration=n,current_source_digest=sd,expected_source_digest=sd,current_nonce_generation=2,expected_nonce_generation=1,session_state='active',interruption_count=0);req('stale_or_replayed_nonce_generation' in replay['errors'])
  privacy=assess_persistent_developer_reliability(hardening_receipt=h,long_session_evidence=e,nonce_registration=n,current_source_digest=sd,expected_source_digest=sd,current_nonce_generation=1,expected_nonce_generation=1,session_state='paused',interruption_count=1,privacy_findings=('finding',));req('privacy_findings_present' in privacy['errors'])
  authority=assess_persistent_developer_reliability(hardening_receipt=h,long_session_evidence=e,nonce_registration=n,current_source_digest=sd,expected_source_digest=sd,current_nonce_generation=1,expected_nonce_generation=1,session_state='paused',interruption_count=1,authority_claims=('release',));req('authority_claims_present' in authority['errors'])
 for k in ('automatic_resume','automatic_retry','execution_invoked','authority_granted'):req(good[k] is False)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':'persistent-developer-adversarial-reliability-checkpoint','read_only':True,'post_available':False,'content_free':True,'source_modified':False,'authority_preserved':True,'desktop_verification_deferred_until_v1200':True,'summary':{'valid_case_count':2,'blocked_case_count':3,'review_case_count':1},'limitations':['Source and session observations remain caller-supplied evidence.','Nonce and writer durability remain local single-host filesystem foundations.','No recovery, retry, resume, or campaign work is executed.'],'structural_digest':good['adversarial_reliability_digest']}
