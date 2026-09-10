from __future__ import annotations
import argparse,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090-4-'); sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import repair_candidate_registration as registration
import repair_candidate_review as review
import repair_candidate_verification_evidence as verification
import repair_candidate_comparison as comparison
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def fixture(count=2):
 s=create_conversation_session('candidate comparison',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); f=finding.create_evaluation_finding(finding_title='PRIVATE_FINDING_1090_4',issue_domain='interface',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True); current=f; candidates=[]
 for i in range(count):
  regs=registration.register_repair_candidate(f['finding_id'],candidate_kind='source_archive' if i%2==0 else 'patch_artifact',artifact_sha256=f'{i+1:x}'*64,source_manifest_sha256='b'*64,label=f'PRIVATE_LABEL_{i}',private_reference=f'PRIVATE_REF_{i}',expected_revision=current['revision'],operator_confirmed=True); current={'revision':regs['finding_revision']}; candidates.append(regs['candidates'][-1])
 return f,current,candidates
def add_evidence(f,current,c,passed,total,result='pass'):
 return verification.record_repair_candidate_verification_evidence(f['finding_id'],c['candidate_id'],evidence_kind='core_profile',result=result,evidence_digest=('d' if passed==total else 'e')*64,passed_checks=passed,total_checks=total,suite_count=2,source_tree_unchanged=(result=='pass'),expected_revision=current['revision'],operator_confirmed=True)

def test_comparison_requires_two_to_eight_distinct_candidates():
 f,current,c=fixture(2)
 for ids in ([c[0]['candidate_id']], [c[0]['candidate_id']]*2):
  try:comparison.build_repair_candidate_comparison(f['finding_id'],ids)
  except finding.EvaluationFindingError:pass
  else:raise AssertionError('too few')
 f2,current2,many=fixture(9)
 try:comparison.build_repair_candidate_comparison(f2['finding_id'],[x['candidate_id'] for x in many])
 except finding.EvaluationFindingError:pass
 else:raise AssertionError('too many')
def test_candidates_must_belong_to_same_finding():
 f,current,c=fixture(2); f2,current2,c2=fixture(1)
 try:comparison.build_repair_candidate_comparison(f['finding_id'],[c[0]['candidate_id'],c2[0]['candidate_id']])
 except finding.EvaluationFindingError:pass
 else:raise AssertionError('cross-finding accepted')
def test_first_candidate_is_explicit_baseline():
 f,current,c=fixture(2); r=comparison.build_repair_candidate_comparison(f['finding_id'],[c[1]['candidate_id'],c[0]['candidate_id']]); require(r['baseline_candidate_id']==c[1]['candidate_id'] and r['deltas'][0]['baseline_candidate_id']==c[1]['candidate_id'],'baseline')
def test_count_deltas_are_descriptive():
 f,current,c=fixture(2); ev=add_evidence(f,current,c[1],10,10); r=comparison.build_repair_candidate_comparison(f['finding_id'],[c[0]['candidate_id'],c[1]['candidate_id']]); require(r['deltas'][0]['count_deltas']['verification_evidence_count']==1 and r['deltas'][0]['count_deltas']['passing_evidence_count']==1,'deltas')
def test_review_and_verification_states_are_included():
 f,current,c=fixture(2); rv=review.record_repair_candidate_review(f['finding_id'],c[1]['candidate_id'],review_area='artifact_integrity',review_outcome='reviewing',expected_revision=current['revision'],operator_confirmed=True); ev=verification.record_repair_candidate_verification_evidence(f['finding_id'],c[1]['candidate_id'],evidence_kind='focused_suite',result='pass',evidence_digest='f'*64,passed_checks=3,total_checks=3,suite_count=1,source_tree_unchanged=True,expected_revision=rv['finding_revision'],operator_confirmed=True); r=comparison.build_repair_candidate_comparison(f['finding_id'],[c[0]['candidate_id'],c[1]['candidate_id']]); row=r['candidates'][1]; require(row['review_state']=='reviewing' and row['verification_evidence_count']==1,'state')
def test_private_content_never_leaks():
 f,current,c=fixture(2); r=comparison.build_repair_candidate_comparison(f['finding_id'],[x['candidate_id'] for x in c]); encoded=json.dumps(r,sort_keys=True); require('PRIVATE_LABEL' not in encoded and 'PRIVATE_REF' not in encoded,'leak'); require(not comparison.repair_candidate_comparison_contains_private_fields(r),'private key')
def test_comparison_is_deterministic_and_read_only():
 f,current,c=fixture(2); before=finding.load_evaluation_finding_private(f['finding_id'])['revision']; a=comparison.build_repair_candidate_comparison(f['finding_id'],[x['candidate_id'] for x in c]); b=comparison.build_repair_candidate_comparison(f['finding_id'],[x['candidate_id'] for x in c]); after=finding.load_evaluation_finding_private(f['finding_id'])['revision']; require(a==b and before==after and not a['writes_state'],'determinism')
def test_api_accepts_repeated_and_comma_separated_ids():
 f,current,c=fixture(2); ids=[x['candidate_id'] for x in c]; status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-comparison',{'finding_id':[f['finding_id']],'candidate_id':ids}); require(status==200 and payload['data']['candidate_count']==2,'repeat'); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-comparison',{'finding_id':[f['finding_id']],'candidate_ids':[','.join(ids)]}); require(status==200 and payload['data']['candidate_count']==2,'comma')
def test_no_ranking_winner_or_protected_authority():
 f,current,c=fixture(2); r=comparison.build_repair_candidate_comparison(f['finding_id'],[x['candidate_id'] for x in c])
 for k in ('candidates_ranked','winner_selected','priority_assigned','autonomous_prioritization','statistical_significance_claimed','automatic_test_execution','automatic_task_created','automatic_work_item_created','patch_generated','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','writes_state'): require(r[k] is False,k)
def test_get_only_route_and_registration_order():
 source=(ROOT/'conscious_agent'/'api_server.py').read_text(); post=source[source.index('def handle_api_post'):]; require('parts == ["conversation", "repair-candidate-comparison"]' not in post,'POST'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.4-bounded-candidate-comparison')==1 and names.index('v1090.4-bounded-candidate-comparison')<names.index('v1090.3-candidate-verification-evidence'),'registration')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
 for n,f in TESTS:
  try:f()
  except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1090.4-bounded-candidate-comparison','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
