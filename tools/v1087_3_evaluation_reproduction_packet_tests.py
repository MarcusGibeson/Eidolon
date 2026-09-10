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
import conversation_evaluation_reproduction as mod
def test_packet_is_content_free():
 e=make_eval(['restart_resume'],'interface','major',True); p=mod.build_reproduction_packet(e['evaluation_id']); req(p['reproducible_observation_count']==1,'repro lost'); req('PRIVATE_SENTINEL' not in json.dumps(p),'note leaked'); req(not mod.reproduction_packet_contains_private_fields(p),'private key')
def test_packet_is_deterministic_and_read_only():
 e=make_eval(); a=mod.build_reproduction_packet(e['evaluation_id']); b=mod.build_reproduction_packet(e['evaluation_id']); req(a['packet_digest']==b['packet_digest'],'unstable'); req(not a['provider_invoked'] and not a['writes_state'],'side effect')
def test_route_registered():
 e=make_eval(); st,p=api_server.handle_api_get('/api/conversation/evaluation-reproduction',{'evaluation_id':[e['evaluation_id']]}); req(st==200 and p['data']['type']=='desktop_alpha_evaluation_reproduction_packet','route')
def test_registration():
 names=[x.name for x in verify.SUITES]; req(names.count('v1087.3-evaluation-reproduction-packet')==1,'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true');c=[];p=0
 for n,f in TESTS:
  try:f()
  except Exception as e:c.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else:p+=1;c.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1087.3-evaluation-reproduction-packet','ok':p==len(TESTS),'status':'pass' if p==len(TESTS) else 'fail','passed':p,'total':len(TESTS),'checks':c};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
