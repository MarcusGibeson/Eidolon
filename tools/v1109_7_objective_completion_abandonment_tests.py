from pathlib import Path
import tempfile
from conscious_agent.objective_completion_abandonment import ObjectiveLifecycleStore
from conscious_agent.json_storage import write_json_atomic
from conscious_agent.long_horizon_objective import _default as od
from conscious_agent.objective_progress_evidence import _default as pd

def main():
 root=Path(tempfile.mkdtemp())/'cognition';store=ObjectiveLifecycleStore(root);store.objectives.path.parent.mkdir(parents=True,exist_ok=True)
 s=od();s['objectives']=[{'objective_id':'o1','success_criteria_count':2,'active_influence':True}];write_json_atomic(store.objectives.path,s,expected_type=dict,sort_keys=True)
 p=pd();p['claims']=[{'claim_id':'c-good','objective_id':'o1','progress_state':'completed','supported':True,'criteria_count':2},{'claim_id':'c-bad','objective_id':'o1','progress_state':'partial','supported':True,'criteria_count':2}];write_json_atomic(store.progress.path,p,expected_type=dict,sort_keys=True)
 a=store.review('e1',objective_id='o1',outcome='complete',completion_claim_id='c-bad');b=store.review('e2',objective_id='o1',outcome='complete',completion_claim_id='c-good');c=store.review('e3',objective_id='o1',outcome='abandon',reason='unsafe',remaining_milestone_count=1,reconsideration_eligible=True);d=store.review('e3',objective_id='o1',outcome='abandon',reason='unsafe');i=store.inspection_summary()
 tests=[a['result']['reason']=='completion_evidence_insufficient',b['status']=='lifecycle_review_recorded',c['status']=='lifecycle_review_recorded',d['idempotent'] is True,i['completed_count']==1,i['abandoned_count']==1,all(x.get('historical_record_preserved') for x in i['recent_reviews']),i['authority_boundary']['can_authorize'] is False]
 print(f"v1109.7 objective completion abandonment: {sum(tests)}/{len(tests)} passed");return 0 if all(tests) else 1
if __name__=='__main__':raise SystemExit(main())
