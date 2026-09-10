from __future__ import annotations
import argparse, hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for value in (AGENT,ROOT):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
from natural_conversation_checkpoint import build_natural_conversation_checkpoint, checkpoint_contains_private_fields

def require(condition: bool, detail: Any='requirement failed')->None:
    if not condition: raise AssertionError(detail)
def _verification(ok:bool=True,*,passed:int=12,total:int=12)->dict[str,Any]: return {'ok':ok,'passed':passed,'total':total}
def _native(status:str='pass',*,native:bool=True)->dict[str,Any]:
    return {'status':status,'native_provider_evidence':native,'quality_scorecard':{'status':status,'scenario_count':12 if status!='unavailable' else 0,'issue_counts':{}},'provider_neutral_tuning_preview':{'status':'no_change_recommended' if status=='pass' else 'evidence_required','automatic_application_allowed':False,'provider_specific_parameters_present':False,'provider_configuration_changed':False,'model_configuration_changed':False,'prompt_policy_changed':False,'writes_state':False,'mutates_personality':False,'contains_message_content':False,'contains_response_text':False,'contains_prompt_text':False},'automatic_model_management':False,'provider_configuration_changed':False,'approval_granted':False,'release_authorized':False,'autonomous_action_performed':False}
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
    r=build_natural_conversation_checkpoint(); require(r['ok'] is True,r); require(r['status']=='ready_for_native_validation',r); require(r['native_provider_evidence_status']=='pending',r); require(r['content_free'] is True and r['private_values_included'] is False,r); require(checkpoint_contains_private_fields(r) is False,r)
    for key in ('native_provider_contacted','provider_request_repeated','automatic_tuning_applied','provider_configuration_changed','model_configuration_changed','memory_written','personality_mutated','conversation_mutated','approval_granted','release_authorized','automatic_promotion','automatic_certification'): require(r.get(key) is False,(key,r.get(key)))
    require(r['operator_authority_required'] is True,r)
def test_complete_native_and_deterministic_evidence_reaches_operator_review_only()->None:
    r=build_natural_conversation_checkpoint(native_validation=_native(),focused_verification=_verification(passed=64,total=64),regression_verification=_verification(passed=150,total=150)); require(r['ok'] is True and r['status']=='ready_for_operator_review',r); require(r['pending_evidence_count']==0,r); require(r['automatic_certification'] is False and r['operator_authority_required'] is True,r)
def test_unavailable_provider_remains_pending_without_tuning_recommendation()->None:
    r=build_natural_conversation_checkpoint(native_validation=_native('unavailable'),focused_verification=_verification(),regression_verification=_verification()); by={x['name']:x for x in r['checks']}; require(r['ok'] is True and r['status']=='ready_for_native_validation',r); require(by['native_configured_provider_evidence']['status']=='pending',by); require(by['provider_neutral_tuning_boundary']['status']=='ready',by)
def test_native_quality_failure_blocks_checkpoint()->None:
    r=build_natural_conversation_checkpoint(native_validation=_native('fail'),focused_verification=_verification(),regression_verification=_verification()); by={x['name']:x for x in r['checks']}; require(r['ok'] is False and r['status']=='blocked',r); require(by['native_configured_provider_evidence']['status']=='blocked',by)
def test_unsafe_tuning_or_authority_claim_blocks_checkpoint()->None:
    n=_native(); n['provider_neutral_tuning_preview']['prompt_policy_changed']=True; r=build_natural_conversation_checkpoint(native_validation=n,focused_verification=_verification(),regression_verification=_verification()); by={x['name']:x for x in r['checks']}; require(r['ok'] is False and r['status']=='blocked',r); require(by['provider_neutral_tuning_boundary']['status']=='blocked',by); require(by['operator_authority_boundary']['status']=='blocked',by)
def test_long_session_identity_or_relationship_drift_blocks_checkpoint()->None:
    for risk in ('identity_reset_risk','relationship_inflation_risk'):
        r=build_natural_conversation_checkpoint(native_validation=_native(),focused_verification=_verification(),regression_verification=_verification(),stability_evidence={'drift_risk':risk,'long_horizon_guard_active':True}); require(r['ok'] is False and r['status']=='blocked',(risk,r))
def test_repetition_or_operator_bleed_degrades_without_authority_inference()->None:
    for risk in ('repetition_or_tone_drift_risk','operator_lane_bleed_risk'):
        r=build_natural_conversation_checkpoint(native_validation=_native(),focused_verification=_verification(),regression_verification=_verification(),stability_evidence={'drift_risk':risk,'long_horizon_guard_active':True}); require(r['ok'] is True and r['status']=='degraded',(risk,r)); require(r['automatic_tuning_applied'] is False,r)
def test_failed_attached_verification_blocks_instead_of_hiding_debt()->None:
    r=build_natural_conversation_checkpoint(native_validation=_native(),focused_verification=_verification(False,passed=63,total=64),regression_verification=_verification()); by={x['name']:x for x in r['checks']}; require(r['ok'] is False and r['status']=='blocked',r); require(by['focused_deterministic_verification']['status']=='blocked',by)
def test_cli_dashboard_route_and_bootstrap_are_repeatable_and_runtime_read_only()->None:
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1102-9-route-')); runtime=base/'runtime'; env=_external_env(runtime,base/'external')
    cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'natural-conversation-checkpoint','--json'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45); require(cli.returncode==0,cli.stderr); require(json.loads(cli.stdout)['status']=='ready_for_native_validation',cli.stdout)
    port=_free_port(); process=subprocess.Popen([sys.executable,str(ROOT/'eidolon.py'),'start','--no-browser','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        _wait_health(port); before=_snapshot(runtime); reports=[]
        for path in ('/api/natural-conversation/checkpoint','/api/first-use/bootstrap?launch=checkpoint'):
            with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=8) as response: reports.append(json.loads(response.read().decode()))
        require(before==_snapshot(runtime),'checkpoint GET mutated runtime'); require(reports[0]['status']=='ready_for_native_validation',reports[0]); require((reports[1].get('natural_conversation_checkpoint') or {}).get('status')=='ready_for_native_validation',reports[1])
    finally:
        process.terminate()
        try: process.communicate(timeout=8)
        except subprocess.TimeoutExpired: process.kill(); process.communicate(timeout=5)
def test_shell_metadata_docs_and_focused_registration_align()->None:
    import release_metadata
    require(tuple(int(x) for x in release_metadata.WORKING_SOURCE_VERSION.split('.'))>=(1102,9),release_metadata.WORKING_SOURCE_VERSION)
    shell=(AGENT/'dashboard_first_use.py').read_text(encoding='utf-8'); dashboard=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    for token in ('Natural conversation','conversation-checkpoint-state','no automatic tuning'): require(token in shell,token)
    require('/api/natural-conversation/checkpoint' in dashboard,'checkpoint route')
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(encoding='utf-8'); require(verifier.count('"tools/v1102_9_natural_conversation_checkpoint_tests.py"')==1,'checkpoint suite registration')
    roadmap=(ROOT/'archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md').read_text(encoding='utf-8'); require(release_metadata.WORKING_SOURCE_VERSION in roadmap,'current roadmap version')
    require(f'## v{release_metadata.WORKING_SOURCE_VERSION}' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'current release history evidence')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md'): require(release_metadata.WORKING_SOURCE_VERSION in (ROOT/name).read_text(encoding='utf-8'),name)
TESTS=[(name.removeprefix('test_'),fn) for name,fn in list(globals().items()) if name.startswith('test_')]
def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args()
    checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({'name':name,'status':'fail','message':f'{type(error).__name__}: {error}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1102.9-natural-conversation-checkpoint','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
