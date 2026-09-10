from __future__ import annotations
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent'
for p in (AGENT,ROOT):
    if str(p) not in os.sys.path:os.sys.path.insert(0,str(p))
from persistent_internal_life_checkpoint import build_persistent_internal_life_checkpoint
from persistent_motivation import MotivationStore
from endogenous_cognitive_cycle import EndogenousCognitiveCycle
from proactive_communication import ProactiveCommunicationStore
from cognitive_continuity import CognitiveContinuityStore
from belief_revision import BeliefRevisionStore

def require(c:bool,d:Any='requirement failed'):
    if not c:raise AssertionError(d)
def fixture():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1104-9-'));root=base/'runtime'/'cognition';source=base/'source'/'Eidolon';source.mkdir(parents=True);m=MotivationStore(root);return base,root,source,m
def populate(root,m):
    mid=m.record_motivation('m',kind='concern',summary='Checkpoint concern',cognitive_state='desire',urgency=.9,confidence=.8,origin_type='fixture',origin_ref='m')['result']['motivation_id']
    cycle=EndogenousCognitiveCycle(root,motivation_store=m);cycle.set_control('budget',action='adjust_budget',max_cycles_per_hour=60,max_cycles_per_day=100)
    result=cycle.run_cycle('cycle',trigger_type='memory_change',perceived_events=[{'event_type':'memory_change','event_ref':'ref','motivation_id':mid}],provider_available=False,now_epoch=100)
    ProactiveCommunicationStore(root,motivation_store=m).consider_cycle(result,now_epoch=100)
    CognitiveContinuityStore(root,motivation_store=m).advance_time('advance',now_epoch=100)
    beliefs=BeliefRevisionStore(root,motivation_store=m);beliefs.record_belief('belief',proposition='The checkpoint fixture is coherent',confidence=.7,origin_type='fixture',origin_ref='belief')
    return mid

def test_checkpoint_is_read_only_on_empty_runtime():
    _,root,source,_=fixture();before=list(root.parent.rglob('*'));cp=build_persistent_internal_life_checkpoint(root,source_root=source);after=list(root.parent.rglob('*'));require(before==after,(before,after));require(cp['runtime_mutated'] is False and cp['provider_contacted'] is False)
def test_checkpoint_aggregates_persistent_motivation_cycle_initiative_continuity_and_beliefs():
    _,root,source,m=fixture();populate(root,m);cp=build_persistent_internal_life_checkpoint(root,source_root=source);summary=cp['summary'];require(summary['active_motivation_count']==1,summary);require(summary['cycle_count']==1 and summary['proactive_message_count']==1,summary);require(summary['continuity_subject_count']==1 and summary['active_belief_count']==1,summary)
def test_checkpoint_remains_epistemically_careful():
    _,root,source,_=fixture();cp=build_persistent_internal_life_checkpoint(root,source_root=source);require(cp['consciousness_claimed'] is False);require(cp['epistemic_status']=='candidate_artificial_consciousness_not_proven');require('proven' not in cp['headline'].lower())
def test_privacy_and_hidden_reasoning_checks_pass():
    _,root,source,m=fixture();populate(root,m);cp=build_persistent_internal_life_checkpoint(root,source_root=source);require(cp['raw_prompts_exposed'] is False and cp['private_conversations_exposed'] is False and cp['hidden_reasoning_exposed'] is False);require(next(c for c in cp['checks'] if c['id']=='privacy_boundary')['status']=='pass')
def test_internal_state_action_boundary_is_preserved():
    _,root,source,m=fixture();populate(root,m);cp=build_persistent_internal_life_checkpoint(root,source_root=source);require(cp['action_authority_changed'] is False);require(next(c for c in cp['checks'] if c['id']=='action_boundary')['status']=='pass')
def test_external_runtime_separation_is_recognized():
    _,root,source,_=fixture();cp=build_persistent_internal_life_checkpoint(root,source_root=source);require(cp['runtime_external'] is True);require(next(c for c in cp['checks'] if c['id']=='runtime_separation')['status']=='pass')
def test_in_source_runtime_is_reported_pending_not_silently_accepted():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1104-9-inside-'));source=base/'Eidolon';root=source/'data'/'cognition';cp=build_persistent_internal_life_checkpoint(root,source_root=source);require(cp['runtime_external'] is False);require(next(c for c in cp['checks'] if c['id']=='runtime_separation')['status']=='pending_desktop')
def test_provider_unavailability_or_absence_is_informational_not_product_failure():
    _,root,source,_=fixture();cp=build_persistent_internal_life_checkpoint(root,source_root=source);require(cp['provider_classification']=='not_run');require(next(c for c in cp['checks'] if c['id']=='native_provider')['status']=='informational');require(cp['ok'] is True)
def test_checkpoint_does_not_promote_certify_or_manage_models():
    _,root,source,_=fixture();cp=build_persistent_internal_life_checkpoint(root,source_root=source);require(cp['release_promoted'] is False and cp['release_certified'] is False);text=json.dumps(cp);require('install the model' not in text.lower() and 'pull the model' not in text.lower())
def test_api_checkpoint_route_is_read_only():
    from api_server import dispatch_api
    data=Path(tempfile.mkdtemp(prefix='eidolon-v1104-9-api-'))/'runtime';previous=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(data)
    try:
        status,payload=dispatch_api('GET','/api/cognition/internal-life-checkpoint');require(status==200,payload);require(payload['data']['action_authority_changed'] is False,payload)
    finally:
        if previous is None:os.environ.pop('EIDOLON_DATA_DIR',None)
        else:os.environ['EIDOLON_DATA_DIR']=previous
def test_cli_checkpoint_is_provider_free_and_structured():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1104-9-cli-'));env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(base/'runtime');run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'internal-life-checkpoint','--json'],cwd=ROOT,env=env,capture_output=True,text=True);require(run.returncode==0,run.stderr);payload=json.loads(run.stdout);require(payload['provider_contacted'] is False and payload['release_certified'] is False,payload)
def test_dashboard_exposes_checkpoint_without_raw_reasoning():
    from dashboard_first_use import render_first_use_shell
    html=render_first_use_shell();require("id='internal-life-checkpoint-state'" in html);require('/api/cognition/internal-life-checkpoint' in html);section=html.split("id='internal-life-checkpoint-state'",1)[1].split('</section>',1)[0];require('title=' not in section and 'chain-of-thought' not in section.lower())

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--json',action='store_true');parser.parse_args();checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as x:checks.append({'name':n,'status':'fail','message':f'{type(x).__name__}: {x}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    report={'suite':'v1104.9-persistent-internal-life-checkpoint','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
