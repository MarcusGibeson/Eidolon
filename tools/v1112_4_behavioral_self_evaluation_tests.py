from pathlib import Path
import tempfile
from conscious_agent.behavioral_outcome_evidence import BehavioralOutcomeStore
from conscious_agent.behavioral_outcome_attribution import BehavioralAttributionStore
from conscious_agent.behavioral_pattern_detection import BehavioralPatternStore
from conscious_agent.behavioral_self_evaluation import BehavioralSelfEvaluationStore
def req(x):
 if not x:raise AssertionError
root=Path(tempfile.mkdtemp())/'cognition';o=BehavioralOutcomeStore(root);a=BehavioralAttributionStore(root)
for i in range(4):
 r=o.record_outcome(f'o{i}',outcome_class='attention_utility',outcome_state='useful',origin_type='agenda',origin_id=f'i{i}',lineage_refs=[f'l{i}'],score=.7,feedback_known=True);a.record_attribution(f'a{i}',outcome_id=r['result']['outcome_id'],status='attributed',contributors=[{'decision_type':'agenda','decision_id':f'd{i}','weight':.6}])
p=BehavioralPatternStore(root);pid=p.detect('p',pattern_kind='useful_attention',outcome_class='attention_utility',decision_type='agenda')['result']['pattern_id'];e=BehavioralSelfEvaluationStore(root);r=e.evaluate('e',pattern_id=pid,evaluation_code='attention_helpful',proposed_direction_code='preserve_weighting',uncertainty=.3);req(r['result']['outcome']=='hypothesis_eligible');req('hypothesis_id' in r['result']);req(e.evaluate('e',pattern_id=pid,evaluation_code='attention_helpful')['idempotent']);x=e.inspection_summary();req(x['hypothesis_count']==1 and not x['behavior_changed']);req(not x['recent_hypotheses'][0]['adaptation_proposal_created']);req(not x['authority_boundary']['can_adapt']);req(not x['raw_content_exposed']);print('{"passed":8,"total":8,"suite":"v1112.4"}')
