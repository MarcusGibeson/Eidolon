from pathlib import Path
import tempfile,json
from conscious_agent.evidence_change_signals import EvidenceChangeSignalStore
passed=0
def req(v):
 global passed; assert v; passed+=1
with tempfile.TemporaryDirectory() as td:
 s=EvidenceChangeSignalStore(Path(td),clock=lambda:'2026-08-02T00:00:00Z')
 kw=dict(belief_id='belief-1',evidence_id='evidence-1',change_type='evidence_corrected',confidence_delta=-.2,uncertainty_delta=.3,contradiction_severity=.7,structural_digest='abc')
 a=s.register('e1',**kw); req(a['status']=='evidence_change_signal_registered'); sid=a['result']['signal_id']; req(s.register('e1',**kw)['idempotent']); req(s.register('e2',**kw)['status']=='duplicate_signal_ignored'); req(len(s.snapshot()['signals'])==1); req(s.snapshot()['signals'][0]['belief_revision_id']==''); req(not any(s.snapshot()['authority_boundary'].values())); req(s.revise('e3',sid,new_state='corrected')['result']['state']=='corrected'); req(len(s.snapshot()['signals'][0]['history'])==2); ins=s.inspection_summary(); req(not ins['hidden_reasoning_exposed'] and not ins['evidence_text_exposed']); req(ins['runtime_mutated'] is False)
print(json.dumps({'passed':passed,'total':10,'suite':'v1118.0'}))
