from pathlib import Path
import tempfile, json
from conscious_agent.prospective_obligation_records import ProspectiveObligationStore
from conscious_agent.prospective_outcome_evidence import ProspectiveOutcomeEvidenceStore
from conscious_agent.temporal_reliability_patterns import TemporalReliabilityAnalyzer, build_temporal_reliability_inspection
p=0
def req(x):
 global p; assert x; p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td); os=ProspectiveObligationStore(r); ev=ProspectiveOutcomeEvidenceStore(r)
 for i,out in enumerate(['not_fulfilled','not_fulfilled','expired_without_evidence']):
  oid=os.register(f'o{i}',origin_type='objective',origin_id=f'obj{i}',category='review',earliest_review_at='2030-01-01T00:00:00Z',target_window_start='2030-01-01T00:00:00Z',target_window_end='2030-01-02T00:00:00Z')['result']['obligation_id']; ev.record(f'e{i}',obligation_id=oid,outcome=out)
 a=TemporalReliabilityAnalyzer(r); z=a.analyze('r1',minimum_evidence=3); req(z['ok']); q=z['result']; req(q['sufficient_evidence']); req(q['drift_status']=='adverse_drift'); req(q['recurrence_status']=='repeated_nonfulfillment'); req(bool(q['proposal_id'])); req(not q['schedule_changed']); req(a.analyze('r1',minimum_evidence=3)['idempotent']); x=build_temporal_reliability_inspection(r); req(x['proposal_count']==1); req(all(y['operator_review_required'] and not y['applied'] for y in x['recent_proposals'])); req(not any(x['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':10,'suite':'v1117.7'}))
