from pathlib import Path
import json,tempfile
from conscious_agent.behavioral_adaptation_proposals import BehavioralAdaptationProposalStore
from conscious_agent.behavioral_adaptation_lifecycle import BehavioralAdaptationLifecycleStore
passed=0
def req(x):
 global passed
 assert x;passed+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';r.mkdir();(r/'behavioral_self_evaluations.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1112.4','evaluations':[],'hypotheses':[{'hypothesis_id':'h1','state':'unreviewed','evidence_count':5}],'processed_events':[],'revision':0,'updated_at':'','controls':{},'state_separation':{},'authority_boundary':{}}))
 p=BehavioralAdaptationProposalStore(r);pid=p.propose('p1',hypothesis_id='h1',scope_code='restraint_weight',requested_delta=-.1)['result']['proposal_id'];l=BehavioralAdaptationLifecycleStore(r)
 try:l.decide('d0',proposal_id=pid,new_state='suspended',operator_confirmation=False);req(False)
 except PermissionError:req(True)
 x=l.decide('d1',proposal_id=pid,new_state='approved_for_bounded_apply',operator_confirmation=True,decision_code='operator_review');req(x['ok']);row=p._load()['proposals'][0];req(row['approval_granted'] and not row['authorization_granted'] and not row['applied']);req(l._load()['weight_receipts'][0]['receipt_state']=='approved_not_applied');req(not l._load()['weight_receipts'][0]['behavior_mutated']);req(l.decide('d1',proposal_id=pid,new_state='approved_for_bounded_apply',operator_confirmation=True)['idempotent']);x=l.decide('d2',proposal_id=pid,new_state='rolled_back',operator_confirmation=True);req(x['result']['state']=='rolled_back');req(l.inspection_summary()['authority_boundary']['can_apply'] is False)
print(json.dumps({'passed':passed,'total':8,'suite':'v1112.7'}))
