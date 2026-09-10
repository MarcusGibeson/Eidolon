from __future__ import annotations
import argparse, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090-2-'); sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import repair_candidate_registration as registration
import repair_candidate_review as review
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def fixture():
 s=create_conversation_session('Candidate review',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); f=finding.create_evaluation_finding(finding_title='PRIVATE_REVIEW_FINDING',finding_details='PRIVATE',issue_domain='interface',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True); regs=registration.register_repair_candidate(f['finding_id'],candidate_kind='patch_artifact',artifact_sha256='a'*64,source_manifest_sha256='b'*64,label='PRIVATE_REVIEW_LABEL',private_reference='PRIVATE_REVIEW_REFERENCE',expected_revision=f['revision'],operator_confirmed=True); return f,regs,regs['candidates'][0]
def record(regs,candidate,**kw):
 return review.record_repair_candidate_review(regs['finding_id'],candidate['candidate_id'],review_area=kw.get('review_area','artifact_integrity'),review_outcome=kw.get('review_outcome','reviewing'),evidence_digest=kw.get('evidence_digest','c'*64),note=kw.get('note','PRIVATE_CANDIDATE_REVIEW_NOTE'),expected_revision=kw.get('expected_revision',regs['finding_revision']),operator_confirmed=kw.get('operator_confirmed',True))

def test_review_requires_confirmation_and_exact_revision():
 f,regs,c=fixture()
 for confirmed,rev in ((False,regs['finding_revision']),(True,None),(True,regs['finding_revision']-1)):
  try:record(regs,c,operator_confirmed=confirmed,expected_revision=rev)
  except finding.EvaluationFindingError:pass
  else:raise AssertionError('unguarded review')

def test_review_area_outcome_and_evidence_are_validated():
 f,regs,c=fixture()
 for area,outcome,evidence in (('moon','reviewing','c'*64),('artifact_integrity','approved','c'*64),('artifact_integrity','reviewing','bad')):
  try:record(regs,c,review_area=area,review_outcome=outcome,evidence_digest=evidence)
  except finding.EvaluationFindingError:pass
  else:raise AssertionError('invalid review accepted')

def test_review_starts_explicitly_and_is_append_only():
 f,regs,c=fixture(); r=record(regs,c); require(r['review_state']=='reviewing' and r['review_event_count']==1,'review'); require(r['review_events'][0]['review_area']=='artifact_integrity','event')

def test_private_review_note_is_digest_only_publicly():
 f,regs,c=fixture(); r=record(regs,c); encoded=json.dumps(r,sort_keys=True); require('PRIVATE_CANDIDATE_REVIEW_NOTE' not in encoded,'note leaked'); require(r['review_events'][0]['private_note_digest'],'digest'); require(not review.repair_candidate_review_contains_private_fields(r),'private key')

def test_private_record_retains_review_note():
 f,regs,c=fixture(); record(regs,c); private=finding.load_evaluation_finding_private(f['finding_id']); event=private['repair_candidate_review_records'][0]['review_events'][0]; require(event['private_note']=='PRIVATE_CANDIDATE_REVIEW_NOTE','private note missing')

def test_duplicate_review_event_is_idempotent():
 f,regs,c=fixture(); first=record(regs,c); duplicate=review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='artifact_integrity',review_outcome='reviewing',evidence_digest='c'*64,note='PRIVATE_CANDIDATE_REVIEW_NOTE',expected_revision=first['finding_revision'],operator_confirmed=True); require(duplicate['duplicate_review_event'] and duplicate['review_event_count']==1 and duplicate['finding_revision']==first['finding_revision'],'duplicate')

def test_transition_to_acceptable_for_testing_is_not_approval():
 f,regs,c=fixture(); first=record(regs,c); second=review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='verification_evidence',review_outcome='acceptable_for_testing',evidence_digest='d'*64,expected_revision=first['finding_revision'],operator_confirmed=True); require(second['review_state']=='acceptable_for_testing' and not second['application_approval_state_exists'],'state'); require(not second['approval_granted'] and not second['patch_applied'],'authority')

def test_invalid_transition_is_rejected():
 f,regs,c=fixture()
 try:record(regs,c,review_outcome='acceptable_for_testing')
 except finding.EvaluationFindingError:pass
 else:raise AssertionError('skipped reviewing state')

def test_rejected_candidate_is_terminal():
 f,regs,c=fixture(); rejected=record(regs,c,review_outcome='rejected')
 try:review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='source_scope',review_outcome='reviewing',expected_revision=rejected['finding_revision'],operator_confirmed=True)
 except finding.EvaluationFindingError:pass
 else:raise AssertionError('terminal candidate reopened')

def test_api_get_and_post_routes():
 f,regs,c=fixture(); status,payload=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'record_candidate_review','finding_id':f['finding_id'],'candidate_id':c['candidate_id'],'review_area':'privacy_boundary','review_outcome':'reviewing','expected_revision':regs['finding_revision'],'operator_confirmed':True},{}); require(status==200 and payload['data']['review_state']=='reviewing','POST'); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-review',{'finding_id':[f['finding_id']],'candidate_id':[c['candidate_id']]}); require(status==200 and payload['data']['review_event_count']==1,'GET')

def test_no_automatic_testing_patch_or_release_authority():
 f,regs,c=fixture(); r=record(regs,c)
 for k in ('automatic_test_execution','automatic_task_created','automatic_work_item_created','autonomous_prioritization','candidate_ranked','patch_generated','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','writes_state'): require(r[k] is False,k)

def test_registration_order_and_source_only_privacy():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.2-explicit-candidate-review-findings')==1 and names.index('v1090.2-explicit-candidate-review-findings')<names.index('v1090.1-immutable-candidate-registration'),'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
 for n,f in TESTS:
  try:f()
  except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1090.2-explicit-candidate-review-findings','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
