from __future__ import annotations
import argparse, json, os, tempfile
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for p in (AGENT,ROOT):
    if str(p) not in os.sys.path: os.sys.path.insert(0,str(p))
from cognitive_continuity import CognitiveContinuityStore
from persistent_motivation import MotivationStore

def require(c: bool, d: Any='requirement failed')->None:
    if not c: raise AssertionError(d)

def fixture():
    root=Path(tempfile.mkdtemp(prefix='eidolon-v1104-6-'))/'cognition'; m=MotivationStore(root); c=CognitiveContinuityStore(root,motivation_store=m); return m,c,root

def add(m:MotivationStore,event:str,kind='concern',urgency=.8,confidence=.8):
    return m.record_motivation(event,kind=kind,summary=f'Subject {event}',cognitive_state='desire',urgency=urgency,confidence=confidence,origin_type='fixture',origin_ref=event)['result']['motivation_id']

def test_subjects_persist_across_restart():
    m,c,root=fixture(); mid=add(m,'persist'); c.advance_time('advance',now_epoch=1000); restarted=CognitiveContinuityStore(root,motivation_store=MotivationStore(root)); require(restarted.snapshot()['subjects'][0]['motivation_id']==mid)

def test_relevance_decays_but_enduring_goals_keep_floor():
    m,c,_=fixture(); add(m,'goal',kind='enduring_goal',urgency=1,confidence=1); c.advance_time('a',now_epoch=0); c.advance_time('b',now_epoch=120*86400); row=c.snapshot()['subjects'][0]; require(row['current_relevance']>=.42,row)

def test_temporary_subjects_decay_more_than_enduring_goals():
    m,c,_=fixture(); add(m,'temp',kind='temporary_goal',urgency=1,confidence=1); add(m,'end',kind='enduring_goal',urgency=1,confidence=1); c.advance_time('a',now_epoch=0); c.advance_time('b',now_epoch=60*86400); rows={r['kind']:r for r in c.snapshot()['subjects']}; require(rows['temporary_goal']['current_relevance']<rows['enduring_goal']['current_relevance'],rows)

def test_due_revisit_events_are_bounded_and_content_free():
    m,c,_=fixture(); [add(m,f'x{i}') for i in range(20)]; c.advance_time('a',now_epoch=100); events=c.due_revisit_events(now_epoch=100,limit=5); require(len(events)==5,events); require(all(e['content_free'] and 'Subject' not in json.dumps(e) for e in events),events)

def test_sleep_consolidation_is_bounded_and_provider_free():
    m,c,_=fixture(); [add(m,f's{i}') for i in range(12)]; c.advance_time('a',now_epoch=100); result=c.sleep_and_consolidate('sleep',now_epoch=100,max_items=3); require(result['result']['consolidated_count']==3,result); require(result['result']['provider_contacted'] is False,result)

def test_sleep_and_wake_preserve_internal_continuity():
    m,c,_=fixture(); mid=add(m,'wake'); c.advance_time('a',now_epoch=100); c.sleep_and_consolidate('s',now_epoch=100); wake=c.wake('w',now_epoch=90000); require(c.snapshot()['mode']=='awake'); require(any(r['motivation_id']==mid for r in c.snapshot()['subjects'])); require(wake['result']['continuity_erased'] is False)

def test_calendar_boundary_is_recorded_once():
    m,c,_=fixture(); add(m,'day'); c.advance_time('d1',now_epoch=100); first=c.advance_time('d2',now_epoch=90000); second=c.advance_time('d3',now_epoch=90100); require(first['result']['calendar_boundary_crossed'] is True); require(second['result']['calendar_boundary_crossed'] is False); require(len(c.snapshot()['day_ledger'])==1)

def test_duplicate_events_do_not_duplicate_consolidation():
    m,c,_=fixture(); add(m,'dup'); c.advance_time('a',now_epoch=10); first=c.sleep_and_consolidate('same',now_epoch=10); second=c.sleep_and_consolidate('same',now_epoch=10); require(first['idempotent'] is False and second['idempotent'] is True); require(len(c.snapshot()['consolidation_receipts'])==1)

def test_retracted_motivations_stop_active_influence_without_history_erasure():
    m,c,_=fixture(); mid=add(m,'retract'); c.advance_time('a',now_epoch=10); m.retract_motivation('r',mid,reason_code='correction',correction_ref='ref'); c.advance_time('b',now_epoch=20); row=c.snapshot()['subjects'][0]; require(row['active'] is False and row['current_relevance']==0); require(len(m.snapshot()['motivations'])==1)

def test_identity_survives_provider_switch_and_calendar_change():
    m,c,root=fixture(); m.initialize_self_model('i',provider_id='provider-a'); add(m,'identity'); c.advance_time('a',now_epoch=10); m.initialize_self_model('j',provider_id='provider-b'); c.wake('w',now_epoch=90000); snap=MotivationStore(root).snapshot(); require(snap['identity']['identity_id']=='eidolon'); require(len(snap['self_model']['provider_observations'])==2)

def test_continuity_cannot_authorize_or_execute_actions():
    m,c,_=fixture(); add(m,'boundary'); c.advance_time('a',now_epoch=10); c.sleep_and_consolidate('s',now_epoch=10); state=c.snapshot(); require(state['authority_boundary']['can_authorize_action'] is False); require(state['authority_boundary']['can_execute_action'] is False); require(all(not bool(r.get('raw_chain_of_thought_stored')) for r in state.get('consolidation_receipts',[])))

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for n,f in TESTS:
        try: f()
        except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    report={'suite':'v1104.6-multi-day-cognitive-continuity','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
