from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1338_service_orchestration_test_support import *
from service_orchestration import *

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,sp,pp=service_candidate(Path(td));before=sorted((x.relative_to(src).as_posix(),x.read_bytes()) for x in src.rglob('*') if x.is_file())
  r=start_service_stack(wid,[definition('base'),definition('web',deps=('base',))],active_grant=grant,service_precondition_record_id=sp,process_precondition_record_id=pp,runtime_root=runtime,now_unix=101);req(r['ok'] and r['service_stack']['ready_count']==2,'integrated_service_checkpoint')
  req(r['service_stack']['dependency_order']==['base','web'] and all(x['port']>0 for x in r['service_stack']['services']),'dependency_and_port_evidence')
  stop=stop_service_stack(r['service_stack']['service_stack_id'],active_grant=grant,runtime_root=runtime,now_unix=101);req(stop['ok'] and stop['service_stack']['orphaned_service_count']==0,'known_recoverable_host_state')
  after=sorted((x.relative_to(src).as_posix(),x.read_bytes()) for x in src.rglob('*') if x.is_file());req(before==after,'selected_source_immutable')
  row=stop['service_stack'];req(row['release_authorized'] is False and row['external_network_authorized'] is False and row['os_network_sandbox_claimed'] is False,'authority_and_sandbox_truthful')
 print({'ok':True,'suite':'v1338.9-service-orchestration-checkpoint','passed':p[0],'total':5})
if __name__=='__main__':main()
