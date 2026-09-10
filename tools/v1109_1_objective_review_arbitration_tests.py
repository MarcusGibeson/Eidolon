from pathlib import Path
import tempfile
from conscious_agent.json_storage import write_json_atomic
from conscious_agent.bounded_intention_formation import BoundedIntentionStore
from conscious_agent.long_horizon_objective import LongHorizonObjectiveStore
from conscious_agent.objective_review_arbitration import ObjectiveReviewArbitrator

def run():
 root=Path(tempfile.mkdtemp())/'cognition';i=BoundedIntentionStore(root);s=i._load();s['intentions'].append({'intention_id':'i1','agenda_id':'a1','reflection_id':'r1','subject_digest':'d1','active':True});write_json_atomic(i.path,s,expected_type=dict,sort_keys=True)
 LongHorizonObjectiveStore(root).register('e1',intention_id='i1',success_criteria=['done'],salience=.9,urgency=.8);arb=ObjectiveReviewArbitrator(root);a=arb.select('s1');b=arb.select('s1');state=arb._load();state['controls']['quiet']=True;write_json_atomic(arb.path,state,expected_type=dict,sort_keys=True);c=arb.select('s2')
 tests=[a['status']=='objective_selected_for_review',a['receipt']['reflection_handoff_eligible'] is True,a['receipt']['proposal_id']=='',b['idempotent'] is True,c['status']=='deliberate_no_selection',c['receipt']['reason_code']=='control_boundary',arb.inspection_summary()['provider_contacted'] is False]
 print({'suite':'v1109.1','passed':sum(tests),'total':len(tests)});return all(tests)
if __name__=='__main__':raise SystemExit(0 if run() else 1)
