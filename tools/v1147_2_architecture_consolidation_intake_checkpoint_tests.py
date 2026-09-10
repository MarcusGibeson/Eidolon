import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.architecture_consolidation_intake_checkpoint import build_architecture_consolidation_intake_checkpoint
r=build_architecture_consolidation_intake_checkpoint(source_root=ROOT); checks=[r['contract_version']=='v1147.2',r['ok'],r['passed']==r['total']==12,r['read_only'] and not r['post_available'],not r['source_modified'] and not r['runtime_mutated'],r['summary']['ownership_domain_count']==9,r['summary']['checkpoint_count']==2,r['desktop_verification_pending'] and not r['consciousness_proven']]
env=dict(os.environ); env['PYTHONDONTWRITEBYTECODE']='1'; env['EIDOLON_DATA_DIR']=tempfile.mkdtemp()
p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'architecture-consolidation-intake-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=60); checks.append(p.returncode==0 and json.loads(p.stdout)['contract_version']=='v1147.2')
from conscious_agent.api_server import dispatch_api
status,payload=dispatch_api('GET','/api/cognition/architecture-consolidation-intake-checkpoint'); checks.append(status==200 and payload['data']['contract_version']=='v1147.2')
post,_=dispatch_api('POST','/api/cognition/architecture-consolidation-intake-checkpoint',body={'confirm':True}); checks.append(post in (404,405))
dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(); checks.append('architecture-consolidation-intake-checkpoint-panel' in dash and 'loadArchitectureConsolidationIntakeCheckpoint' in dash)
assert all(checks); print(json.dumps({'suite':'v1147.2','passed':len(checks),'total':len(checks)}))
