from pathlib import Path
import tempfile, json
from conscious_agent.prospective_obligation_records import ProspectiveObligationStore
from conscious_agent.prospective_outcome_evidence import ProspectiveOutcomeEvidenceStore, build_prospective_outcome_evidence_inspection
p=0
def req(x):
 global p; assert x; p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td); o=ProspectiveObligationStore(r); made=o.register('o1',origin_type='objective',origin_id='obj',category='review',earliest_review_at='2030-01-01T00:00:00Z',target_window_start='2030-01-01T00:00:00Z',target_window_end='2030-01-02T00:00:00Z'); oid=made['result']['obligation_id']; s=ProspectiveOutcomeEvidenceStore(r); a=s.record('e1',obligation_id=oid,outcome='fulfilled',source_receipt_ids=['receipt-1']); req(a['ok']); req(not a['idempotent']); req(s.record('e1',obligation_id=oid,outcome='fulfilled')['idempotent']); snap=s.snapshot(); req(len(snap['records'])==1); req(snap['records'][0]['content_free']); req(not snap['records'][0]['obligation_changed']); req(not snap['records'][0]['schedule_changed']); x=build_prospective_outcome_evidence_inspection(r); req(x['contract_version']=='v1117.6'); req(not x['hidden_reasoning_exposed']); req(not any(x['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':10,'suite':'v1117.6'}))
