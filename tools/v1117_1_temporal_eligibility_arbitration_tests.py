from pathlib import Path
import tempfile,json
from conscious_agent.prospective_obligation_records import ProspectiveObligationStore
from conscious_agent.temporal_eligibility_arbitration import TemporalEligibilityArbitrator
passed=0
def req(v):
 global passed
 assert v;passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); clock=lambda:'2026-08-01T00:00:00Z'; s=ProspectiveObligationStore(root,clock=clock)
 oid=s.register('o1',origin_type='active_inquiry',origin_id='inq-1',category='evidence_follow_up',earliest_review_at='2026-08-02T00:00:00Z',target_window_start='2026-08-02T00:00:00Z',target_window_end='2026-08-03T00:00:00Z',stale_after='2026-08-05T00:00:00Z',precondition_ids=['p1'])['result']['obligation_id']; a=TemporalEligibilityArbitrator(root,clock=clock)
 def outcome(e,**kw):return a.arbitrate(e,obligation_id=oid,**kw)['result']['outcome']
 req(outcome('e1',now_at='2026-08-01T00:00:00Z')=='awaiting_prerequisite'); req(outcome('e2',now_at='2026-08-01T00:00:00Z',satisfied_preconditions=['p1'])=='not_yet_eligible'); req(outcome('e3',now_at='2026-08-02T12:00:00Z',satisfied_preconditions=['p1'])=='eligible_for_bounded_review'); req(outcome('e4',now_at='2026-08-02T12:00:00Z',satisfied_preconditions=['p1'],cognitive_load=.6)=='eligible_reduced_budget'); req(outcome('e5',now_at='2026-08-02T12:00:00Z',satisfied_preconditions=['p1'],cognitive_load=.9)=='deferred_by_cognitive_load'); req(outcome('e6',now_at='2026-08-02T12:00:00Z',satisfied_preconditions=['p1'],recovery_required=True)=='deferred_by_recovery_requirement'); req(outcome('e7',now_at='2026-08-04T00:00:00Z',satisfied_preconditions=['p1'])=='missed_window'); req(a.arbitrate('e7',obligation_id=oid,now_at='2026-08-04T00:00:00Z',satisfied_preconditions=['p1'])['idempotent']); ins=a.inspection_summary(); req(ins['time_passing_is_outcome_evidence'] is False); req(not any(ins['authority_boundary'].values()))
print(json.dumps({'passed':passed,'total':10,'suite':'v1117.1'}))
