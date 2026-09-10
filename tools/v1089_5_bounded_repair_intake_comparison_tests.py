from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_reproducibility as repro
import conversation_evaluation_finding_repair_candidates as repairs
import conversation_evaluation_finding_triage as triage
import conversation_evaluation_finding_comparison as comparison
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def make(title,domain='interface',severity='major'):
 s=create_conversation_session(title,select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); return finding.create_evaluation_finding(finding_title=title,finding_details='PRIVATE_COMPARE_DETAILS',issue_domain=domain,severity=severity,evaluation_id=e['evaluation_id'],operator_confirmed=True)
def enrich(f):
 a=repro.record_reproduction_attempt(f['finding_id'],outcome='reproduced',environment_kind='same_environment',note='PRIVATE_COMPARE_NOTE',expected_revision=f['revision'],operator_confirmed=True); b=repairs.add_repair_candidate_reference(f['finding_id'],reference_kind='patch_candidate',reference_value='PRIVATE_COMPARE_REF',expected_revision=a['finding_revision'],operator_confirmed=True); c=triage.start_evaluation_finding_triage(f['finding_id'],note='PRIVATE_TRIAGE_COMPARE',expected_revision=b['finding_revision'],operator_confirmed=True); return triage.set_evaluation_finding_triage_disposition(f['finding_id'],disposition='repair_candidate_review',expected_revision=c['finding_revision'],operator_confirmed=True)
def test_requires_two_distinct_and_at_most_eight():
 f=make('PRIVATE_ONE')
 for ids in ([f['finding_id']], [f['finding_id']]*2):
  try: comparison.build_evaluation_finding_comparison(ids)
  except finding.EvaluationFindingError: pass
  else: raise AssertionError('bad lower bound')
 many=[make(f'PRIVATE_{i}')['finding_id'] for i in range(9)]
 try: comparison.build_evaluation_finding_comparison(many)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('bad upper bound')
def test_baseline_is_explicit_first_finding():
 a=make('PRIVATE_BASE'); b=make('PRIVATE_OTHER'); r=comparison.build_evaluation_finding_comparison([a['finding_id'],b['finding_id']]); require(r['baseline_finding_id']==a['finding_id'] and r['deltas'][0]['finding_id']==b['finding_id'],'baseline')
def test_count_deltas_and_state_comparisons_are_descriptive():
 a=make('PRIVATE_DELTA_A'); b=make('PRIVATE_DELTA_B',domain='model_quality',severity='blocking'); enrich(b); r=comparison.build_evaluation_finding_comparison([a['finding_id'],b['finding_id']]); d=r['deltas'][0]; require(d['count_deltas']['reproduction_attempt_count']==1 and d['count_deltas']['repair_candidate_reference_count']==1 and not d['same_issue_domain'] and not d['same_severity'],'delta')
def test_private_content_is_redacted():
 a=make('PRIVATE_COMPARE_A'); b=make('PRIVATE_COMPARE_B'); enrich(b); r=comparison.build_evaluation_finding_comparison([a['finding_id'],b['finding_id']]); encoded=json.dumps(r,sort_keys=True); require('PRIVATE_COMPARE' not in encoded and not comparison.finding_comparison_contains_private_fields(r),'privacy')
def test_digest_is_deterministic():
 a=make('PRIVATE_STABLE_A'); b=make('PRIVATE_STABLE_B'); x=comparison.build_evaluation_finding_comparison([a['finding_id'],b['finding_id']]); y=comparison.build_evaluation_finding_comparison([a['finding_id'],b['finding_id']]); require(x['comparison_digest']==y['comparison_digest'],'digest')
def test_api_get_supports_repeated_and_csv_ids():
 a=make('PRIVATE_API_A'); b=make('PRIVATE_API_B'); status,p=api_server.handle_api_get('/api/conversation/evaluation-finding-comparison',{'finding_id':[a['finding_id'],b['finding_id']]}); require(status==200 and p['data']['finding_count']==2,'repeated api'); status,p=api_server.handle_api_get('/api/conversation/evaluation-finding-comparison',{'finding_ids':[a['finding_id']+','+b['finding_id']]}); require(status==200 and p['data']['finding_count']==2,'csv api')
def test_no_ranking_priority_task_patch_or_release_authority():
 a=make('PRIVATE_AUTH_A'); b=make('PRIVATE_AUTH_B'); r=comparison.build_evaluation_finding_comparison([a['finding_id'],b['finding_id']])
 for key in ('findings_ranked','winner_selected','priority_assigned','autonomous_prioritization','statistical_significance_claimed','automatic_task_created','automatic_work_item_created','patch_generated','patch_reviewed','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','writes_state'): require(r[key] is False,f'authority {key}')
def test_comparison_does_not_mutate_findings():
 a=make('PRIVATE_MUT_A'); b=make('PRIVATE_MUT_B'); before=[finding.load_evaluation_finding_private(x['finding_id'])['revision'] for x in (a,b)]; comparison.build_evaluation_finding_comparison([a['finding_id'],b['finding_id']]); after=[finding.load_evaluation_finding_private(x['finding_id'])['revision'] for x in (a,b)]; require(before==after,'mutated')
def test_source_only_and_registration():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1089.5-bounded-repair-intake-comparison')==1 and names.index('v1089.5-bounded-repair-intake-comparison')<names.index('v1089.4-finding-triage-review'),'registration')
def test_source_immutability_surface():
 p=ROOT/'conscious_agent'/'conversation_evaluation_finding_comparison.py'; before=p.read_bytes(); a=make('PRIVATE_SRC_A'); b=make('PRIVATE_SRC_B'); comparison.build_evaluation_finding_comparison([a['finding_id'],b['finding_id']]); require(before==p.read_bytes(),'source changed')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
 for name,fn in TESTS:
  try: fn()
  except Exception as e: checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
 report={'suite':'v1089.5-bounded-repair-intake-comparison','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
