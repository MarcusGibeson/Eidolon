from __future__ import annotations
import argparse, hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for value in (AGENT,ROOT):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
from messaging_reliability_checkpoint import build_messaging_reliability_checkpoint, checkpoint_contains_private_fields

def require(condition:bool,detail:Any='requirement failed')->None:
    if not condition: raise AssertionError(detail)
def _verification(ok:bool=True,*,passed:int=184,total:int=184)->dict[str,Any]: return {'ok':ok,'passed':passed,'total':total}
def _native(ok:bool=True)->dict[str,Any]: return {'ok':ok,'native_windows':True,'status':'pass' if ok else 'failed','automatic_promotion':False,'automatic_certification':False,'approval_granted':False,'release_authorized':False,'provider_configuration_changed':False,'model_configuration_changed':False}
def _provider(status:str='unavailable')->dict[str,Any]: return {'status':status,'return_proven':status in {'ready','returned'},'accepted_turn_replayed':False,'provider_request_repeated':False,'automatic_retry':False,'automatic_fallback':False,'provider_configuration_changed':False,'model_configuration_changed':False,'false_ready_state':False}
def _snapshot(root:Path)->dict[str,str]:
    if not root.exists(): return {}
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}}
def _free_port()->int:
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock: sock.bind(('127.0.0.1',0)); return int(sock.getsockname()[1])
def _wait_health(port:int)->None:
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/dashboard-health',timeout=.5) as response:
                if json.loads(response.read().decode()).get('service')=='eidolon-dashboard': return
        except Exception: time.sleep(.08)
    raise AssertionError('dashboard health timeout')
def _external_env(runtime:Path,process_root:Path)->dict[str,str]:
    env=os.environ.copy(); env.update({'EIDOLON_DATA_DIR':str(runtime),'EIDOLON_PROCESS_RUNTIME_ROOT':str(process_root/'process'),'EIDOLON_METADATA_LOCK_DIR':str(process_root/'locks'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONPYCACHEPREFIX':str(process_root/'pycache'),'PYTHONUNBUFFERED':'1'}); return env

def test_default_checkpoint_is_content_free_read_only_and_honest()->None:
    r=build_messaging_reliability_checkpoint(); require(r['ok'] is True,r); require(r['status']=='ready_for_native_windows_review',r); require(r['content_free'] is True and r['private_values_included'] is False,r); require(checkpoint_contains_private_fields(r) is False,r)
    for key in ('provider_contacted','accepted_turn_replayed','provider_request_repeated','automatic_retry','automatic_resend','automatic_takeover','conversation_mutated','draft_mutated','ownership_mutated','provider_configuration_changed','model_configuration_changed','approval_granted','release_authorized','automatic_promotion','automatic_certification'): require(r.get(key) is False,(key,r.get(key)))
    require(r['operator_authority_required'] is True,r)
def test_complete_verification_and_native_evidence_reaches_operator_review_only()->None:
    r=build_messaging_reliability_checkpoint(provider_evidence=_provider('returned'),focused_verification=_verification(passed=12,total=12),regression_verification=_verification(),native_windows_evidence=_native(True)); require(r['ok'] is True and r['status']=='ready_for_operator_review',r); require(r['pending_evidence_count']==0,r); require(r['automatic_certification'] is False,r)
def test_exactly_once_violation_blocks_checkpoint()->None:
    r=build_messaging_reliability_checkpoint(exactly_once_evidence={'status':'blocked','exactly_once':False,'automatic_retry_count':0,'acceptance_claim_count':2,'operation_count':2,'execution_start_count':2,'provider_request_count':2}); by={x['name']:x for x in r['checks']}; require(r['ok'] is False and r['status']=='blocked',r); require(by['exactly_once_acceptance_and_provider_request']['status']=='blocked',by)
def test_replay_false_ready_or_stale_save_violation_blocks_checkpoint()->None:
    base={'scroll_anchor_preserved':True,'jump_to_latest_available':True,'atomic_conversation_switch':True,'source_draft_preserved':True,'target_draft_restored':True,'stale_save_rejected':True,'provider_return_requires_explicit_send':True,'accepted_turn_replayed':False,'provider_request_repeated':False,'automatic_retry':False,'false_ready_state':False}
    for key in ('accepted_turn_replayed','provider_request_repeated','automatic_retry','false_ready_state'):
        c=dict(base); c[key]=True; r=build_messaging_reliability_checkpoint(continuity_evidence=c); require(r['ok'] is False and r['status']=='blocked',(key,r))
def test_terminal_overwrite_or_automatic_retry_blocks_checkpoint()->None:
    for op in ({'terminal_truth_preserved':False,'automatic_retry_allowed':False,'late_result_ignored_count':1},{'terminal_truth_preserved':True,'automatic_retry_allowed':True,'late_result_ignored_count':1}):
        r=build_messaging_reliability_checkpoint(operation_evidence=op); by={x['name']:x for x in r['checks']}; require(r['ok'] is False,r); require(by['cancellation_retry_and_late_result_reconciliation']['status']=='blocked',by)
def test_automatic_takeover_or_stale_tab_send_blocks_checkpoint()->None:
    for own in ({'automatic_takeover':True,'stale_tab_may_send':False,'take_control_available':True,'is_owner':False},{'automatic_takeover':False,'stale_tab_may_send':True,'take_control_available':True,'is_owner':False}):
        r=build_messaging_reliability_checkpoint(ownership_evidence=own); by={x['name']:x for x in r['checks']}; require(r['ok'] is False,r); require(by['multi_tab_ownership_and_stale_recovery']['status']=='blocked',by)
def test_failed_soak_blocks_instead_of_hiding_debt()->None:
    r=build_messaging_reliability_checkpoint(soak_evidence={'status':'blocked','passed':False,'exactly_once_preserved':False,'iterations':60,'automatic_retries':1,'source_mutations':0}); by={x['name']:x for x in r['checks']}; require(r['ok'] is False and r['status']=='blocked',r); require(by['long_session_messaging_soak']['status']=='blocked',by)
def test_provider_unavailable_remains_pending_but_replay_violation_blocks()->None:
    r=build_messaging_reliability_checkpoint(provider_evidence=_provider('unavailable')); by={x['name']:x for x in r['checks']}; require(r['ok'] is True and r['status']=='ready_for_native_windows_review',r); require(by['provider_outage_and_return_truth']['status']=='pending',by); unsafe=_provider('returned'); unsafe['provider_request_repeated']=True; b=build_messaging_reliability_checkpoint(provider_evidence=unsafe); require(b['ok'] is False and b['status']=='blocked',b)
def test_failed_native_evidence_degrades_without_certifying()->None:
    r=build_messaging_reliability_checkpoint(native_windows_evidence=_native(False)); require(r['ok'] is True and r['status']=='degraded',r); require(r['native_windows_evidence_status']=='degraded',r); require(r['automatic_certification'] is False,r)
def test_failed_attached_verification_blocks_checkpoint()->None:
    r=build_messaging_reliability_checkpoint(focused_verification=_verification(False,passed=11,total=12),regression_verification=_verification()); by={x['name']:x for x in r['checks']}; require(r['ok'] is False and r['status']=='blocked',r); require(by['focused_deterministic_verification']['status']=='blocked',by)
def test_cli_dashboard_route_and_bootstrap_are_repeatable_and_runtime_read_only()->None:
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1103-9-route-')); runtime=base/'runtime'; env=_external_env(runtime,base/'external')
    cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'messaging-reliability-checkpoint','--json'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45); require(cli.returncode==0,cli.stderr); require(json.loads(cli.stdout)['status']=='ready_for_native_windows_review',cli.stdout)
    port=_free_port(); proc=subprocess.Popen([sys.executable,str(ROOT/'eidolon.py'),'start','--no-browser','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        _wait_health(port); before=_snapshot(runtime); reports=[]
        for path in ('/api/messaging-reliability/checkpoint','/api/first-use/bootstrap?launch=checkpoint'):
            with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=8) as response: reports.append(json.loads(response.read().decode()))
        require(before==_snapshot(runtime),'checkpoint GET mutated runtime'); require(reports[0]['status']=='ready_for_native_windows_review',reports[0]); require((reports[1].get('messaging_reliability_checkpoint') or {}).get('status')=='ready_for_native_windows_review',reports[1])
    finally:
        proc.terminate()
        try: proc.communicate(timeout=8)
        except subprocess.TimeoutExpired: proc.kill(); proc.communicate(timeout=5)
def test_shell_metadata_docs_and_focused_registration_align()->None:
    import release_metadata
    require(tuple(int(x) for x in release_metadata.WORKING_SOURCE_VERSION.split('.'))>=(1103,9),release_metadata.WORKING_SOURCE_VERSION)
    shell=(AGENT/'dashboard_first_use.py').read_text(encoding='utf-8'); dashboard=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    for token in ('Messaging reliability','messaging-checkpoint-state','no automatic replay, retry, takeover, or certification'): require(token in shell,token)
    require('/api/messaging-reliability/checkpoint' in dashboard,'checkpoint route')
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(encoding='utf-8'); require(verifier.count('"tools/v1103_9_messaging_reliability_checkpoint_tests.py"')==1,'registration')
    roadmap=(ROOT/'archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md').read_text(encoding='utf-8'); require(release_metadata.WORKING_SOURCE_VERSION in roadmap,'current roadmap version')
    require(f'## v{release_metadata.WORKING_SOURCE_VERSION}' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'current history')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md'): require(release_metadata.WORKING_SOURCE_VERSION in (ROOT/name).read_text(encoding='utf-8'),name)
TESTS=[(name.removeprefix('test_'),fn) for name,fn in list(globals().items()) if name.startswith('test_')]
def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({'name':name,'status':'fail','message':f'{type(error).__name__}: {error}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1103.9-messaging-reliability-checkpoint','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
