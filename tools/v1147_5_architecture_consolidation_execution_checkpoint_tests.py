import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp()
from conscious_agent.architecture_consolidation_execution_checkpoint import build_architecture_consolidation_execution_checkpoint
r=build_architecture_consolidation_execution_checkpoint(source_root=ROOT); checks=[r['contract_version']=='v1147.5',r['ok'],r['passed']==r['total']==13,r['read_only'] and not r['post_available'],not r['source_modified'] and not r['runtime_mutated'],r['summary']['registered_checkpoint_count']==2,r['summary']['startup_tier_count']==3,r['desktop_verification_pending'] and not r['consciousness_proven']]
env=dict(os.environ); env['EIDOLON_DATA_DIR']=tempfile.mkdtemp(); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'architecture-consolidation-execution-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90); checks.append(p.returncode==0 and json.loads(p.stdout)['contract_version']=='v1147.5')
from conscious_agent.api_server import dispatch_api
status,payload=dispatch_api('GET','/api/cognition/architecture-consolidation-execution-checkpoint'); checks.append(status==200 and payload['data']['contract_version']=='v1147.5')
post,_=dispatch_api('POST','/api/cognition/architecture-consolidation-execution-checkpoint',body={'confirm':True}); checks.append(post in (404,405))
dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(); checks.append('architecture-consolidation-execution-checkpoint-panel' in dash and 'loadArchitectureConsolidationExecutionCheckpoint' in dash)
assert all(checks); print(json.dumps({'suite':'v1147.5','passed':len(checks),'total':len(checks)}))
