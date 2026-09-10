from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1338_service_orchestration_test_support import *
from service_orchestration import *

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 req(READINESS_KINDS==('tcp','http'),'typed_readiness_surface')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,sp,pp=service_candidate(Path(td));before=(src/'service_fixture.py').read_bytes()
  r=start_service_stack(wid,[definition()],active_grant=grant,service_precondition_record_id=sp,process_precondition_record_id=pp,runtime_root=runtime,now_unix=101);row=r['service_stack'];req(r['ok'] and row['stack_state']=='ready' and row['ready_count']==1,'real_loopback_service_ready')
  req(row['services'][0]['port']>0 and row['services'][0]['readiness_state']=='ready','port_and_readiness_evidence')
  stopped=stop_service_stack(row['service_stack_id'],active_grant=grant,runtime_root=runtime,now_unix=101);req(stopped['ok'] and stopped['service_stack']['orphaned_service_count']==0 and stopped['service_stack']['stack_state']=='stopped','exact_cleanup_no_orphan')
  req((src/'service_fixture.py').read_bytes()==before and row['raw_command_exposed'] is False and row['external_network_authorized'] is False,'source_privacy_authority_boundary')
 print({'ok':True,'suite':'v1338.0-2-service-orchestration-foundations','passed':p[0],'total':5})
if __name__=='__main__':main()
