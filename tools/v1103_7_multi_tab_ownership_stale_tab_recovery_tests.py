from __future__ import annotations
import json, sys, tempfile, uuid, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
import conversation_tab_coordination as tabs
from messaging_resilience import build_tab_recovery_state

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)

def isolated():
    t=tempfile.TemporaryDirectory(); root=Path(t.name)
    tabs.TAB_COORDINATION_DIR=root; tabs.TAB_COORDINATION_STATE_FILE=root/'state.json'; tabs.TAB_COORDINATION_MUTATION_DIR=root/'mutations'
    return t

def identities(): return str(uuid.uuid4()),str(uuid.uuid4()),str(uuid.uuid4()),str(uuid.uuid4())

def test_follower_cannot_take_over_live_visible_owner_automatically():
    with isolated():
        tab1,tab2,browser1,browser2=identities(); a=tabs.register_dashboard_tab(tab1,browser1,instance_nonce='instance-owner-0001',now_epoch=0,lease_seconds=10)
        b=tabs.register_dashboard_tab(tab2,browser2,instance_nonce='instance-follow-0002',now_epoch=1,lease_seconds=10)
        require(a['is_owner'] and not b['is_owner'] and b['owner_present'],(a,b))
        r=build_tab_recovery_state(b); require(r['status']=='following' and r['explicit_transfer_required'] and not r['automatic_takeover'],r)

def test_expired_owner_allows_explicit_recovery_and_stale_heartbeat_loses():
    with isolated():
        tab1,tab2,browser1,browser2=identities(); a=tabs.register_dashboard_tab(tab1,browser1,instance_nonce='instance-owner-0001',now_epoch=0,lease_seconds=3)
        snap=tabs.coordination_snapshot(tab_id=tab2,now_epoch=5); require(not snap['owner_present'],snap)
        acquired=tabs.acquire_dashboard_tab_ownership(tab2,browser2,instance_nonce='instance-follow-0002',visible=True,force=True,now_epoch=5,lease_seconds=10)
        stale=tabs.heartbeat_dashboard_tab(tab1,a['lease_token'],instance_nonce='instance-owner-0001',now_epoch=6)
        require(acquired['is_owner'] and not stale['is_owner'],(acquired,stale))

def test_duplicated_tab_identity_is_fenced():
    with isolated():
        tab1,_,browser1,_=identities(); tabs.register_dashboard_tab(tab1,browser1,instance_nonce='instance-owner-0001',now_epoch=0)
        conflict=tabs.register_dashboard_tab(tab1,browser1,instance_nonce='instance-duplicate-2',now_epoch=1)
        report=build_tab_recovery_state(conflict)
        require(report['renew_tab_identity'] and not report['stale_tab_may_send'],report)

def test_owner_and_available_recovery_states_are_content_free():
    owner=build_tab_recovery_state({'status':'ownership_retained','owner_present':True,'is_owner':True})
    open_state=build_tab_recovery_state({'status':'ownership_expired','owner_present':False,'is_owner':False})
    require(owner['status']=='owner' and owner['stale_tab_may_send'],owner)
    require(open_state['take_control_available'] and open_state['content_free'],open_state)

def test_first_use_shell_has_explicit_takeover_periodic_heartbeat_and_stale_fencing():
    src=(AGENT/'dashboard_first_use.py').read_text()
    for token in ('take-control','takeConversationControl','heartbeatOwnership','setInterval(heartbeatOwnership,5000)','stale or follower tab never sends, cancels, retries, or switches automatically'):
        require(token in src,token)

def test_rendered_first_use_javascript_is_syntactically_valid():
    from dashboard_first_use import render_first_use_shell
    html=render_first_use_shell(); match=re.search(r'<script>(.*?)</script>',html,re.S); require(match is not None,'script missing')
    with tempfile.TemporaryDirectory() as raw:
        path=Path(raw)/'first-use.js'; path.write_text(match.group(1))
        try: result=subprocess.run(['node','--check',str(path)],text=True,capture_output=True,timeout=30)
        except FileNotFoundError: return
        require(result.returncode==0,result.stderr)

def test_registration_exactly_once():
    src=(ROOT/'tools/post_review_development_verify.py').read_text(); require(src.count('"tools/v1103_7_multi_tab_ownership_stale_tab_recovery_tests.py"')==1,'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.7-multi-tab-ownership-stale-tab-recovery','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
