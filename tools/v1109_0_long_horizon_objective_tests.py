from pathlib import Path
import tempfile
from conscious_agent.bounded_intention_formation import BoundedIntentionStore
from conscious_agent.long_horizon_objective import LongHorizonObjectiveStore

def run():
 root=Path(tempfile.mkdtemp())/'cognition'; intentions=BoundedIntentionStore(root)
 # seed directly through established store shape to avoid provider/reflection coupling
 s=intentions._load();s['intentions'].append({'intention_id':'i1','agenda_id':'a1','reflection_id':'r1','subject_digest':'d1','active':True});from conscious_agent.json_storage import write_json_atomic;write_json_atomic(intentions.path,s,expected_type=dict,sort_keys=True)
 store=LongHorizonObjectiveStore(root);a=store.register('e1',intention_id='i1',success_criteria=['criterion one']);b=store.register('e1',intention_id='i1',success_criteria=['criterion one']);snap=store.inspection_summary();row=snap['recent_objectives'][0]
 tests=[a['status']=='objective_registered',b['idempotent'] is True,snap['objective_count']==1,row['success_criteria_count']==1,row['proposal_id']==row['authorization_id']==row['action_id']=='',snap['authority_boundary']['can_execute'] is False,snap['private_content_exposed'] is False]
 print({'suite':'v1109.0','passed':sum(tests),'total':len(tests)});return all(tests)
if __name__=='__main__':raise SystemExit(0 if run() else 1)
