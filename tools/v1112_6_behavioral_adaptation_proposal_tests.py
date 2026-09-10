from pathlib import Path
import json,tempfile
from conscious_agent.behavioral_adaptation_proposals import BehavioralAdaptationProposalStore
passed=0
def req(x):
 global passed
 assert x;passed+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';r.mkdir();h={'schema_version':'1','contract_version':'v1112.4','evaluations':[],'hypotheses':[{'hypothesis_id':'h1','state':'unreviewed','evidence_count':5}], 'processed_events':[],'revision':0,'updated_at':'','controls':{},'state_separation':{},'authority_boundary':{}}
 (r/'behavioral_self_evaluations.json').write_text(json.dumps(h));s=BehavioralAdaptationProposalStore(r)
 x=s.propose('e1',hypothesis_id='h1',scope_code='attention_weight',requested_delta=.4,uncertainty=.3,rationale_code='reduce_repeat')
 req(x['ok'] and x['result']['state']=='pending_operator_review');p=s._load()['proposals'][0];req(p['requested_delta']==.15 and 'delta_clamped' in p['reason_codes']);req(not p['approval_granted'] and not p['authorization_granted'] and not p['applied']);req(s.propose('e1',hypothesis_id='h1',scope_code='attention_weight',requested_delta=.4)['idempotent']);req(s.propose('e2',hypothesis_id='h1',scope_code='attention_weight',requested_delta=.4,rationale_code='reduce_repeat')['result']['status']=='duplicate_proposal_ignored');req(s.inspection_summary()['raw_content_exposed'] is False);req(s.inspection_summary()['state_separation']['proposal_is_approval'] is False);req(s.inspection_summary()['authority_boundary']['can_apply'] is False)
print(json.dumps({'passed':passed,'total':8,'suite':'v1112.6'}))
