from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_reproducibility as repro
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def make():
 s=create_conversation_session('Repro session',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); return finding.create_evaluation_finding(finding_title='PRIVATE_REPRO_FINDING',finding_details='private',issue_domain='provider_transport',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True)
def add(f,**kw): return repro.record_reproduction_attempt(f['finding_id'],outcome=kw.get('outcome','reproduced'),environment_kind=kw.get('environment_kind','same_environment'),environment_label=kw.get('environment_label','PRIVATE_ENVIRONMENT_LABEL'),note=kw.get('note','PRIVATE_REPRO_NOTE'),evidence_digest=kw.get('evidence_digest','a'*64),expected_revision=kw.get('expected_revision',f['revision']),operator_confirmed=kw.get('operator_confirmed',True))

def test_attempt_requires_confirmation_and_exact_revision():
 f=make()
 for confirmed,rev in [(False,f['revision']),(True,None),(True,f['revision']-1)]:
  try: add(f,operator_confirmed=confirmed,expected_revision=rev)
  except finding.EvaluationFindingError: pass
  else: raise AssertionError('unguarded attempt accepted')

def test_supported_outcome_and_environment_are_validated():
 f=make()
 for outcome,env in [('imaginary','same_environment'),('reproduced','moon')]:
  try: add(f,outcome=outcome,environment_kind=env)
  except finding.EvaluationFindingError: pass
  else: raise AssertionError('invalid reproduction token accepted')

def test_attempt_is_explicit_and_updates_status():
 f=make(); result=add(f); require(result['attempt_count']==1 and result['reproducibility_status']=='confirmed','status wrong')

def test_private_environment_and_note_are_digest_only_publicly():
 f=make(); result=add(f); encoded=json.dumps(result,sort_keys=True); require('PRIVATE_ENVIRONMENT_LABEL' not in encoded and 'PRIVATE_REPRO_NOTE' not in encoded,'private reproduction leaked'); require(result['attempts'][0]['environment_label_digest'] and result['attempts'][0]['note_digest'],'digests absent')

def test_private_record_retains_attempt_content():
 f=make(); add(f); private=finding.load_evaluation_finding_private(f['finding_id']); row=private['reproduction_attempts'][0]; require(row['private_environment_label']=='PRIVATE_ENVIRONMENT_LABEL' and row['private_note']=='PRIVATE_REPRO_NOTE','private attempt missing')

def test_duplicate_attempt_is_idempotent_without_revision_advance():
 f=make(); first=add(f); duplicate=repro.record_reproduction_attempt(f['finding_id'],outcome='reproduced',environment_kind='same_environment',environment_label='PRIVATE_ENVIRONMENT_LABEL',note='PRIVATE_REPRO_NOTE',evidence_digest='a'*64,expected_revision=first['finding_revision'],operator_confirmed=True); require(duplicate['duplicate_attempt'] and duplicate['attempt_count']==1 and duplicate['finding_revision']==first['finding_revision'],'duplicate mutated')

def test_mixed_status_is_reported_without_statistical_claim():
 f=make(); first=add(f); second=repro.record_reproduction_attempt(f['finding_id'],outcome='not_reproduced',environment_kind='clean_restart',environment_label='',note='',evidence_digest='',expected_revision=first['finding_revision'],operator_confirmed=True); require(second['reproducibility_status']=='mixed' and second['outcome_counts']['not_reproduced']==1,'mixed status wrong')

def test_attempt_removal_is_explicit():
 f=make(); first=add(f); attempt=first['attempts'][0]['attempt_id']; removed=repro.remove_reproduction_attempt(f['finding_id'],attempt,expected_revision=first['finding_revision'],operator_confirmed=True); require(removed['attempt_count']==0 and removed['reproducibility_status']=='not_reviewed','remove failed')

def test_evidence_digest_validation():
 f=make()
 try: add(f,evidence_digest='not-sha')
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('bad evidence digest accepted')

def test_api_get_and_post_routes():
 f=make(); status,payload=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'record_reproduction_attempt','finding_id':f['finding_id'],'outcome':'inconclusive','environment_kind':'other','expected_revision':f['revision'],'operator_confirmed':True},{}); require(status==200 and payload['data']['attempt_count']==1,'api post failed'); status,payload=api_server.handle_api_get('/api/conversation/evaluation-finding-reproducibility',{'finding_id':[f['finding_id']]}); require(status==200 and payload['data']['attempt_count']==1,'api get failed')

def test_no_automatic_rerun_provider_or_task_authority():
 f=make(); result=add(f)
 for key in ('automatic_rerun','provider_invoked','automatic_replay','automatic_resend','automatic_task_created','patch_generated','release_certified','writes_state'): require(result[key] is False,f'authority escalated {key}')

def test_source_only_and_registration():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1089.1-finding-reproducibility-review')==1 and names.index('v1089.1-finding-reproducibility-review')<names.index('v1089.0-evaluation-finding-intake'),'registration wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
 for name,fn in TESTS:
  try: fn()
  except Exception as e: checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
 report={'suite':'v1089.1-finding-reproducibility-review','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
