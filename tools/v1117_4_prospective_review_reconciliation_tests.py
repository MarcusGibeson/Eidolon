from pathlib import Path
import json,tempfile
from conscious_agent.prospective_obligation_records import ProspectiveObligationStore
from conscious_agent.temporal_eligibility_arbitration import TemporalEligibilityArbitrator
from conscious_agent.prospective_review_sessions import ProspectiveReviewSessionStore
from conscious_agent.prospective_review_reconciliation import ProspectiveReviewReconciler
p=0
def req(x):
 global p;assert x;p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td);clock=lambda:'2026-08-03T12:00:00Z';o=ProspectiveObligationStore(r,clock=clock);oid=o.register('o1',origin_type='objective',origin_id='obj1',category='review',earliest_review_at='2026-08-01T00:00:00Z',target_window_start='2026-08-01T00:00:00Z',target_window_end='2026-08-02T00:00:00Z')['result']['obligation_id'];e=TemporalEligibilityArbitrator(r,clock=clock);er=e.arbitrate('e1',obligation_id=oid);req(er['result']['outcome']=='missed_window');s=ProspectiveReviewSessionStore(r,clock=clock);sid=s.open('s1',eligibility_id=er['result']['eligibility_id'])['result']['session_id'];q=ProspectiveReviewReconciler(r,clock=clock);a=q.reconcile('r1',session_id=sid);req(a['result']['outcome']=='missed_window_unresolved');req(not a['result']['success_inferred'] and not a['result']['failure_inferred']);req(q.reconcile('r2',session_id=sid,acknowledged=True)['result']['outcome']=='missed_window_acknowledged');req(q.reconcile('r3',session_id=sid,deferred_until='2026-08-05T00:00:00Z')['result']['outcome']=='bounded_deferral');req(q.reconcile('r4',session_id=sid,conflicting_session_ids=['other'])['result']['outcome']=='conflict_detected');req(q.reconcile('r4',session_id=sid)['idempotent']);req(not q.snapshot()['records'][0]['schedule_changed']);req(not any(q.inspection_summary()['authority_boundary'].values()));req(q.inspection_summary()['record_count']==4)
print(json.dumps({'passed':p,'total':10,'suite':'v1117.4'}))
