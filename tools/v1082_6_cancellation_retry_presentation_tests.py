from __future__ import annotations
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path.insert(0,str(AGENT))
import conversation_turn_presentation as presentation, dashboard_chat_console, post_review_development_verify as isolated_verify

def require(v,m):
    if not v: raise AssertionError(m)

def marker(state='running',**extra):
    value={'operation_id':'conversation_20260720T010101_'+'a'*12,'session_id':'conversation_session_20260720T010101_'+'b'*10,'accepted_at':'2026-07-20T01:01:01Z','public_state':state};value.update(extra);return value

def test_running_and_cancelling_vocabulary():
    running=presentation.build_turn_presentation(marker())
    cancelling=presentation.build_turn_presentation(marker(cancellation_requested=True))
    require(running['state']=='accepted_running' and running['action']=='reconcile','running vocabulary wrong')
    require(cancelling['state']=='accepted_cancelling' and 'exact operation' in cancelling['detail'],'cancelling vocabulary wrong')

def test_completed_and_late_completion_memory_boundary():
    done=presentation.build_turn_presentation(marker('completed'),turn={'success':True,'completion_state':'completed'})
    late=presentation.build_turn_presentation(marker('completed',client_disconnected=True),turn={'success':True,'completion_state':'completed'})
    require(done['state']=='accepted_completed' and done['memory_commit_allowed'],'completed presentation wrong')
    require(late['state']=='accepted_completed_late' and late['memory_commit_allowed'],'late completion presentation wrong')

def test_cancelled_has_no_memory_commit():
    value=presentation.build_turn_presentation(marker('cancelled'),turn={'success':False,'completion_state':'cancelled'})
    require(value['state']=='accepted_cancelled' and not value['memory_commit_allowed'],'cancelled memory boundary wrong')

def test_failed_recovery_is_explicit_only():
    value=presentation.build_turn_presentation(marker('failed'),turn={'completion_state':'failed'},recovery={'retryable':True,'acceptance_proven':True})
    require(value['state']=='accepted_recovery_available' and value['action']=='linked_recovery','recovery vocabulary wrong')
    require(value['automatic_retry'] is False and value['automatic_resend'] is False,'recovery became automatic')

def test_uncertain_accepted_never_resends():
    value=presentation.build_turn_presentation(marker('uncertain'))
    require(value['state']=='accepted_uncertain' and value['accepted'],'uncertain accepted state wrong')
    require(value['explicit_resend_allowed'] is False and value['action']=='reconcile','accepted uncertain turn can resend')

def test_proven_unaccepted_preserves_draft():
    evidence={'non_acceptance_proven':True}
    value=presentation.build_turn_presentation(None,non_acceptance=evidence)
    claimed=presentation.build_turn_presentation(None,non_acceptance=evidence,resend_lineage={'resend_acceptance_key':'fresh-key'})
    require(value['state']=='proven_unaccepted' and value['draft_preserved'] and value['explicit_resend_allowed'],'unaccepted state wrong')
    require(claimed['state']=='proven_unaccepted_claimed','claimed resend state wrong')

def test_content_free_no_synthetic_response():
    value=presentation.build_turn_presentation(marker('failed'))
    require(not presentation.turn_presentation_contains_private_fields(value),'presentation leaked private fields')
    require(value['synthetic_assistant_response'] is False and value['provider_request_replayed'] is False,'synthetic/replay boundary wrong')

def test_operation_status_exposes_canonical_contract():
    source=(AGENT/'dashboard_chat_console.py').read_text()
    require('"turn_presentation": build_turn_presentation(' in source,'operation status omits canonical turn presentation')
    require('function applyTurnPresentation(presentation)' in source,'browser does not consume canonical turn presentation')
    require('if (!applyTurnPresentation(payload.turn_presentation || null))' in source,'legacy fallback does not defer to canonical contract')

def test_rendered_javascript_syntax():
    html=dashboard_chat_console.render_realtime_chat_panel(None,compact=True)
    node=shutil.which('node')
    if not node:return
    with tempfile.TemporaryDirectory(prefix='eidolon-v1082-6-js-') as d:
        pos=0;i=0
        while True:
            a=html.find('<script>',pos)
            if a<0:break
            b=html.find('</script>',a);require(b>=0,'unclosed script')
            p=Path(d)/f'{i}.js';p.write_text(html[a+8:b]);r=subprocess.run([node,'--check',str(p)],capture_output=True,text=True,timeout=30);require(r.returncode==0,r.stderr);pos=b+9;i+=1

def test_registration_and_metadata():
    require('v1082.6-cancellation-retry-presentation' in {x.name for x in isolated_verify.select_suites('core')},'core registration missing')
    require((TOOLS/'release_verify.py').read_text().count('v1082_6_cancellation_retry_presentation_tests.py')==1,'release registration wrong')
    import release_metadata
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split(".")) >= (1082, 8), "runtime regressed below v1082.8")

TESTS=[('running_and_cancelling_vocabulary',test_running_and_cancelling_vocabulary),('completed_and_late_completion_memory_boundary',test_completed_and_late_completion_memory_boundary),('cancelled_has_no_memory_commit',test_cancelled_has_no_memory_commit),('failed_recovery_is_explicit_only',test_failed_recovery_is_explicit_only),('uncertain_accepted_never_resends',test_uncertain_accepted_never_resends),('proven_unaccepted_preserves_draft',test_proven_unaccepted_preserves_draft),('content_free_no_synthetic_response',test_content_free_no_synthetic_response),('operation_status_exposes_canonical_contract',test_operation_status_exposes_canonical_contract),('rendered_javascript_syntax',test_rendered_javascript_syntax),('registration_and_metadata',test_registration_and_metadata)]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1082.6-cancellation-retry-presentation','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
