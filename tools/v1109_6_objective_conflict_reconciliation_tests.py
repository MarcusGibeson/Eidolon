from pathlib import Path
import tempfile
from conscious_agent.objective_conflict_reconciliation import ObjectiveConflictStore

def main():
 root=Path(tempfile.mkdtemp())/'cognition';store=ObjectiveConflictStore(root)
 # seed objective ledger directly with bounded structural fixtures
 store.objectives.path.parent.mkdir(parents=True,exist_ok=True)
 from conscious_agent.json_storage import write_json_atomic
 from conscious_agent.long_horizon_objective import _default
 s=_default();s['objectives']=[{'objective_id':'o1','active_influence':True},{'objective_id':'o2','active_influence':True},{'objective_id':'o3','active_influence':True}];write_json_atomic(store.objectives.path,s,expected_type=dict,sort_keys=True)
 a=store.reconcile('e1',objective_ids=['o1','o2'],outcome='unresolved');b=store.reconcile('e1',objective_ids=['o1','o2'],outcome='unresolved');c=store.reconcile('e2',objective_ids=['o1','missing'],outcome='coexist');d=store.reconcile('e3',objective_ids=['o1','o2'],outcome='replaced',replacement_objective_id='o3');i=store.inspection_summary()
 tests=[a['status']=='conflict_recorded',b['idempotent'] is True,c['result']['reason']=='objective_missing',d['status']=='conflict_recorded',i['decision_count']==2,i['unresolved_count']==1,i['authority_boundary']['can_execute'] is False,all(x.get('historical_records_preserved') for x in i['recent_decisions'])]
 print(f"v1109.6 objective conflict reconciliation: {sum(tests)}/{len(tests)} passed");return 0 if all(tests) else 1
if __name__=='__main__':raise SystemExit(main())
