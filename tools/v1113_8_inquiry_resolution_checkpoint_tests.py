from pathlib import Path
import tempfile,json,os,subprocess,sys
from conscious_agent.inquiry_resolution_lifecycle_v1113 import InquiryResolutionLifecycleStore
from conscious_agent.inquiry_resolution_checkpoint import build_inquiry_resolution_checkpoint
from conscious_agent.api_server import dispatch_api

def req(x):
 if not x:raise AssertionError(x)
def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);s=InquiryResolutionLifecycleStore(root)
  s.inquiries.snapshot=lambda:{'records':[{'active_inquiry_id':'a1','inquiry_candidate_id':'c1'}]}
  s.assim._load=lambda:{'assimilations':[{'assimilation_id':'x1','active_inquiry_id':'a1','outcome':'assimilated'}]}
  try:s.decide('e0',active_inquiry_id='a1',outcome='resolved_supported');raise AssertionError('confirmation bypassed')
  except PermissionError:pass
  r=s.decide('e1',active_inquiry_id='a1',outcome='resolved_supported',operator_confirmation=True);req(r['ok']);req(r['result']['outcome']=='resolved_supported')
  dup=s.decide('e1',active_inquiry_id='a1',outcome='resolved_supported',operator_confirmation=True);req(dup['idempotent'])
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);before=list(root.rglob('*'));c=build_inquiry_resolution_checkpoint(root,source_root=Path(__file__).resolve().parents[1]);after=list(root.rglob('*'));req(c['ok']);req(c['contract_version']=='v1113.8');req(len(c['checks'])==14);req(before==after);req(not c['runtime_mutated']);req(not c['authorization_granted']);req(not c['external_browsing_performed'])
 status,payload=dispatch_api('GET','/api/cognition/inquiry-resolution-checkpoint');req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1113.8')
 run=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'eidolon.py'),'inquiry-resolution-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(run.returncode==0 and json.loads(run.stdout)['contract_version']=='v1113.8')
 print('v1113.8 focused tests: 10/10')
if __name__=='__main__':main()
