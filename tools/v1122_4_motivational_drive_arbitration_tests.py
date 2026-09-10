from pathlib import Path
import tempfile
from conscious_agent.motivational_pressure_signals import MotivationalPressureSignalStore
from conscious_agent.motivational_drive_candidates import MotivationalDriveCandidateStore
from conscious_agent.motivational_drive_deliberation import MotivationalDriveDeliberationStore
from conscious_agent.motivational_drive_arbitration import MotivationalDriveArbitrator
checks=[]
def req(x): checks.append(bool(x))
def session(root,n,operator=False):
 sig=MotivationalPressureSignalStore(root); s=sig.register(f's{n}',source_type='objective',source_id=f'o{n}',signal_type='objective_pull',durability=.8,transient=False,importance=.8,urgency=.4,confidence=.8,uncertainty=.2,structural_digest=n)['result']['signal_id']; cand=MotivationalDriveCandidateStore(root,signals=sig); c=cand.register(f'c{n}',signal_ids=[s],durable_drive_score=.8,transient_urgency_score=.3,importance=.8,uncertainty=.2,false_urgency_risk=.1,operator_review_required=operator,structural_digest=n)['result']['candidate_id']; return MotivationalDriveDeliberationStore(root).open(f'e{n}',candidate_id=c)['result']['session_id']
with tempfile.TemporaryDirectory() as td:
 root=Path(td); arb=MotivationalDriveArbitrator(root)
 req(arb.arbitrate('a1',session_id=session(root,'1'),durable_drive_strength=.9,importance=.8,uncertainty=.2)['arbitration']['outcome']=='prioritize_for_bounded_review')
 req(arb.arbitrate('a2',session_id=session(root,'2'),durable_drive_strength=.2,transient_urgency=.9,false_urgency_risk=.9)['arbitration']['outcome']=='decay_transient_urgency')
 req(arb.arbitrate('a3',session_id=session(root,'3'),recovery_constraint=.9)['arbitration']['outcome']=='defer_drive')
 req(arb.arbitrate('a4',session_id=session(root,'4'),overlap_strength=.9)['arbitration']['outcome']=='merge_overlapping_drive')
 req(arb.arbitrate('a5',session_id=session(root,'5'),durable_drive_strength=.1,transient_urgency=.1)['arbitration']['outcome']=='deliberate_non_selection')
 req(arb.arbitrate('a6',session_id=session(root,'6'),force_unresolved=True)['arbitration']['outcome']=='unresolved')
 req(arb.arbitrate('a7',session_id=session(root,'7',True))['arbitration']['outcome']=='requires_operator_review')
 x=arb.inspection_summary(); req(x['contract_version']=='v1122.4'); req(not any(x[k] for k in ('attention_selected','initiative_created','message_sent','external_action_executed'))); req(not any(x['authority_boundary'].values()))
print(f"v1122.4 motivational drive arbitration: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)
