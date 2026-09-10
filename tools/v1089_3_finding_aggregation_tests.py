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
import conversation_evaluation_finding_aggregation as aggregation
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def make(title,domain='interface',severity='major'):
 s=create_conversation_session(title,select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); return finding.create_evaluation_finding(finding_title=title,finding_details='PRIVATE_AGG_DETAILS',issue_domain=domain,severity=severity,evaluation_id=e['evaluation_id'],operator_confirmed=True)

def test_empty_aggregation_is_bounded_and_read_only():
 r=aggregation.build_evaluation_finding_aggregation(); require(r['finding_count']==0 and r['maximum_findings']==256 and r['read_only'] and not r['writes_state'],'empty contract')
def test_counts_findings_reproduction_and_repair_states():
 f=make('PRIVATE_AGG_ONE'); rr=repro.record_reproduction_attempt(f['finding_id'],outcome='reproduced',environment_kind='same_environment',environment_label='PRIVATE_ENV',note='PRIVATE_NOTE',expected_revision=f['revision'],operator_confirmed=True); repairs.add_repair_candidate_reference(f['finding_id'],reference_kind='test_case',reference_value='PRIVATE_REF',expected_revision=rr['finding_revision'],operator_confirmed=True); r=aggregation.build_evaluation_finding_aggregation(); require(r['finding_count']==1 and r['reproducibility_counts']['confirmed']==1 and r['repair_reference_state_counts']['proposed']==1,'counts wrong')
def test_filters_are_explicit_and_bounded():
 a=make('PRIVATE_FILTER_A'); b=make('PRIVATE_FILTER_B',domain='model_quality',severity='blocking'); r=aggregation.build_evaluation_finding_aggregation(evaluation_id=a['evaluation_id'],limit=1); require(r['finding_count']==1 and r['findings'][0]['finding_id']==a['finding_id'] and r['maximum_findings']==256,'filter wrong')
def test_private_content_is_not_returned_or_inspected():
 make('PRIVATE_AGG_MARKER'); r=aggregation.build_evaluation_finding_aggregation(); encoded=json.dumps(r,sort_keys=True); require('PRIVATE_AGG_MARKER' not in encoded and 'PRIVATE_AGG_DETAILS' not in encoded,'private leak'); require(not aggregation.finding_aggregation_contains_private_fields(r) and not r['private_finding_content_inspected'],'privacy contract')
def test_digest_is_deterministic():
 make('PRIVATE_DIGEST'); a=aggregation.build_evaluation_finding_aggregation(); b=aggregation.build_evaluation_finding_aggregation(); require(a['aggregation_digest']==b['aggregation_digest'],'digest unstable')
def test_api_get_route():
 f=make('PRIVATE_API_AGG'); status,payload=api_server.handle_api_get('/api/conversation/evaluation-finding-aggregation',{'evaluation_id':[f['evaluation_id']]}); require(status==200 and payload['data']['finding_count']==1 and payload['data']['findings'][0]['finding_id']==f['finding_id'],'api failed')
def test_no_priority_task_patch_or_release_authority():
 make('PRIVATE_AUTH_AGG'); r=aggregation.build_evaluation_finding_aggregation()
 for key in ('findings_ranked','priority_assigned','autonomous_prioritization','automatic_task_created','automatic_work_item_created','patch_generated','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','writes_state'): require(r[key] is False,f'authority {key}')
def test_source_only_and_registration():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1089.3-finding-aggregation')==1 and names.index('v1089.3-finding-aggregation')<names.index('v1089.2-repair-candidate-references'),'registration')
def test_source_immutability_surface():
 before=(ROOT/'conscious_agent'/'conversation_evaluation_finding_aggregation.py').read_bytes(); aggregation.build_evaluation_finding_aggregation(); require(before==(ROOT/'conscious_agent'/'conversation_evaluation_finding_aggregation.py').read_bytes(),'source changed')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
 for name,fn in TESTS:
  try: fn()
  except Exception as e: checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
 report={'suite':'v1089.3-finding-aggregation','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
