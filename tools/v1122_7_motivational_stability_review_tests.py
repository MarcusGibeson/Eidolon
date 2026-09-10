from pathlib import Path
import json,tempfile
from conscious_agent.motivational_outcome_lineage import MotivationalOutcomeLineageStore
from conscious_agent.motivational_stability_review import MotivationalStabilityReviewer
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); l=MotivationalOutcomeLineageStore(root); r=MotivationalStabilityReviewer(root); req(r.review(drive_id='none')['status']=='insufficient_evidence')
 for n,out in enumerate(['retain_drive','decay_transient_urgency','retain_drive'],1): l.record(f'e{n}',drive_id='d1',session_id=f's{n}',outcome=out)
 x=r.review(drive_id='d1',operator_review_required=True); req(x['sample_size']==3); req(x['motivational_instability_detected']); req(x['reversal_count']==2); req(x['false_pattern_suppressed'] is False); req(x['operator_review_proposal']['applied'] is False); req(not x['attention_selected'] and not x['initiative_created']); req(not x['message_sent'] and not x['notification_created']); req(not x['approval_granted'] and not x['authorization_granted'] and not x['external_action_executed']); req(r.inspection_summary()['contract_version']=='v1122.7')
print(json.dumps({'passed':passed,'total':10,'suite':'v1122.7'}))
