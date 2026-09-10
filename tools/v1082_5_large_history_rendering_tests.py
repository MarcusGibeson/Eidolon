from __future__ import annotations
import argparse,json,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path.insert(0,str(AGENT))
import conversation_sessions as sessions, dashboard_chat_console, post_review_development_verify as isolated_verify

def require(v,m):
    if not v:raise AssertionError(m)
class Store:
    def __init__(self):
        self.t=tempfile.TemporaryDirectory(prefix='eidolon-v1082-5-'); r=Path(self.t.name)/'sessions'; self.o=(sessions.CONVERSATION_SESSIONS_DIR,sessions.ACTIVE_SESSION_FILE,sessions.CONVERSATION_DRAFTS_DIR,sessions.CONVERSATION_DRAFT_CONFLICTS_DIR); sessions.CONVERSATION_SESSIONS_DIR=r;sessions.ACTIVE_SESSION_FILE=r/'active_session.json';sessions.CONVERSATION_DRAFTS_DIR=r/'drafts';sessions.CONVERSATION_DRAFT_CONFLICTS_DIR=r/'conflicts'
    def close(self):(setattr(sessions,'CONVERSATION_SESSIONS_DIR',self.o[0]),setattr(sessions,'ACTIVE_SESSION_FILE',self.o[1]),setattr(sessions,'CONVERSATION_DRAFTS_DIR',self.o[2]),setattr(sessions,'CONVERSATION_DRAFT_CONFLICTS_DIR',self.o[3]));self.t.cleanup()
def seed(n=250):
    st=Store(); sid=sessions.create_conversation_session('Long history')['id']
    for i in range(n):sessions.append_conversation_turn(sid,turn_id=f'turn-{i:04d}',user_message=f'user {i}',assistant_response=f'assistant {i}',completion_state='completed',success=True)
    return st,sid

def test_latest_window_is_bounded():
    st,sid=seed()
    try:
        w=sessions.conversation_session_turn_window(sid,limit=80); require(w['shown']==80 and w['total_turns']==250 and w['has_older'],'latest window wrong'); require(w['oldest_turn_id']=='turn-0170' and w['newest_turn_id']=='turn-0249','latest boundaries wrong')
    finally:st.close()
def test_earlier_windows_do_not_overlap():
    st,sid=seed()
    try:
        latest=sessions.conversation_session_turn_window(sid,limit=80); earlier=sessions.conversation_session_turn_window(sid,before_turn_id=latest['oldest_turn_id'],limit=80)
        a={t['id'] for t in latest['turns']}; b={t['id'] for t in earlier['turns']}; require(not a&b,'windows overlap'); require(earlier['newest_turn_id']=='turn-0169' and earlier['oldest_turn_id']=='turn-0090','earlier boundaries wrong')
    finally:st.close()
def test_missing_anchor_is_rejected():
    st,sid=seed(3)
    try:
        try:sessions.conversation_session_turn_window(sid,before_turn_id='missing',limit=2)
        except ValueError:pass
        else:raise AssertionError('missing anchor accepted')
    finally:st.close()
def test_rendered_window_contains_only_requested_turns():
    st,sid=seed(100)
    try:
        r=dashboard_chat_console.dashboard_chat_session_window(sid,before_turn_id='turn-0080',limit=10); require(r['shown']==10 and r['has_older'],'render metadata wrong'); require('user 70' in r['transcript_html'] and 'user 80' not in r['transcript_html'],'rendered window range wrong'); require(r['receipts_included'] is False,'receipt boundary missing')
    finally:st.close()
def test_large_window_performance_is_bounded():
    st,sid=seed(600)
    try:
        start=time.perf_counter(); w=sessions.conversation_session_turn_window(sid,limit=80); elapsed=time.perf_counter()-start; require(w['shown']==80,'bounded window count wrong'); require(elapsed<2.0,f'window too slow {elapsed:.3f}s')
    finally:st.close()
def test_browser_loads_earlier_without_replacing_existing_log():
    s=(AGENT/'dashboard_chat_console.py').read_text(); require("/api/dashboard-chat/session-window?" in s,'window endpoint not used'); require('log.insertBefore(fragment, log.firstChild)' in s,'older history does not prepend'); require('log.scrollTop += Math.max(0, log.scrollHeight - priorHeight)' in s,'scroll position not preserved')
def test_snapshot_is_bounded_and_endpoint_registered():
    s=(AGENT/'dashboard_chat_console.py').read_text(); require('conversation_session_turn_window(resolved_session_id, limit=80)' in s,'snapshot not bounded'); d=(AGENT/'dashboard.py').read_text(); require('if path == "/api/dashboard-chat/session-window"' in d,'window endpoint missing')
def test_narrow_layout_and_privacy():
    styles=dashboard_chat_console.COMPANION_CHAT_STYLES; require('.chat-history-window-controls' in styles and 'overflow-wrap:anywhere' in styles,'history controls not narrow-safe'); files=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]; require(not any(x.startswith('data/conversation_sessions/') for x in files),'runtime sessions packaged')
def test_registration():
    require('v1082.5-large-history-rendering' in {x.name for x in isolated_verify.select_suites('core')},'core registration missing'); require((TOOLS/'release_verify.py').read_text().count('v1082_5_large_history_rendering_tests.py')==1,'release registration wrong')
TESTS=[('latest_window_is_bounded',test_latest_window_is_bounded),('earlier_windows_do_not_overlap',test_earlier_windows_do_not_overlap),('missing_anchor_is_rejected',test_missing_anchor_is_rejected),('rendered_window_contains_only_requested_turns',test_rendered_window_contains_only_requested_turns),('large_window_performance_is_bounded',test_large_window_performance_is_bounded),('browser_loads_earlier_without_replacing_existing_log',test_browser_loads_earlier_without_replacing_existing_log),('snapshot_is_bounded_and_endpoint_registered',test_snapshot_is_bounded_and_endpoint_registered),('narrow_layout_and_privacy',test_narrow_layout_and_privacy),('registration',test_registration)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');p.parse_args();checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1082.5-large-history-rendering','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
