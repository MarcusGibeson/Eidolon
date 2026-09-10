from pathlib import Path
import tempfile
from conscious_agent.repair_execution_continuity import RepairExecutionContinuityStore
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/'cognition'; s=RepairExecutionContinuityStore(root)
 r=s.reconcile('evt-1',worker_id='worker-a')
 check('reconcile succeeds',r['ok'] and r['status']=='reconciled')
 check('idempotent retry',s.reconcile('evt-1')['idempotent'])
 i=s.inspection_summary()
 check('continuity contract',i['contract_version']=='v1141.6' and i['restart_safe'])
 check('suppression',i['stale_worker_suppression'] and i['duplicate_suppression'])
 check('authority separation',not i['source_modified'] and not i['installation_modified'] and not i['approval_created'] and not i['authorization_created'])
 check('privacy',not i['patch_text_exposed'] and not i['commands_exposed'] and not i['logs_exposed'] and not i['hidden_reasoning_exposed'])
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
