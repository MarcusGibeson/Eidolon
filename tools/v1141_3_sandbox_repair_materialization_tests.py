from pathlib import Path
import json, tempfile
from conscious_agent.sandbox_repair_materialization import SandboxRepairMaterializationStore, EXACT_CONFIRMATION
from conscious_agent.json_storage import write_json_atomic
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 root=Path(td); runtime=root/'runtime'; source=root/'source'; source.mkdir(); (source/'fixture.py').write_text('print("before")\n')
 wo={'schema_version':'1','contract_version':'v1141.1','work_orders':[{'work_order_id':'wo-1','eligibility_id':'el-1','state':'ready_for_operator_confirmed_materialization','authorized_bounds_match':True,'approval_id':'ap-1','authorization_id':'au-1','reviewed_artifact_set_digest':'d1','execution_token_id':'tok-1'}],'processed_events':[],'revision':1,'updated_at':''}
 runtime.mkdir(parents=True); write_json_atomic(runtime/'sandbox_repair_work_orders.json',wo,expected_type=dict,sort_keys=True)
 store=SandboxRepairMaterializationStore(runtime)
 bad=store.materialize('e0',work_order_id='wo-1',confirmation='no',operator_id='op',worker_id='wk',source_root=source,copy_paths=['fixture.py']); check('exact confirmation',not bad['ok'])
 good=store.materialize('e1',work_order_id='wo-1',confirmation=EXACT_CONFIRMATION,operator_id='op',worker_id='wk',source_root=source,copy_paths=['fixture.py']); check('materialized',good['ok'] and good['status']=='materialized')
 snap=store.snapshot(); row=snap['materializations'][0]; workspace=runtime/'repair_sandboxes'/row['workspace_id']; check('isolated copy',workspace.joinpath('fixture.py').read_text()=='print("before")\n' and source.joinpath('fixture.py').read_text()=='print("before")\n')
 again=store.materialize('e1',work_order_id='wo-1',confirmation=EXACT_CONFIRMATION,operator_id='op',worker_id='wk',source_root=source,copy_paths=['fixture.py']); check('idempotent',again['idempotent'])
 check('privacy',not store.inspection_summary()['raw_source_exposed'] and not store.inspection_summary()['patch_text_exposed'])
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
