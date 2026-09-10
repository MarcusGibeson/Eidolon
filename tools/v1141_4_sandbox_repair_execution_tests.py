from pathlib import Path
import tempfile
from conscious_agent.sandbox_repair_materialization import SandboxRepairMaterializationStore, EXACT_CONFIRMATION as MC
from conscious_agent.sandbox_repair_execution import SandboxRepairExecutionStore, EXACT_CONFIRMATION as EC
from conscious_agent.json_storage import write_json_atomic
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 root=Path(td); runtime=root/'runtime'; source=root/'source'; source.mkdir(); (source/'fixture.py').write_text('print("before")\n'); runtime.mkdir()
 write_json_atomic(runtime/'sandbox_repair_work_orders.json',{'schema_version':'1','contract_version':'v1141.1','work_orders':[{'work_order_id':'wo','eligibility_id':'el','state':'ready_for_operator_confirmed_materialization','authorized_bounds_match':True,'approval_id':'ap','authorization_id':'au','reviewed_artifact_set_digest':'d','execution_token_id':'tok'}],'processed_events':[],'revision':1,'updated_at':''},expected_type=dict,sort_keys=True)
 m=SandboxRepairMaterializationStore(runtime); mr=m.materialize('m1',work_order_id='wo',confirmation=MC,operator_id='op',worker_id='wk',source_root=source,copy_paths=['fixture.py']); mid=mr['materialization_id']; wid=m.snapshot()['materializations'][0]['workspace_id']; workspace=runtime/'repair_sandboxes'/wid
 e=SandboxRepairExecutionStore(runtime); bad=e.execute('x0',materialization_id=mid,confirmation='bad',changes=[],commands=[],test_commands=[]); check('execution confirmation',not bad['ok'])
 good=e.execute('x1',materialization_id=mid,confirmation=EC,changes=[{'path':'fixture.py','content':'print("after")\n'}],commands=[['python','-m','py_compile','fixture.py']],test_commands=[['python','fixture.py']],timeout_seconds=10); check('bounded execution',good['ok'] and good['status']=='completed' and good['result_count']==2)
 check('sandbox only',workspace.joinpath('fixture.py').read_text()=='print("after")\n' and source.joinpath('fixture.py').read_text()=='print("before")\n')
 rb=e.rollback('r1',execution_id=good['execution_id'],confirmation=EC); check('rollback',rb['status']=='rollback_completed' and workspace.joinpath('fixture.py').read_text()=='print("before")\n')
 check('single use',not e.execute('x2',materialization_id=mid,confirmation=EC,changes=[],commands=[],test_commands=[])['ok'])
 check('privacy',not e.inspection_summary()['commands_exposed'] and not e.inspection_summary()['logs_exposed'])
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
