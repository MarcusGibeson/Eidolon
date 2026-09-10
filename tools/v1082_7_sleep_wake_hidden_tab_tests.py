from __future__ import annotations
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';TOOLS=ROOT/'tools';sys.path.insert(0,str(AGENT))
import conversation_lifecycle_recovery as lifecycle,dashboard_chat_console,post_review_development_verify as isolated_verify

def require(v,m):
    if not v:raise AssertionError(m)

def test_visible_wake_reconciles_without_generation():
    value=lifecycle.lifecycle_recovery_plan('sleep-resume',hidden=False,online=True,owns_control=True,active_operation_id='conversation_x')
    require(value['coordination_action']=='heartbeat' and value['reconcile_session'],'visible wake plan wrong')
    require(value['resume_operation_poll'] and value['active_operation_id']=='conversation_x','accepted operation poll not resumed')
    require(value['automatic_generation_retry'] is False and value['provider_request_replayed'] is False,'wake replays provider')

def test_hidden_tab_does_not_reconcile_or_poll():
    value=lifecycle.lifecycle_recovery_plan('sleep-resume',hidden=True,online=True,owns_control=False,active_operation_id='conversation_x')
    require(value['coordination_action']=='register','follower coordination plan wrong')
    require(not value['reconcile_session'] and not value['resume_operation_poll'] and not value['active_operation_id'],'hidden tab performs foreground recovery')

def test_offline_focus_waits_for_network():
    value=lifecycle.lifecycle_recovery_plan('focus-recovery',hidden=False,online=False,owns_control=True,active_operation_id='conversation_x')
    require(not value['reconcile_session'] and not value['resume_operation_poll'],'offline focus performs network recovery')

def test_unknown_reason_is_bounded():
    value=lifecycle.lifecycle_recovery_plan('invented-event',hidden=False,online=True,owns_control=False)
    require(value['reason']=='history-return' and value['single_flight_required'],'unknown lifecycle reason not bounded')

def test_session_snapshot_exposes_content_free_plan():
    source=(AGENT/'dashboard_chat_console.py').read_text()
    require('"lifecycle_recovery": lifecycle_recovery_plan(' in source,'session snapshot omits lifecycle contract')
    require(not lifecycle.lifecycle_plan_contains_private_fields(lifecycle.lifecycle_recovery_plan('history-return',hidden=False,online=True,owns_control=False)),'lifecycle plan leaks private fields')

def test_browser_uses_one_single_flight_path():
    source=(AGENT/'dashboard_chat_console.py').read_text()
    require('let lifecycleRecoveryPromise = null;' in source and 'let lifecycleRecoveryGeneration = 0;' in source,'single-flight state missing')
    require('async function recoverConversationLifecycle(reason, options)' in source,'canonical lifecycle function missing')
    require('if (lifecycleRecoveryPromise) return lifecycleRecoveryPromise;' in source,'duplicate lifecycle recoveries not coalesced')
    require("recoverConversationLifecycle('sleep-resume')" in source and "recoverConversationLifecycle('offline-recovery')" in source and "recoverConversationLifecycle('focus-recovery')" in source,'lifecycle events not consolidated')

def test_pageshow_and_operation_poll_do_not_submit():
    source=(AGENT/'dashboard_chat_console.py').read_text()
    block=source[source.index('async function recoverConversationLifecycle'):source.index('async function confirmConversationControl')]
    require('pollOperation(activeOperationId' in block,'active operation poll not resumed')
    for forbidden in ('form.requestSubmit','start_dashboard_chat_operation','/api/dashboard-chat/stream','persistNonAcceptanceEvidence'):
        require(forbidden not in block,f'lifecycle recovery contains submission path {forbidden}')
    require("event.persisted ? 'bfcache-return' : 'history-return'" in source,'pageshow not consolidated')

def test_rendered_javascript_syntax():
    html=dashboard_chat_console.render_realtime_chat_panel(None,compact=True);node=shutil.which('node')
    if not node:return
    with tempfile.TemporaryDirectory(prefix='eidolon-v1082-7-js-') as d:
        pos=0;i=0
        while True:
            a=html.find('<script>',pos)
            if a<0:break
            b=html.find('</script>',a);require(b>=0,'unclosed script');p=Path(d)/f'{i}.js';p.write_text(html[a+8:b]);r=subprocess.run([node,'--check',str(p)],capture_output=True,text=True,timeout=30);require(r.returncode==0,r.stderr);pos=b+9;i+=1

def test_registration():
    require('v1082.7-sleep-wake-hidden-tab' in {x.name for x in isolated_verify.select_suites('core')},'core registration missing')
    require((TOOLS/'release_verify.py').read_text().count('v1082_7_sleep_wake_hidden_tab_tests.py')==1,'release registration wrong')

TESTS=[('visible_wake_reconciles_without_generation',test_visible_wake_reconciles_without_generation),('hidden_tab_does_not_reconcile_or_poll',test_hidden_tab_does_not_reconcile_or_poll),('offline_focus_waits_for_network',test_offline_focus_waits_for_network),('unknown_reason_is_bounded',test_unknown_reason_is_bounded),('session_snapshot_exposes_content_free_plan',test_session_snapshot_exposes_content_free_plan),('browser_uses_one_single_flight_path',test_browser_uses_one_single_flight_path),('pageshow_and_operation_poll_do_not_submit',test_pageshow_and_operation_poll_do_not_submit),('rendered_javascript_syntax',test_rendered_javascript_syntax),('registration',test_registration)]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1082.7-sleep-wake-hidden-tab','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
