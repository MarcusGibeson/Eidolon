from pathlib import Path
import tempfile
from conscious_agent.supervised_repair_execution_checkpoint import build_supervised_repair_execution_checkpoint
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=build_supervised_repair_execution_checkpoint(Path(td)/'cognition')
 check('checkpoint 12/12',r['ok'] and r['passed']==r['total']==12)
 check('contracts',r['materialization']['contract_version']=='v1141.3' and r['execution']['contract_version']=='v1141.4')
 check('authority separation',not r['source_modified'] and not r['installation_modified'])
 check('privacy',not r['patch_text_exposed'] and not r['commands_exposed'] and not r['logs_exposed'] and not r['hidden_reasoning_exposed'])
 check('desktop pending',r['desktop_verification']=='pending')
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
