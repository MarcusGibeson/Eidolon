from __future__ import annotations
import hashlib,tempfile
from pathlib import Path
from typing import Any
from persistent_supervised_developer_hardening_checkpoint import build_persistent_supervised_developer_hardening_checkpoint
from persistent_supervised_developer_hardening import create_supervised_developer_hardening_review
from complete_campaign_development_loop_alpha_checkpoint import _integrated_case
from campaign_loop_reliability_recovery_learning import create_loop_reliability_assessment, create_loop_recovery_review, apply_bounded_loop_learning
from adversarial_campaign_hardening_long_session import create_long_session_evidence, register_review_nonce, public_summary
CONTRACT_VERSION='v1189.5'
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def build_adversarial_campaign_hardening_long_session_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 checks=[];req=lambda v:checks.append(bool(v));base=build_persistent_supervised_developer_hardening_checkpoint(source_root=source_root,runtime_root=runtime_root);req(base['ok'])
 case=_integrated_case(token='long-session',result_code='passed');loop,receipt=case['loop'],case['receipt'];sd=_h('source')
 a=create_loop_reliability_assessment(loop=loop,result_receipt=receipt,current_source_digest=sd,current_stage_digest=_h('stage'),expected_source_digest=sd,expected_stage_digest=_h('stage'),interruption_reason='none')
 rr=create_loop_recovery_review(assessment=a,decision='approve',recovery_action='hold',operator_decision_digest=_h('recovery'))
 l=apply_bounded_loop_learning(loop=loop,result_receipt=receipt,recovery_review=rr,learning_codes=('retain_verified_pattern','no_generalization'),operator_learning_digest=_h('learning'))
 h=create_supervised_developer_hardening_review(loop=loop,result_receipt=receipt,reliability_receipt=a,learning_receipt=l,source_digest=sd,expected_source_digest=sd,review_nonce='long-session-review-0001',operator_review_digest=_h('operator'))
 ev=create_long_session_evidence(hardening_receipt=h,session_id='campaign-session-0001',session_index=12,started_at_ms=1000,observed_at_ms=91000,checkpoint_count=18,interruption_count=2,source_digest=sd)
 req(ev['status']=='review_required');req(ev['duration_ms']==90000);req(ev['checkpoint_count']==18);req(public_summary(ev)['content_free'])
 with tempfile.TemporaryDirectory() as d:
  root=Path(d);n1=register_review_nonce(runtime_root=root,campaign_id='campaign-long-0001',review_nonce='review-nonce-0001',operator_review_digest=_h('op'),expected_generation=0);req(n1['status']=='registered');req(n1['generation']==1)
  replay=register_review_nonce(runtime_root=root,campaign_id='campaign-long-0001',review_nonce='review-nonce-0001',operator_review_digest=_h('op'),expected_generation=1);req('replayed_review_nonce' in replay['errors'])
  stale=register_review_nonce(runtime_root=root,campaign_id='campaign-long-0001',review_nonce='review-nonce-0002',operator_review_digest=_h('op'),expected_generation=0);req('stale_nonce_generation' in stale['errors'])
 for k in ('automatic_resume','execution_invoked','authority_granted'):req(ev[k] is False)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':'adversarial-campaign-hardening-long-session-checkpoint','read_only':True,'post_available':False,'content_free':True,'source_modified':False,'authority_preserved':True,'desktop_verification_deferred_until_v1200':True,'summary':{'durable_nonce_case_count':3,'long_session_case_count':1},'limitations':['Nonce durability is local single-host filesystem storage.','Long-session metrics are caller-supplied content-free evidence.','No campaign work is executed or resumed.'],'structural_digest':ev['long_session_evidence_digest']}
