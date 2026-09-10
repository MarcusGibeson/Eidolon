from __future__ import annotations
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for p in (AGENT,ROOT):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from persistent_motivation import MotivationStore
from self_directed_inquiry import InquiryWorkspace
from prospective_planning import ProspectivePlanningStore

def require(value:bool,detail:Any='requirement failed'):
    if not value: raise AssertionError(detail)

def alternatives():
    return [
        {'alternative_id':'reversible','label':'Run a reversible local trial','expected_outcomes':['Gain bounded evidence'],'risks':['Small time cost'],'expected_benefit':.8,'risk':.2,'reversibility':.95,'confidence':.75},
        {'alternative_id':'irreversible','label':'Commit immediately','expected_outcomes':['Faster completion'],'risks':['Hard to undo'],'expected_benefit':.7,'risk':.8,'reversibility':.1,'confidence':.5},
    ]

def fixture():
    root=Path(tempfile.mkdtemp(prefix='eidolon-v1105-1-'))/'runtime'/'cognition'; m=MotivationStore(root)
    mid=m.record_motivation('m',kind='curiosity',summary='Which path is safer?',cognitive_state='desire',urgency=.8,confidence=.7,origin_type='fixture',origin_ref='m')['result']['motivation_id']
    inquiries=InquiryWorkspace(root,motivation_store=m); iid=inquiries.create_inquiry('i',motivation_id=mid,question='What choice preserves reversibility?')['result']['inquiry_id']
    return root,m,inquiries,mid,iid

def test_plan_links_motivation_and_inquiry_and_persists():
    root,m,i,mid,iid=fixture(); result=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i).create_plan('create',subject='Choose an implementation path',alternatives=alternatives(),motivation_ids=[mid],inquiry_ids=[iid],constraints=['No protected action'])
    require(result['status']=='plan_created',result); restarted=ProspectivePlanningStore(root,motivation_store=MotivationStore(root)); require(restarted.inspection_summary()['active_plan_count']==1)

def test_plan_requires_two_alternatives():
    root,m,i,mid,iid=fixture()
    try: ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i).create_plan('create',subject='Too few',alternatives=alternatives()[:1])
    except ValueError: return
    raise AssertionError('single alternative accepted')

def test_unknown_links_are_rejected():
    root,m,i,mid,iid=fixture(); store=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i)
    try: store.create_plan('create',subject='Missing link',alternatives=alternatives(),motivation_ids=['missing'])
    except KeyError: return
    raise AssertionError('unknown link accepted')

def test_duplicate_event_and_semantic_plan_are_idempotent():
    root,m,i,mid,iid=fixture(); store=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i); first=store.create_plan('same',subject='Same',alternatives=alternatives(),motivation_ids=[mid]); replay=store.create_plan('same',subject='Ignored',alternatives=alternatives()); duplicate=store.create_plan('other',subject='Same',alternatives=alternatives(),motivation_ids=[mid])
    require(replay['idempotent'] is True,replay); require(duplicate['status']=='duplicate_plan_ignored',duplicate); require(store.inspection_summary()['active_plan_count']==1)

def test_comparison_deterministically_favors_reversible_lower_risk_option():
    root,m,i,mid,iid=fixture(); store=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i); pid=store.create_plan('create',subject='Compare',alternatives=alternatives())['result']['plan_id']; result=store.compare_plan('compare',plan_id=pid)
    require(result['result']['recommended_alternative_id']=='reversible',result); require(result['result']['ranking'][0]['rank']==1)

def test_counterfactual_is_bounded_and_reference_safe():
    root,m,i,mid,iid=fixture(); store=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i); pid=store.create_plan('create',subject='Counterfactual',alternatives=alternatives())['result']['plan_id']; result=store.record_counterfactual('cf',plan_id=pid,alternative_id='reversible',premise='The trial fails quickly',expected_outcome='Return to the prior state',probability=.3,downside=.2,reversibility=.95,supporting_refs=['private-evidence-ref'])
    require(result['status']=='counterfactual_recorded',result); text=json.dumps(store.snapshot()); require('private-evidence-ref' not in text,text); require('The trial fails quickly' in text)

def test_internal_proposal_is_never_authorized_or_executed():
    root,m,i,mid,iid=fixture(); store=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i); pid=store.create_plan('create',subject='Proposal',alternatives=alternatives())['result']['plan_id']; store.compare_plan('compare',plan_id=pid); result=store.propose_intention('proposal',plan_id=pid,alternative_id='reversible',rationale='Prefer reversible evidence gathering',supporting_refs=['comparison'])
    require(result['result']['authorized'] is False and result['result']['executed'] is False,result); summary=store.inspection_summary(); require(summary['action_authority_changed'] is False and summary['external_action_executed'] is False,summary)

def test_corrected_plan_remains_historical_without_active_influence():
    root,m,i,mid,iid=fixture(); store=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i); pid=store.create_plan('create',subject='Wrong premise',alternatives=alternatives())['result']['plan_id']; store.set_status('correct',plan_id=pid,status='corrected',reason_code='premise_changed',correction_ref='private-correction')
    summary=store.inspection_summary(); require(summary['active_plan_count']==0 and summary['historical_plan_count']==1,summary); require('private-correction' not in json.dumps(store.snapshot()))

def test_api_create_compare_and_inspect_routes():
    from api_server import dispatch_api
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-1-api-')); old=os.environ.get('EIDOLON_DATA_DIR'); os.environ['EIDOLON_DATA_DIR']=str(base/'runtime')
    try:
        status,payload=dispatch_api('POST','/api/cognition/prospective-planning/create',body={'event_id':'p','subject':'API plan','alternatives':alternatives()}); require(status==200,payload); pid=payload['data']['result']['plan_id']
        status,payload=dispatch_api('POST','/api/cognition/prospective-planning/compare',body={'event_id':'c','plan_id':pid}); require(status==200 and payload['data']['result']['recommended_alternative_id']=='reversible',payload)
        status,payload=dispatch_api('GET','/api/cognition/prospective-planning'); require(status==200 and payload['data']['active_plan_count']==1,payload)
    finally:
        if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
        else: os.environ['EIDOLON_DATA_DIR']=old

def test_cli_status_is_provider_free_and_action_inert():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-1-cli-')); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(base/'runtime')
    run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'planning-status','--json'],cwd=ROOT,env=env,capture_output=True,text=True); require(run.returncode==0,run.stderr); payload=json.loads(run.stdout); require(payload['provider_contacted'] is False and payload['action_authority_changed'] is False,payload)

def test_planning_is_resource_bounded_and_provider_free():
    root,m,i,mid,iid=fixture(); summary=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=i).inspection_summary(); require(summary['resource_limits']['max_alternatives_per_plan']==8); require(summary['provider_contacted'] is False and summary['hidden_reasoning_exposed'] is False)

TESTS=[(name.removeprefix('test_'),fn) for name,fn in list(globals().items()) if name.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1105.1-prospective-planning-counterfactual-evaluation','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
