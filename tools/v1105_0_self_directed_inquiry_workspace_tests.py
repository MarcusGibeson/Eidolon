from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for p in (AGENT,ROOT):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from persistent_motivation import MotivationStore
from self_directed_inquiry import InquiryWorkspace

def require(value: bool, detail: Any='requirement failed'):
    if not value: raise AssertionError(detail)

def fixture(kind='curiosity'):
    root=Path(tempfile.mkdtemp(prefix='eidolon-v1105-0-'))/'runtime'/'cognition'; m=MotivationStore(root)
    result=m.record_motivation('motivation',kind=kind,summary='Why does this pattern recur?',cognitive_state='desire',urgency=.8,confidence=.7,origin_type='fixture',origin_ref='motivation')
    return root,m,result['result']['motivation_id']

def test_inquiry_is_created_from_durable_curiosity():
    root,m,mid=fixture(); result=InquiryWorkspace(root,motivation_store=m).create_inquiry('create',motivation_id=mid,question='What evidence would distinguish the explanations?',uncertainty=.8,sources_sought=['local memory references'],stop_conditions=['Stop after three conclusions.'])
    require(result['status']=='inquiry_created',result); row=InquiryWorkspace(root,motivation_store=m).select_next(); require(row and row['motivation_id']==mid,row)

def test_non_curiosity_motivation_is_rejected():
    root,m,mid=fixture('temporary_goal')
    try: InquiryWorkspace(root,motivation_store=m).create_inquiry('create',motivation_id=mid,question='Should not open')
    except ValueError: return
    raise AssertionError('non-curiosity accepted')

def test_state_survives_restart():
    root,m,mid=fixture(); InquiryWorkspace(root,motivation_store=m).create_inquiry('create',motivation_id=mid,question='Persistent question')
    require(InquiryWorkspace(root,motivation_store=MotivationStore(root)).inspection_summary()['active_inquiry_count']==1)

def test_duplicate_event_and_semantic_inquiry_are_idempotent():
    root,m,mid=fixture(); store=InquiryWorkspace(root,motivation_store=m); first=store.create_inquiry('same',motivation_id=mid,question='One question'); replay=store.create_inquiry('same',motivation_id=mid,question='Different ignored'); duplicate=store.create_inquiry('other',motivation_id=mid,question='One question')
    require(replay['idempotent'] is True,replay); require(duplicate['status']=='duplicate_inquiry_ignored',duplicate); require(store.inspection_summary()['active_inquiry_count']==1)

def test_progress_records_conclusion_and_reference_digests_only():
    root,m,mid=fixture(); store=InquiryWorkspace(root,motivation_store=m); iid=store.create_inquiry('create',motivation_id=mid,question='Question')['result']['inquiry_id']; result=store.add_progress('progress',inquiry_id=iid,conclusion='The local evidence narrows one possibility.',supporting_refs=['private-reference-value'],uncertainty_after=.4,next_question='What would contradict it?')
    require(result['result']['uncertainty']==.4,result); text=json.dumps(store.snapshot()); require('private-reference-value' not in text,text); require('The local evidence narrows' in text)

def test_step_budget_pauses_inquiry_without_looping():
    root,m,mid=fixture(); store=InquiryWorkspace(root,motivation_store=m); iid=store.create_inquiry('create',motivation_id=mid,question='Bounded')['result']['inquiry_id']
    state=store.snapshot(); state['resource_limits']['max_progress_steps_per_inquiry']=1
    from json_storage import write_json_atomic
    write_json_atomic(store.path,state,expected_type=dict,sort_keys=True)
    store.add_progress('p1',inquiry_id=iid,conclusion='One'); result=store.add_progress('p2',inquiry_id=iid,conclusion='Two'); require(result['status']=='inquiry_step_budget_reached',result); require(store.select_next() is None)

def test_completed_and_corrected_inquiries_leave_history_but_no_active_influence():
    root,m,mid=fixture(); store=InquiryWorkspace(root,motivation_store=m); iid=store.create_inquiry('create',motivation_id=mid,question='Correct me')['result']['inquiry_id']; store.set_status('correct',inquiry_id=iid,status='corrected',reason_code='premise_wrong',correction_ref='correction-record')
    summary=store.inspection_summary(); require(summary['active_inquiry_count']==0 and summary['historical_inquiry_count']==1,summary); require('correction-record' not in json.dumps(store.snapshot()))

def test_inquiry_has_no_provider_browse_or_action_authority():
    root,m,mid=fixture(); store=InquiryWorkspace(root,motivation_store=m); store.create_inquiry('create',motivation_id=mid,question='Boundary'); summary=store.inspection_summary(); require(summary['provider_contacted'] is False and summary['external_browsing_performed'] is False and summary['action_authority_changed'] is False,summary)

def test_api_routes_create_and_inspect():
    from api_server import dispatch_api
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-0-api-')); old=os.environ.get('EIDOLON_DATA_DIR'); os.environ['EIDOLON_DATA_DIR']=str(base/'runtime')
    try:
        m=MotivationStore(); mid=m.record_motivation('m',kind='curiosity',summary='API curiosity',cognitive_state='desire',urgency=.7,confidence=.7,origin_type='fixture',origin_ref='m')['result']['motivation_id']
        status,payload=dispatch_api('POST','/api/cognition/inquiries/create',body={'event_id':'i','motivation_id':mid,'question':'API question'}); require(status==200,payload)
        status,payload=dispatch_api('GET','/api/cognition/inquiries'); require(status==200 and payload['data']['active_inquiry_count']==1,payload)
    finally:
        if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
        else: os.environ['EIDOLON_DATA_DIR']=old

def test_cli_status_is_structured_and_provider_free():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-0-cli-')); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(base/'runtime')
    run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'inquiry-status','--json'],cwd=ROOT,env=env,capture_output=True,text=True)
    require(run.returncode==0,run.stderr); payload=json.loads(run.stdout); require(payload['provider_contacted'] is False and payload['action_authority_changed'] is False,payload)

TESTS=[(name.removeprefix('test_'),fn) for name,fn in list(globals().items()) if name.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1105.0-self-directed-inquiry-workspace','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
