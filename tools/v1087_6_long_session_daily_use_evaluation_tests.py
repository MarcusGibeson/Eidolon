from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1087c-')
import api_server
import conversation_daily_evaluation as evaluation
import conversation_evaluation_long_session as mod
import conversation_sessions as sessions
import post_review_development_verify as verify

def req(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not any(part in {'__pycache__','.git','.venv','venv'} for part in p.parts) and p.suffix!='.pyc':
            h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()
def make_eval(signals):
    session=sessions.create_conversation_session(title='Long session evaluation fixture')
    item=evaluation.start_daily_evaluation(session['id'],operator_confirmed=True)
    return evaluation.record_operator_observation(item['evaluation_id'],ratings={'continuity':5,'usability':4},signals=list(signals),note='PRIVATE_LONG_SESSION_SENTINEL',expected_revision=item['revision'],operator_confirmed=True)

def test_complete_coverage_is_content_free_and_bounded():
    item=make_eval(mod.REQUIRED_LONG_SESSION_SIGNALS); report=mod.build_long_session_evaluation(item['evaluation_id'])
    req(report['coverage_status']=='complete' and report['covered_count']==report['required_count']==11,'coverage')
    req(report['initial_complete_turn_limit']==80 and report['earlier_complete_turn_limit']==120,'history bounds')
    req(report['scroll_anchor_preserved'] and report['jump_to_latest_available'] and report['narrow_layout_contained'],'ux bounds')
    req('PRIVATE_LONG_SESSION_SENTINEL' not in json.dumps(report),'private note leaked')
    req(not mod.long_session_evaluation_contains_private_fields(report),'private fields exposed')

def test_incomplete_coverage_is_honest():
    item=make_eval(['long_history','multi_tab']); report=mod.build_long_session_evaluation(item['evaluation_id'])
    req(report['coverage_status']=='incomplete','status'); req('draft_continuity' in report['missing_signals'],'missing signal')

def test_get_route_is_provider_free():
    item=make_eval(['consecutive_use']); status,payload=api_server.handle_api_get('/api/conversation/long-session-evaluation',{'evaluation_id':[item['evaluation_id']]})
    data=payload['data']; req(status==200 and payload.get('ok'),'route'); req(not data['provider_invoked'] and not data['generation_invoked'] and not data['writes_state'],'side effect')

def test_long_session_signals_are_protocol_admissible():
    from conversation_daily_evaluation_protocol import EVALUATION_SIGNALS
    req(set(mod.REQUIRED_LONG_SESSION_SIGNALS)<=set(EVALUATION_SIGNALS),'signals unavailable')

def test_registration_and_no_post_route():
    names=[s.name for s in verify.SUITES]; req(names.count('v1087.6-long-session-daily-use-evaluation')==1,'registration')
    source=(ROOT/'conscious_agent'/'api_server.py').read_text(); post=source[source.index('def handle_api_post'):]
    req('parts == ["conversation", "long-session-evaluation"]' not in post,'mutation route')

def test_build_preserves_source_tree():
    item=make_eval(['long_history']); before=tree_digest(); mod.build_long_session_evaluation(item['evaluation_id']); req(before==tree_digest(),'source mutation')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1087.6-long-session-daily-use-evaluation','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
