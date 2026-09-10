from __future__ import annotations
import argparse,json,os,tempfile
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for p in (AGENT,ROOT):
    if str(p) not in os.sys.path: os.sys.path.insert(0,str(p))
from belief_revision import BeliefRevisionStore
from persistent_motivation import MotivationStore

def require(c:bool,d:Any='requirement failed'):
    if not c: raise AssertionError(d)
def fixture():
    root=Path(tempfile.mkdtemp(prefix='eidolon-v1104-7-'))/'cognition'; m=MotivationStore(root); b=BeliefRevisionStore(root,motivation_store=m); return m,b,root
def belief(b,event,prop,confidence=.5): return b.record_belief(event,proposition=prop,confidence=confidence,origin_type='fixture',origin_ref=event)['result']['belief_id']
def motivation(m,event,state='commitment'): return m.record_motivation(event,kind='enduring_goal',summary=f'Commitment {event}',cognitive_state=state,urgency=.8,confidence=.8,origin_type='fixture',origin_ref=event)['result']['motivation_id']

def test_beliefs_persist_across_restart():
    m,b,root=fixture(); bid=belief(b,'p','The fixture is stable'); require(BeliefRevisionStore(root,motivation_store=MotivationStore(root)).snapshot()['beliefs'][0]['belief_id']==bid)
def test_supporting_evidence_increases_confidence():
    _,b,_=fixture(); bid=belief(b,'b','A',.4); r=b.add_evidence('e',belief_id=bid,stance='supports',weight=1,reliability=1,evidence_ref='ref'); require(r['result']['confidence']>.4,r)
def test_contradicting_evidence_decreases_confidence_and_marks_contested():
    _,b,_=fixture(); bid=belief(b,'b','A',.6); b.add_evidence('s',belief_id=bid,stance='supports',weight=.5,reliability=1,evidence_ref='support'); r=b.add_evidence('c',belief_id=bid,stance='contradicts',weight=1,reliability=1,evidence_ref='contradict'); require(r['result']['confidence']<.6 and r['result']['lifecycle_state']=='contested',r)
def test_uncertainty_remains_explicit():
    _,b,_=fixture(); bid=belief(b,'b','A',.5); row=b.snapshot()['beliefs'][0]; require(row['uncertainty']==1.0); b.add_evidence('e',belief_id=bid,stance='supports',weight=1,reliability=1,evidence_ref='ref'); require(b.snapshot()['beliefs'][0]['uncertainty']<1.0)
def test_duplicate_evidence_and_conflicts_are_idempotent():
    _,b,_=fixture(); a=belief(b,'a','A'); c=belief(b,'c','C'); first=b.add_evidence('e1',belief_id=a,stance='supports',weight=.5,reliability=.5,evidence_ref='same'); second=b.add_evidence('e2',belief_id=a,stance='supports',weight=.5,reliability=.5,evidence_ref='same'); x=b.create_conflict_set('x',belief_ids=[a,c],reason_code='contradiction'); y=b.create_conflict_set('y',belief_ids=[c,a],reason_code='contradiction'); require(second['result']['status']=='duplicate_evidence_ignored'); require(y['result']['status']=='duplicate_conflict_ignored'); require(len(b.snapshot()['conflict_sets'])==1)
def test_conflict_evaluation_retains_uncertainty_when_margin_is_small():
    _,b,_=fixture(); a=belief(b,'a','A',.55); c=belief(b,'c','C',.5); conflict=b.create_conflict_set('x',belief_ids=[a,c],reason_code='contradiction')['result']['conflict_id']; review=b.evaluate_conflict('review',conflict_id=conflict); require(review['result']['recommendation']=='retain_conflict_and_seek_evidence',review)
def test_conflict_resolution_supersedes_without_erasing_history():
    _,b,_=fixture(); a=belief(b,'a','A',.9); c=belief(b,'c','C',.2); conflict=b.create_conflict_set('x',belief_ids=[a,c],reason_code='contradiction')['result']['conflict_id']; b.resolve_conflict('r',conflict_id=conflict,preferred_belief_id=a,evidence_ref='decisive'); rows={r['belief_id']:r for r in b.snapshot()['beliefs']}; require(rows[c]['lifecycle_state']=='superseded'); require(len(rows[c]['update_history'])>1); require(b.snapshot()['conflict_sets'][0]['status']=='resolved')
def test_retracted_evidence_stays_accountable_but_loses_influence():
    _,b,_=fixture(); bid=belief(b,'b','A',.5); e=b.add_evidence('e',belief_id=bid,stance='supports',weight=1,reliability=1,evidence_ref='bad')['result']['evidence_id']; high=b.snapshot()['beliefs'][0]['confidence']; b.retract_evidence('r',belief_id=bid,evidence_id=e,correction_ref='correction'); row=b.snapshot()['beliefs'][0]; require(row['confidence']<high and row['evidence'][0]['active'] is False); require(row['evidence'][0]['correction_ref_digest'])
def test_commitment_review_recommends_reconsideration_under_conflict():
    m,b,_=fixture(); mid=motivation(m,'m'); a=belief(b,'a','A'); c=belief(b,'c','C'); b.create_conflict_set('x',belief_ids=[a,c],reason_code='contradiction',motivation_ids=[mid]); review=b.review_commitment('review',motivation_id=mid,belief_ids=[a,c]); require(review['result']['recommendation']=='reconsider',review)
def test_internal_commitment_can_be_suspended_without_action_authority():
    m,b,_=fixture(); mid=motivation(m,'m'); result=b.reconsider_commitment('reconsider',motivation_id=mid,decision='suspend',supporting_refs=['review']); require(result['result']['lifecycle_state']=='suspended'); require(result['result']['action_authority_changed'] is False); require(m.snapshot()['motivations'][0]['authority']['authorizes_action'] is False)
def test_provider_switch_does_not_change_belief_identity():
    m,b,root=fixture(); m.initialize_self_model('a',provider_id='provider-a'); bid=belief(b,'b','Stable identity'); m.initialize_self_model('z',provider_id='provider-b'); require(BeliefRevisionStore(root).snapshot()['beliefs'][0]['belief_id']==bid)
def test_belief_state_never_authorizes_executes_or_exposes_hidden_reasoning():
    _,b,_=fixture(); belief(b,'b','A'); snap=b.snapshot(); require(snap['authority_boundary']['belief_can_authorize_action'] is False and snap['authority_boundary']['belief_can_execute_action'] is False); require(all(not r['authority']['authorizes_action'] for r in snap['beliefs'])); require('chain_of_thought' not in json.dumps(snap).lower())

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    report={'suite':'v1104.7-motivation-conflict-belief-revision','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
