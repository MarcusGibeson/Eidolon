from __future__ import annotations
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path.insert(0,str(AGENT))
import dashboard_chat_console, post_review_development_verify as isolated_verify, release_metadata

def require(v,m):
    if not v: raise AssertionError(m)

def source(): return (AGENT/'dashboard_chat_console.py').read_text()
def test_content_free_history_state():
    s=source(); require("chatHistorySchema = 'eidolon-chat-history-v1'" in s,'history schema missing')
    for token in ('session_id','catalog_query','include_archived','catalog_offset','view_anchor_turn_id','view_anchor_offset_px','content_free:true'): require(token in s,f'history field missing {token}')
    block=s[s.index('function currentChatHistoryState'):s.index('function writeChatHistoryState')]
    for forbidden in ('draft_content','user_message','assistant_response','prompt','provider','model'): require(forbidden not in block,f'private history field {forbidden}')

def test_push_replace_and_popstate_paths():
    s=source(); require("writeChatHistoryState('push')" in s,'session switch does not push history')
    require("writeChatHistoryState('replace')" in s,'initial/catalog state does not replace history')
    require("window.addEventListener('popstate'" in s and 'restoreChatHistoryState(event.state' in s,'popstate restoration missing')
    require("querySelectorAll('[data-session-turn-id]')" in s and "candidate.dataset.sessionTurnId" in s,'history anchor restoration must use direct data-value comparison')
    require('cssEscape(anchor)' not in s,'history restoration references undefined cssEscape helper')

def test_pageshow_bfcache_restoration():
    s=source(); require("event.persisted ? 'bfcache-return' : 'history-return'" in s,'bfcache reason missing')
    require("recoverConversationLifecycle(event.persisted ? 'bfcache-return' : 'history-return'" in s,'pageshow restoration missing')
    require('initialHistoryRestorationPending' in s and "initial-history-restore" in s,'reload history state is overwritten before restoration')

def test_history_restore_does_not_push_duplicate_entry():
    s=source(); require("options.historyRestore" in s and "if (!(options && options.historyRestore)) writeChatHistoryState('push')" in s,'history restore push suppression missing')
    block=s[s.index('async function restoreChatHistoryState'):s.index("let activeOperationId = ''")]
    require("if (!sessionIdentityResolved) await reconcileActiveSessionSnapshot" in block,'initial history restore leaves the selected conversation unresolved')

def test_history_state_restores_catalog_and_anchor():
    s=source(); require('await refreshConversationOrganizer(Number(state.catalog_offset || 0))' in s,'catalog restoration missing')
    require('await switchConversationSession(target, {{ historyRestore:true }})' in s,'session restoration missing')
    require("data-session-turn-id='" in s and 'view_anchor_offset_px' in s,'reading anchor restoration missing')

def test_rendered_javascript_syntax():
    html=dashboard_chat_console.render_realtime_chat_panel(None,compact=True); expected=f"data-chat-version='{release_metadata.RUNTIME_VERSION_TAG}-{release_metadata.RUNTIME_UI_CONTRACT}'"; require(expected in html,'UI contract wrong')
    node=shutil.which('node')
    if not node:return
    cursor=0; scripts=[]
    while True:
        a=html.find('<script>',cursor)
        if a<0:break
        b=html.find('</script>',a); require(b>=0,'unclosed script'); scripts.append(html[a+8:b]); cursor=b+9
    with tempfile.TemporaryDirectory(prefix='eidolon-v1082-4-js-') as d:
        for i,script in enumerate(scripts):
            p=Path(d)/f'{i}.js'; p.write_text(script); r=subprocess.run([node,'--check',str(p)],capture_output=True,text=True,timeout=30); require(r.returncode==0,r.stderr)

def test_registration():
    require('v1082.4-browser-navigation-hardening' in {x.name for x in isolated_verify.select_suites('core')},'core registration missing')
    require((TOOLS/'release_verify.py').read_text().count('v1082_4_browser_navigation_hardening_tests.py')==1,'release registration wrong')

TESTS=[('content_free_history_state',test_content_free_history_state),('push_replace_and_popstate_paths',test_push_replace_and_popstate_paths),('pageshow_bfcache_restoration',test_pageshow_bfcache_restoration),('history_restore_does_not_push_duplicate_entry',test_history_restore_does_not_push_duplicate_entry),('history_state_restores_catalog_and_anchor',test_history_state_restores_catalog_and_anchor),('rendered_javascript_syntax',test_rendered_javascript_syntax),('registration',test_registration)]
def main():
    p=argparse.ArgumentParser(); p.add_argument('--json',action='store_true'); p.parse_args(); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1082.4-browser-navigation-hardening','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
