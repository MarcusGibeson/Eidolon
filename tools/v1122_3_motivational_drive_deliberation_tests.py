from pathlib import Path
import tempfile
from conscious_agent.motivational_pressure_signals import MotivationalPressureSignalStore
from conscious_agent.motivational_drive_candidates import MotivationalDriveCandidateStore
from conscious_agent.motivational_drive_deliberation import MotivationalDriveDeliberationStore
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 root=Path(td); sig=MotivationalPressureSignalStore(root); a=sig.register('s1',source_type='objective',source_id='o1',signal_type='objective_pull',durability=.8,transient=False,importance=.8,urgency=.4,confidence=.8,uncertainty=.2,structural_digest='d'); sid=a['result']['signal_id']; cand=MotivationalDriveCandidateStore(root,signals=sig); b=cand.register('c1',signal_ids=[sid],durable_drive_score=.8,transient_urgency_score=.3,importance=.8,uncertainty=.2,false_urgency_risk=.1,structural_digest='c'); cid=b['result']['candidate_id']; store=MotivationalDriveDeliberationStore(root); r=store.open('e1',candidate_id=cid); session=r['result']['session_id']; req(r['status']=='motivational_drive_deliberation_opened'); req(store.open('e1',candidate_id=cid)['idempotent']); req(store.open('e2',candidate_id=cid)['status']=='active_session_reused'); out=store.record_outcome('e3',session_id=session,outcome='retain_drive'); req(out['result']['outcome']=='retain_drive'); req(not out['result']['attention_selected'] and not out['result']['initiative_created']); snap=store.inspection_summary(); req(snap['contract_version']=='v1122.3'); req(snap['session_count']==1); req(snap['outcome_counts'].get('retain_drive')==1); req(not any(snap['authority_boundary'].values())); req(not snap['hidden_reasoning_exposed'])
print(f"v1122.3 motivational drive deliberation: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)
