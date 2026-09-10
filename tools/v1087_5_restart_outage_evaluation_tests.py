from __future__ import annotations
import argparse,hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1087b-')
import conversation_sessions as sessions
import conversation_daily_evaluation as evaluation
import post_review_development_verify as verify
def req(v,m):
 if not v: raise AssertionError(m)
def make_eval(signals=(),domain='none',severity='none',repro=False,state='completed'):
 s=sessions.create_conversation_session(title='Evaluation fixture'); e=evaluation.start_daily_evaluation(s['id'],operator_confirmed=True); e=evaluation.record_operator_observation(e['evaluation_id'],ratings={'continuity':4,'recovery':4},signals=list(signals),issue_domain=domain,severity=severity,reproducible=repro,note='PRIVATE_SENTINEL',expected_revision=e['revision'],operator_confirmed=True); return evaluation.finish_daily_evaluation(e['evaluation_id'],state=state,expected_revision=e['revision'],operator_confirmed=True)
import api_server
import conversation_evaluation_recovery_scenarios as mod
def test_complete_recovery_coverage():
 e=make_eval(mod.REQUIRED_RECOVERY_SIGNALS); r=mod.build_restart_outage_evaluation(e['evaluation_id']); req(r['coverage_status']=='complete' and r['covered_count']==7,'coverage')
def test_incomplete_is_honest_and_no_replay():
 e=make_eval(['provider_outage']); r=mod.build_restart_outage_evaluation(e['evaluation_id']); req(r['coverage_status']=='incomplete' and 'provider_return' in r['missing_signals'],'missing'); req(not r['automatic_replay_allowed'] and not r['automatic_resend_allowed'],'replay')
def test_route_provider_free():
 e=make_eval(['restart_resume']); st,p=api_server.handle_api_get('/api/conversation/restart-outage-evaluation',{'evaluation_id':[e['evaluation_id']]}); d=p['data']; req(st==200 and not d['provider_invoked'] and not d['generation_invoked'],'route')
def test_registration_and_authority():
 names=[x.name for x in verify.SUITES]; req(names.count('v1087.5-restart-outage-evaluation')==1,'registration'); src=(ROOT/'conscious_agent'/'conversation_evaluation_recovery_scenarios.py').read_text(); req('promotion_performed' not in src and 'approval_granted' not in src,'authority')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true');c=[];p=0
 for n,f in TESTS:
  try:f()
  except Exception as e:c.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else:p+=1;c.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1087.5-restart-outage-evaluation','ok':p==len(TESTS),'status':'pass' if p==len(TESTS) else 'fail','passed':p,'total':len(TESTS),'checks':c};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
