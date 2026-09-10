import json, os, subprocess, sys, tempfile
from pathlib import Path
os.environ.setdefault('EIDOLON_DATA_DIR', tempfile.mkdtemp())
from conscious_agent.architecture_consolidation_reliability_checkpoint import build_architecture_consolidation_reliability_checkpoint
from conscious_agent.api_server import dispatch_api
ROOT=Path(__file__).resolve().parents[1]
r=build_architecture_consolidation_reliability_checkpoint(source_root=ROOT)
checks=[r['contract_version']=='v1147.8',r['ok'],r['passed']==r['total']==20,r['read_only'] and not r['post_available'],not r['source_modified'] and not r['runtime_mutated'],r['summary']['ownership_domain_count']==9,r['summary']['issue_count']==0,r['desktop_verification_pending'] and not r['consciousness_proven']]
env=dict(os.environ); env['EIDOLON_DATA_DIR']=tempfile.mkdtemp(); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'architecture-consolidation-reliability-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90); checks.append(p.returncode==0 and json.loads(p.stdout)['contract_version']=='v1147.8')
status,payload=dispatch_api('GET','/api/cognition/architecture-consolidation-reliability-checkpoint'); checks.append(status==200 and payload['data']['contract_version']=='v1147.8')
status,_=dispatch_api('POST','/api/cognition/architecture-consolidation-reliability-checkpoint'); checks.append(status in {404,405})
assert all(checks); print(json.dumps({'suite':'v1147.8','passed':len(checks),'total':len(checks)}))
