from pathlib import Path
import tempfile, json, os, subprocess, sys
from conscious_agent.inquiry_evidence_governance_checkpoint import build_inquiry_evidence_governance_checkpoint
from conscious_agent.api_server import dispatch_api
def req(x):
 if not x: raise AssertionError(x)
def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);before=list(root.rglob('*'));c=build_inquiry_evidence_governance_checkpoint(root,source_root=Path(__file__).resolve().parents[1]);after=list(root.rglob('*'));req(c['ok']);req(c['contract_version']=='v1113.5');req(len(c['checks'])==12);req(before==after);req(not c['runtime_mutated']);req(not c['external_browsing_performed']);req(not c['provider_contacted']);req(not c['authorization_granted'])
 status,payload=dispatch_api('GET','/api/cognition/inquiry-evidence-governance-checkpoint');req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1113.5')
 run=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'eidolon.py'),'inquiry-evidence-governance-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(run.returncode==0 and json.loads(run.stdout)['contract_version']=='v1113.5')
 print('v1113.5 focused tests: 10/10')
if __name__=='__main__':main()
