from pathlib import Path
import json,tempfile
from conscious_agent.prospective_obligation_records import ProspectiveObligationStore
from conscious_agent.temporal_eligibility_arbitration import TemporalEligibilityArbitrator
from conscious_agent.prospective_review_sessions import ProspectiveReviewSessionStore
p=0
def req(x):
 global p;assert x;p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td);clock=lambda:'2026-08-01T12:00:00Z';o=ProspectiveObligationStore(r,clock=clock);x=o.register('o1',origin_type='objective',origin_id='obj1',category='review',earliest_review_at='2026-08-01T00:00:00Z',target_window_start='2026-08-01T00:00:00Z',target_window_end='2026-08-02T00:00:00Z');oid=x['result']['obligation_id'];e=TemporalEligibilityArbitrator(r,clock=clock);y=e.arbitrate('e1',obligation_id=oid);eid=y['result']['eligibility_id'];s=ProspectiveReviewSessionStore(r,clock=clock);z=s.open('s1',eligibility_id=eid);req(z['status']=='review_session_opened');sid=z['result']['session_id'];req(s.open('s1',eligibility_id=eid)['idempotent']);req(s.open('s2',eligibility_id=eid)['status']=='duplicate_session_ignored');req(s.snapshot()['sessions'][0]['review_performed'] is False);req(not any(s.inspection_summary()['authority_boundary'].values()));req(s.transition('t1',sid,new_state='acknowledged')['result']['state']=='acknowledged');req(s.transition('t2',sid,new_state='deferred',deferred_until='2026-08-03T00:00:00Z',reason_code='capacity')['result']['state']=='deferred');req(bool(s.snapshot()['sessions'][0]['deferral_reason_digest']));req(not s.inspection_summary()['hidden_reasoning_exposed']);req(s.inspection_summary()['session_count']==1)
print(json.dumps({'passed':p,'total':10,'suite':'v1117.3'}))
