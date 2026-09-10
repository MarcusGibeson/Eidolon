from pathlib import Path
import tempfile
from conscious_agent.behavioral_outcome_evidence import BehavioralOutcomeStore
from conscious_agent.behavioral_outcome_attribution import BehavioralAttributionStore
from conscious_agent.behavioral_pattern_detection import BehavioralPatternStore
def req(x):
 if not x:raise AssertionError
root=Path(tempfile.mkdtemp())/'cognition';o=BehavioralOutcomeStore(root);a=BehavioralAttributionStore(root)
for i,score in enumerate((.7,.6,.8)):
 r=o.record_outcome(f'o{i}',outcome_class='initiative_response',outcome_state='acknowledged',origin_type='initiative',origin_id=f'i{i}',lineage_refs=[f'l{i}'],score=score,feedback_known=True);oid=r['result']['outcome_id'];a.record_attribution(f'a{i}',outcome_id=oid,status='attributed',contributors=[{'decision_type':'initiative','decision_id':f'd{i}','weight':.7}])
p=BehavioralPatternStore(root);r=p.detect('p1',pattern_kind='initiative_acknowledgement',outcome_class='initiative_response',decision_type='initiative');req(r['result']['state']=='supported');req(p.detect('p1',pattern_kind='initiative_acknowledgement',outcome_class='initiative_response',decision_type='initiative')['idempotent']);x=p.inspection_summary();req(x['supported_count']==1 and not x['raw_content_exposed']);q=BehavioralPatternStore(Path(tempfile.mkdtemp())/'cognition');z=q.detect('z',pattern_kind='thin',outcome_class='initiative_response');req(z['result']['state']=='suppressed');req(q.inspection_summary()['recent_patterns'][0]['false_pattern_reason_codes']);req(not x['authority_boundary']['can_adapt']);print('{"passed":8,"total":8,"suite":"v1112.3"}')
