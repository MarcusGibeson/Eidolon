from __future__ import annotations
import argparse, json, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from conscious_agent.autonomous_attention_agenda import AutonomousAttentionAgenda
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace
from conscious_agent.inquiry_residual_lineage import InquiryResidualLineage
from conscious_agent.prospective_planning import ProspectivePlanningStore


def require(value, detail="failed"):
    if not value: raise AssertionError(detail)


def tests():
    rows=[]
    def run(name, fn):
        try: fn(); rows.append({"name":name,"status":"pass"})
        except Exception as exc: rows.append({"name":name,"status":"fail","detail":repr(exc)})

    def persists_and_is_provider_neutral():
        root=Path(tempfile.mkdtemp())/'runtime'/'cognition'; a=AutonomousAttentionAgenda(root)
        a.upsert_candidate('e1',origin_type='motivation',origin_ref='m1',subject='Understand a durable concern',salience=.8,urgency=.7,uncertainty=.6,confidence=.4)
        q=AutonomousAttentionAgenda(root).inspection_summary(); require(q['active_candidate_count']==1,q); require(q['provider_contacted'] is False,q)

    def preserves_required_fields_and_state_separation():
        root=Path(tempfile.mkdtemp())/'runtime'/'cognition'; a=AutonomousAttentionAgenda(root)
        a.upsert_candidate('e',origin_type='unfinished_plan',origin_ref='p1',subject='Finish bounded plan',project_id='alpha',topic_key='planning',salience=.7,urgency=.6,uncertainty=.3,confidence=.7,eligible=False,eligibility_reasons=['cooldown'],eligible_after='2026-07-28T00:00:00Z',resource_cost=.2,resource_steps=1,lineage_refs=['r1'])
        item=a.snapshot()['agenda_items'][0]
        for key in ('origin','salience','urgency','uncertainty','confidence','eligibility','deferral_history','resource_cost_estimate','update_history'): require(key in item,item)
        require(item['state_separation']['state']=='agenda_candidacy',item); require(not any(item['state_separation'][k] for k in ('is_selected_attention','is_intention','is_proposal','is_authorized_action','is_completed_action')),item)

    def duplicate_events_semantics_and_stale_workers_do_not_duplicate():
        root=Path(tempfile.mkdtemp())/'runtime'/'cognition'; a=AutonomousAttentionAgenda(root)
        a.upsert_candidate('same',origin_type='inquiry',origin_ref='q1',subject='What remains?',subject_key='q1',source_revision=2,worker_generation=4)
        require(a.upsert_candidate('same',origin_type='inquiry',origin_ref='q1',subject='What remains?',subject_key='q1',source_revision=2,worker_generation=4)['idempotent'])
        a.upsert_candidate('semantic',origin_type='inquiry',origin_ref='q1',subject='What remains?',subject_key='q1',source_revision=2,worker_generation=4)
        stale=a.upsert_candidate('stale',origin_type='inquiry',origin_ref='q1',subject='Old wording',subject_key='q1',source_revision=1,worker_generation=2)
        require(stale['status']=='stale_candidate_update_ignored',stale); require(len(a.snapshot()['agenda_items'])==1,a.snapshot())
        times=iter(['2026-07-27T10:00:00.000Z','2026-07-27T10:01:00.000Z','2026-07-27T10:02:00.000Z'])
        b=AutonomousAttentionAgenda(Path(tempfile.mkdtemp())/'runtime'/'cognition',clock=lambda: next(times))
        bid=b.upsert_candidate('create',origin_type='inquiry',origin_ref='same',subject='No material change',subject_key='same')['result']['agenda_id']
        b.record_selection('select',bid,selection_receipt_id='receipt')
        refreshed=b.upsert_candidate('refresh',origin_type='inquiry',origin_ref='same',subject='No material change',subject_key='same')
        item=b.snapshot()['agenda_items'][0]
        require(refreshed['result']['meaningful_state_change'] is False,refreshed); require(item['last_meaningful_change_at']=='2026-07-27T10:00:00.000Z',item)

    def corrections_retractions_remain_historical_without_influence():
        root=Path(tempfile.mkdtemp())/'runtime'/'cognition'; a=AutonomousAttentionAgenda(root)
        created=a.upsert_candidate('e',origin_type='memory',origin_ref='mem1',subject='An old corrected memory')['result']['agenda_id']
        a.retire_candidate('r',created,outcome='corrected',reason_code='operator_correction',replacement_ref='mem2')
        state=a.snapshot(); require(len(state['agenda_items'])==1,state); require(state['agenda_items'][0]['active_influence'] is False,state); require(a.inspection_summary()['historical_inactive_count']==1)

    def rejects_post_hoc_dialogue_rationalization():
        root=Path(tempfile.mkdtemp())/'runtime'/'cognition'; a=AutonomousAttentionAgenda(root)
        try: a.upsert_candidate('e',origin_type='motivation',origin_ref='m',subject='Excuse generated reply',origin_phase='dialogue_already_generated')
        except ValueError: return
        raise AssertionError('post-hoc agenda candidate accepted')

    def gathers_established_motivation_inquiry_memory_and_events():
        root=Path(tempfile.mkdtemp())/'runtime'/'cognition'; m=MotivationStore(root)
        mid=m.record_motivation('m',kind='curiosity',summary='Why did the focused test fail?',cognitive_state='desire',urgency=.8,confidence=.5,origin_type='failure',origin_ref='test-1')['result']['motivation_id']
        workspace=InquiryWorkspace(root,motivation_store=m)
        parent=workspace.create_inquiry('q',motivation_id=mid,question='Which invariant was violated?',uncertainty=.9)['result']['inquiry_id']
        InquiryResidualLineage(root,workspace=workspace).create_child('residual',parent_inquiry_id=parent,residual_question='Which edge case remains unresolved?',uncertainty=.8)
        ProspectivePlanningStore(root,motivation_store=m,inquiry_store=workspace).create_plan('plan',subject='Finish the bounded validation plan',alternatives=[{'label':'Run focused tests'},{'label':'Defer with evidence'}],motivation_ids=[mid],inquiry_ids=[parent])
        a=AutonomousAttentionAgenda(root); result=a.sync_from_established_state('sync',memory_records=[{'memory_id':'mem','subject':'A prior conclusion remains relevant'}],structural_events=[{'event_id':'time','event_type':'time_change','subject':'A scheduled review became due'}])
        require(result['gathered_count']>=6,result); origins=a.inspection_summary()['origin_counts']; require(all(name in origins for name in ('motivation','inquiry','residual_question','unfinished_plan','memory','time_change')),origins)

    def inspection_is_redacted_and_authority_free():
        root=Path(tempfile.mkdtemp())/'runtime'/'cognition'; a=AutonomousAttentionAgenda(root)
        secret='private conversation evidence text'; a.upsert_candidate('e',origin_type='residual_question',origin_ref='q',subject=secret)
        q=a.inspection_summary(); require(secret not in json.dumps(q),q); require(all(v is False for k,v in q['authority_boundary'].items() if k!='operator_authority_unchanged'),q); require(q['authority_boundary']['operator_authority_unchanged'] is True,q)

    for name,fn in [
        ('persistence_provider_neutrality',persists_and_is_provider_neutral),('required_fields_state_separation',preserves_required_fields_and_state_separation),('dedupe_stale_workers',duplicate_events_semantics_and_stale_workers_do_not_duplicate),('correction_retraction_history',corrections_retractions_remain_historical_without_influence),('no_post_hoc_rationalization',rejects_post_hoc_dialogue_rationalization),('established_state_gathering',gathers_established_motivation_inquiry_memory_and_events),('redacted_authority_free_inspection',inspection_is_redacted_and_authority_free)]: run(name,fn)
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args()
    rows=tests(); report={'suite':'v1107.0-autonomous-attention-agenda-foundation','passed':sum(r['status']=='pass' for r in rows),'total':len(rows),'tests':rows}; print(json.dumps(report,indent=2)); raise SystemExit(0 if report['passed']==report['total'] else 1)
