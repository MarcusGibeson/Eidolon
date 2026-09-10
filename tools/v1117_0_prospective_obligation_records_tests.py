from pathlib import Path
import tempfile, json
from conscious_agent.prospective_obligation_records import ProspectiveObligationStore
passed=0
def req(v):
 global passed
 assert v; passed+=1
with tempfile.TemporaryDirectory() as td:
 s=ProspectiveObligationStore(Path(td),clock=lambda:'2026-08-01T00:00:00Z')
 kw=dict(origin_type='decision_commitment',origin_id='decision-1',category='reconsideration',earliest_review_at='2026-08-02T00:00:00Z',target_window_start='2026-08-02T00:00:00Z',target_window_end='2026-08-03T00:00:00Z',stale_after='2026-08-05T00:00:00Z',precondition_ids=['p1'],dependency_ids=['d1'],importance=.8,urgency=.7,structural_digest='abc')
 a=s.register('e1',**kw); req(a['status']=='obligation_registered'); oid=a['result']['obligation_id']; req(s.register('e1',**kw)['idempotent']); req(s.register('e2',**kw)['status']=='duplicate_obligation_ignored'); snap=s.snapshot(); req(len(snap['obligations'])==1); req(snap['obligations'][0]['notification_id']==''); req(not any(snap['authority_boundary'].values())); req(s.revise('e3',oid,new_state='corrected')['result']['state']=='corrected'); req(len(s.snapshot()['obligations'][0]['history'])==2); ins=s.inspection_summary(); req(not ins['hidden_reasoning_exposed'] and not ins['raw_messages_exposed']); req(ins['runtime_mutated'] is False)
print(json.dumps({'passed':passed,'total':10,'suite':'v1117.0'}))
