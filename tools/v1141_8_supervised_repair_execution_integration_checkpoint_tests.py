from pathlib import Path
import tempfile
from conscious_agent.supervised_repair_execution_integration_checkpoint import build_supervised_repair_execution_integration_checkpoint
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=build_supervised_repair_execution_integration_checkpoint(Path(td)/'cognition')
 check('checkpoint 16/16',r['ok'] and r['passed']==r['total']==16)
 check('contracts',r['continuity']['contract_version']=='v1141.6' and r['reliability']['contract_version']=='v1141.7')
 check('evidence boundary',r['operator_candidate_evidence_only'] and not r['installation_eligible'])
 check('authority separation',not r['source_modified'] and not r['installation_modified'])
 check('privacy',not r['patch_text_exposed'] and not r['commands_exposed'] and not r['logs_exposed'] and not r['hidden_reasoning_exposed'])
 check('desktop pending',r['desktop_verification']=='pending')
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
