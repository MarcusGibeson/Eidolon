from __future__ import annotations
import argparse, json, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from conscious_agent.autonomous_attention_agenda import AutonomousAttentionAgenda
from conscious_agent.motivation_agenda_arbitration import MotivationAgendaArbitrator


def require(v,d='failed'):
    if not v: raise AssertionError(d)


def fixture(epoch=100000.0):
    root=Path(tempfile.mkdtemp())/'runtime'/'cognition'
    clock=lambda:'2026-07-27T12:00:00.000Z'
    agenda=AutonomousAttentionAgenda(root,clock=clock)
    arb=MotivationAgendaArbitrator(root,agenda=agenda,clock=clock,epoch_clock=lambda:epoch)
    return root,agenda,arb


def add(agenda,event,ref,subject,**kw):
    return agenda.upsert_candidate(event,origin_type=kw.pop('origin_type','motivation'),origin_ref=ref,subject=subject,subject_key=ref,**kw)['result']['agenda_id']


def tests():
    rows=[]
    def run(n,f):
        try:f();rows.append({'name':n,'status':'pass'})
        except Exception as e:rows.append({'name':n,'status':'fail','detail':repr(e)})

    def selects_one_and_hands_to_bounded_path():
        _,a,r=fixture(); low=add(a,'l','l','low',salience=.2,urgency=.2,uncertainty=.2,confidence=.8); high=add(a,'h','h','high',origin_type='inquiry',salience=.9,urgency=.9,uncertainty=.8,confidence=.2)
        x=r.arbitrate('e',arbitration_key='window',gather_candidates=False,quiet=False,minimum_score=.1)
        require(x['result']['selected_agenda_id']==high,x); require(x['result']['selected_agenda_id']!=low,x); h=x['result']['reflection_handoff']; require(h['target_path']=='inquiry_reflection' and h['reflection_step_limit']==1,h); require(h['provider_calls_allowed']==0,h)

    def deliberate_no_selection_for_quiet_sleep_pause_resource_topic():
        for label,kwargs in [('quiet',{'quiet':True}),('sleep',{'sleeping':True,'quiet':False}),('pause',{'paused':True,'quiet':False}),('resource',{'resource_budget':0,'quiet':False}),('topic',{'blocked_topic_keys':['blocked'],'quiet':False})]:
            _,a,r=fixture(); add(a,'a','a','subject',topic_key='blocked',salience=.9,urgency=.9,uncertainty=.9,confidence=.1,resource_cost=.5)
            x=r.arbitrate(label,arbitration_key=label,gather_candidates=False,minimum_score=.1,**kwargs); require(x['result']['deliberate_no_selection'] is True,(label,x))

    def duplicate_tabs_restart_and_stale_workers_are_suppressed():
        root,a,r=fixture(); aid=add(a,'a','a','subject',salience=.9,urgency=.9,uncertainty=.9,confidence=.1)
        first=r.arbitrate('tab1',arbitration_key='same-window',worker_generation=3,gather_candidates=False,quiet=False,minimum_score=.1)
        second=MotivationAgendaArbitrator(root,agenda=AutonomousAttentionAgenda(root),clock=lambda:'2026-07-27T12:00:00.000Z',epoch_clock=lambda:100000.0).arbitrate('tab2',arbitration_key='same-window',worker_generation=3,gather_candidates=False,quiet=False,minimum_score=.1)
        stale=r.arbitrate('stale',arbitration_key='new-window',worker_generation=2,gather_candidates=False,quiet=False,minimum_score=.1)
        require(first['result']['selected_agenda_id']==aid,first); require(second['status']=='duplicate_arbitration_ignored',second); require(stale['status']=='stale_worker_no_selection',stale); require(AutonomousAttentionAgenda(root).snapshot()['agenda_items'][0]['attention_count']==1)

    def repetition_suppression_and_fairness_prevent_starvation():
        _,a,r=fixture(epoch=200000.0); first=add(a,'a','a','urgent recurring',salience=1,urgency=1,uncertainty=.5,confidence=.5); second=add(a,'b','b','enduring quiet subject',salience=.35,urgency=.25,uncertainty=.6,confidence=.4)
        x1=r.arbitrate('one',arbitration_key='one',gather_candidates=False,quiet=False,minimum_score=.05,cooldown_seconds=3600); require(x1['result']['selected_agenda_id']==first,x1)
        x2=r.arbitrate('two',arbitration_key='two',gather_candidates=False,quiet=False,minimum_score=.05,cooldown_seconds=3600); require(x2['result']['selected_agenda_id']==second,x2)

    def meaningful_update_allows_later_reselection():
        _,a,r=fixture(epoch=300000.0); aid=add(a,'a','a','subject',salience=.9,urgency=.9,uncertainty=.8,confidence=.2,source_revision=1)
        r.arbitrate('one',arbitration_key='one',gather_candidates=False,quiet=False,minimum_score=.1,cooldown_seconds=3600)
        a.upsert_candidate('update',origin_type='motivation',origin_ref='a',subject='subject changed',subject_key='a',salience=1,urgency=1,uncertainty=.9,confidence=.1,source_revision=2)
        x=r.arbitrate('two',arbitration_key='two',gather_candidates=False,quiet=False,minimum_score=.1,cooldown_seconds=3600); require(x['result']['selected_agenda_id']==aid,x)

    def provider_unavailable_remains_safe():
        _,a,r=fixture(); add(a,'a','a','subject',salience=.9,urgency=.9,uncertainty=.9,confidence=.1)
        x=r.arbitrate('e',arbitration_key='provider-down',gather_candidates=False,quiet=False,provider_available=False,minimum_score=.1); q=r.inspection_summary(); require(x['result']['selected_agenda_id'],x); require(q['provider_contacted'] is False and q['external_browsing_performed'] is False,q); require(q['action_authority_changed'] is False,q)

    def no_candidate_below_threshold_is_valid():
        _,a,r=fixture(); add(a,'a','a','tiny',salience=0,urgency=0,uncertainty=0,confidence=1,resource_cost=1)
        x=r.arbitrate('e',arbitration_key='none',gather_candidates=False,quiet=False,resource_budget=1,minimum_score=.9); require(x['result']['deliberate_no_selection'] is True,x)

    for n,f in [('single_selection_bounded_handoff',selects_one_and_hands_to_bounded_path),('boundary_no_selection',deliberate_no_selection_for_quiet_sleep_pause_resource_topic),('restart_tab_stale_dedup',duplicate_tabs_restart_and_stale_workers_are_suppressed),('fairness_repetition_suppression',repetition_suppression_and_fairness_prevent_starvation),('meaningful_change_reselection',meaningful_update_allows_later_reselection),('provider_unavailable_safety',provider_unavailable_remains_safe),('threshold_no_selection',no_candidate_below_threshold_is_valid)]:run(n,f)
    return rows

if __name__=='__main__':
    argparse.ArgumentParser().add_argument('--json',action='store_true'); rows=tests(); report={'suite':'v1107.1-motivation-to-agenda-arbitration','passed':sum(r['status']=='pass' for r in rows),'total':len(rows),'tests':rows}; print(json.dumps(report,indent=2)); raise SystemExit(0 if report['passed']==report['total'] else 1)
