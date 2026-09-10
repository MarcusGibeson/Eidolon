from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1087c-')
import api_server
import conversation_daily_evaluation as evaluation
import conversation_evaluation_console as mod
import conversation_sessions as sessions
import dashboard
import post_review_development_verify as verify

def req(v,m):
    if not v: raise AssertionError(m)
def make_eval():
    session=sessions.create_conversation_session(title='Console fixture')
    item=evaluation.start_daily_evaluation(session['id'],operator_confirmed=True)
    item=evaluation.record_operator_observation(item['evaluation_id'],ratings={'tone':4},signals=['provider_outage','long_history'],note='PRIVATE_CONSOLE_SENTINEL',expected_revision=item['revision'],operator_confirmed=True)
    return session,item

def test_console_state_without_selection_is_read_only():
    report=mod.build_evaluation_console_state(); req(report['selection_status']=='none_selected','selection'); req(report['read_routes_only'] and not report['writes_state'] and not report['provider_invoked'],'boundary')

def test_console_state_combines_redacted_evidence():
    session,item=make_eval(); report=mod.build_evaluation_console_state(evaluation_id=item['evaluation_id'],session_id=session['id'])
    req(report['selection_status']=='available' and report['selected_evaluation']['evaluation_id']==item['evaluation_id'],'selection')
    req(report['reproduction'] and report['restart_outage'] and report['long_session'],'evidence missing')
    req('PRIVATE_CONSOLE_SENTINEL' not in json.dumps(report),'private note leaked')

def test_get_route_is_provider_free():
    session,item=make_eval(); status,payload=api_server.handle_api_get('/api/conversation/evaluation-console',{'evaluation_id':[item['evaluation_id']],'session_id':[session['id']]})
    data=payload['data']; req(status==200 and payload.get('ok'),'route'); req(not data['provider_invoked'] and not data['generation_invoked'],'provider')

def test_dashboard_console_has_explicit_controls_and_narrow_layout():
    html=dashboard.render_daily_evaluation_console()
    for token in ('data-evaluation-console-version=\'v1087.7\'','/api/dashboard-chat/daily-evaluation','operator_confirmed: true','window.confirm','/api/conversation/evaluation-review-export'):
        req(token in html,f'missing {token}')
    req('@media(max-width:820px)' in html and 'grid-template-columns:1fr' in html,'narrow layout')
    req('title=' not in html[html.index("data-evaluation-console-version='v1087.7'"):html.index("</script>",html.index("data-evaluation-console-version='v1087.7'"))],'native title tooltip')

def test_console_javascript_syntax():
    html=dashboard.render_daily_evaluation_console(); scripts=re.findall(r'<script>(.*?)</script>',html,re.S)
    script=next((x for x in scripts if '/api/conversation/evaluation-review-export' in x),None); req(script is not None,'script missing')
    path=Path(tempfile.mkdtemp())/'console.js'; path.write_text(script,encoding='utf-8')
    result=subprocess.run(['node','--check',str(path)],capture_output=True,text=True,timeout=30); req(result.returncode==0,result.stderr)

def test_console_route_and_registration():
    source=(ROOT/'conscious_agent'/'dashboard.py').read_text(); req('elif path == "/daily-evaluation-console"' in source,'dashboard route')
    names=[s.name for s in verify.SUITES]; req(names.count('v1087.7-desktop-alpha-evaluation-console')==1,'registration')

def test_mutations_still_require_operator_confirmation():
    session=sessions.create_conversation_session(title='Confirmation fixture')
    try:evaluation.start_daily_evaluation(session['id'],operator_confirmed=False)
    except evaluation.DailyEvaluationError:pass
    else:raise AssertionError('confirmation bypassed')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1087.7-desktop-alpha-evaluation-console','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
