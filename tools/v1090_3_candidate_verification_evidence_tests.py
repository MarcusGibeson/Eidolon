from __future__ import annotations
import argparse, concurrent.futures, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090-3-'); sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import repair_candidate_registration as registration
import repair_candidate_verification_evidence as verification
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def fixture():
 s=create_conversation_session('candidate verification',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); f=finding.create_evaluation_finding(finding_title='PRIVATE_FINDING_1090_3',finding_details='PRIVATE_DETAILS',issue_domain='interface',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True); regs=registration.register_repair_candidate(f['finding_id'],candidate_kind='source_archive',artifact_sha256='a'*64,source_manifest_sha256='b'*64,label='PRIVATE_LABEL',private_reference='PRIVATE_REF',expected_revision=f['revision'],operator_confirmed=True); return f,regs,regs['candidates'][0]
def record(regs,c,**kw):
 return verification.record_repair_candidate_verification_evidence(regs['finding_id'],c['candidate_id'],evidence_kind=kw.get('evidence_kind','core_profile'),result=kw.get('result','pass'),evidence_digest=kw.get('evidence_digest','c'*64),passed_checks=kw.get('passed_checks',12),total_checks=kw.get('total_checks',12),suite_count=kw.get('suite_count',3),source_tree_unchanged=kw.get('source_tree_unchanged',True),note=kw.get('note','PRIVATE_VERIFICATION_NOTE'),expected_revision=kw.get('expected_revision',regs['finding_revision']),operator_confirmed=kw.get('operator_confirmed',True))

def test_confirmation_and_revision_required():
 f,regs,c=fixture()
 for confirmed,rev in ((False,regs['finding_revision']),(True,None),(True,regs['finding_revision']-1)):
  try: record(regs,c,operator_confirmed=confirmed,expected_revision=rev)
  except finding.EvaluationFindingError: pass
  else: raise AssertionError('unguarded evidence')
def test_kind_result_digest_and_counts_are_validated():
 f,regs,c=fixture()
 cases=[{'evidence_kind':'moon'},{'result':'winner'},{'evidence_digest':'bad'},{'passed_checks':13,'total_checks':12},{'passed_checks':-1}]
 for kw in cases:
  try: record(regs,c,**kw)
  except finding.EvaluationFindingError: pass
  else: raise AssertionError(f'invalid accepted {kw}')
def test_passing_evidence_requires_all_checks_and_unchanged_source():
 f,regs,c=fixture()
 for kw in ({'passed_checks':11,'total_checks':12},{'source_tree_unchanged':False},{'total_checks':0,'passed_checks':0}):
  try: record(regs,c,**kw)
  except finding.EvaluationFindingError: pass
  else: raise AssertionError('invalid pass accepted')
def test_evidence_is_bound_to_immutable_candidate_identity():
 f,regs,c=fixture(); r=record(regs,c); row=r['verification_evidence'][0]; require(row['artifact_sha256']=='A'*64 and row['source_manifest_sha256']=='B'*64,'identity'); require(r['artifact_identity_bound'],'binding')
def test_private_note_is_digest_only_publicly():
 f,regs,c=fixture(); r=record(regs,c); encoded=json.dumps(r,sort_keys=True); require('PRIVATE_VERIFICATION_NOTE' not in encoded,'note leak'); require(r['verification_evidence'][0]['private_note_digest'],'digest'); require(not verification.repair_candidate_verification_evidence_contains_private_fields(r),'private key')
def test_private_record_retains_note():
 f,regs,c=fixture(); record(regs,c); private=finding.load_evaluation_finding_private(f['finding_id']); row=private['repair_candidate_review_records'][0]['verification_evidence'][0]; require(row['private_note']=='PRIVATE_VERIFICATION_NOTE','private missing')
def test_duplicate_evidence_is_idempotent():
 f,regs,c=fixture(); first=record(regs,c); dup=record(first,c,expected_revision=first['finding_revision']); require(dup['duplicate_verification_evidence'] and dup['finding_revision']==first['finding_revision'] and dup['verification_evidence_count']==1,'duplicate')
def test_same_revision_race_allows_one_writer():
 f,regs,c=fixture()
 def call(kind):
  try:return record(regs,c,evidence_kind=kind,evidence_digest=('1' if kind=='core_profile' else '2')*64)['verification_evidence_count']
  except finding.EvaluationFindingError:return 'stale'
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: results=list(ex.map(call,['core_profile','full_profile']))
 require(results.count('stale')==1 and len([x for x in results if isinstance(x,int)])==1,'race')
def test_get_and_post_api_routes():
 f,regs,c=fixture(); status,payload=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'record_candidate_verification_evidence','finding_id':f['finding_id'],'candidate_id':c['candidate_id'],'evidence_kind':'focused_suite','verification_result':'pass','evidence_digest':'d'*64,'passed_checks':9,'total_checks':9,'suite_count':1,'source_tree_unchanged':True,'expected_revision':regs['finding_revision'],'operator_confirmed':True},{}); require(status==200 and payload['data']['verification_evidence_count']==1,'POST'); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-verification-evidence',{'finding_id':[f['finding_id']],'candidate_id':[c['candidate_id']]}); require(status==200 and payload['data']['result_counts']['pass']==1,'GET')
def test_no_automatic_execution_or_authority():
 f,regs,c=fixture(); r=record(regs,c)
 for k in ('automatic_test_execution','automatic_task_created','automatic_work_item_created','autonomous_prioritization','candidate_ranked','winner_selected','patch_generated','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','writes_state'): require(r[k] is False,k)
def test_registration_order_and_source_only_privacy():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.3-candidate-verification-evidence')==1 and names.index('v1090.3-candidate-verification-evidence')<names.index('v1090.2-explicit-candidate-review-findings'),'registration')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
 for n,f in TESTS:
  try:f()
  except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1090.3-candidate-verification-evidence','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
