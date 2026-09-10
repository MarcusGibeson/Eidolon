from pathlib import Path
import tempfile,json
from conscious_agent.epistemic_coherence_signals import EpistemicCoherenceSignalStore
passed=0
def req(v):
 global passed; assert v; passed+=1
with tempfile.TemporaryDirectory() as td:
 s=EpistemicCoherenceSignalStore(Path(td)); r=s.register('e1',signal_type='structural_contradiction',left_record_type='belief',left_record_id='b1',right_record_type='knowledge',right_record_id='k1',severity=.8,structural_digest='d'); req(r['status']=='epistemic_coherence_signal_registered'); sid=r['result']['signal_id']; req(s.register('e1',signal_type='structural_contradiction',left_record_type='belief',left_record_id='b1')['idempotent']); req(s.register('e2',signal_type='structural_contradiction',left_record_type='belief',left_record_id='b1',right_record_type='knowledge',right_record_id='k1',severity=.8,structural_digest='d')['status']=='duplicate_signal_ignored'); snap=s.snapshot(); req(len(snap['signals'])==1 and snap['signals'][0]['severity']==.8); req(not any(snap['authority_boundary'].values())); req(s.revise('e3',sid,new_state='corrected')['result']['state']=='corrected'); req(s.snapshot()['signals'][0]['history'][-1]['change']=='corrected'); ins=s.inspection_summary(); req(not ins['hidden_reasoning_exposed'] and not ins['belief_text_exposed']); req(ins['runtime_mutated'] is False); req(ins['contract_version']=='v1119.0')
print(json.dumps({'passed':passed,'total':10,'suite':'v1119.0'}))
