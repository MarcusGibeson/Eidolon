from __future__ import annotations
import socket,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1338_service_orchestration_test_support import *
from service_orchestration import *
from ordinary_chat_development_campaign import _read_json,_atomic_json

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,sp,pp=service_candidate(Path(td))
  cyc=start_service_stack(wid,[definition('a',deps=('b',)),definition('b',deps=('a',))],active_grant=grant,service_precondition_record_id=sp,process_precondition_record_id=pp,runtime_root=runtime,now_unix=101);req(not cyc['ok'] and cyc['status']=='service_dependency_cycle' and cyc['action_executed'] is False,'cycle_rejected_prelaunch')
  sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  try:busy=start_service_stack(wid,[definition('busy',port=port)],active_grant=grant,service_precondition_record_id=sp,process_precondition_record_id=pp,runtime_root=runtime,now_unix=102);req(not busy['ok'] and busy['service_stack']['orphaned_service_count']==0,'occupied_port_fails_clean')
  finally:sock.close()
  fail=start_service_stack(wid,[definition('good'),definition('bad',deps=('good',),mode='exit',readiness=.5)],active_grant=grant,service_precondition_record_id=sp,process_precondition_record_id=pp,runtime_root=runtime,now_unix=103);fr=fail['service_stack'];req(not fail['ok'] and fr['cleanup_performed'] and fr['orphaned_service_count']==0,'readiness_failure_rolls_back_started_dependencies')
  req(all(x['process_state'] in {'completed','failed','cancelled','interrupted','uncertain'} for x in fr['services']),'failure_cleanup_terminal')
  ok=start_service_stack(wid,[definition('one')],active_grant=grant,service_precondition_record_id=sp,process_precondition_record_id=pp,runtime_root=runtime,now_unix=104);sid=ok['service_stack']['service_stack_id'];dup=start_service_stack(wid,[definition('one')],active_grant=grant,service_precondition_record_id=sp,process_precondition_record_id=pp,runtime_root=runtime,now_unix=104);req(dup['status']=='service_stack_already_exists' and dup['action_executed'] is False,'duplicate_start_converges')
  baddef=restart_service(sid,definition('one',mode='exit'),active_grant=grant,process_precondition_record_id=pp,runtime_root=runtime,now_unix=104);req(not baddef['ok'] and baddef['status']=='service_definition_lineage_mismatch' and baddef['action_executed'] is False,'restart_lineage_bound')
  from service_orchestration import _path
  path=_path(sid,runtime);raw=_read_json(path);raw['stack_state']='ready_forever';_atomic_json(path,raw);req(load_service_stack(sid,runtime_root=runtime)=={},'tamper_rejected')
  # stop exact owned process using pre-tamper public operation id before temp cleanup
  from typed_process_operations import stop_candidate_process
  op=ok['service_stack']['services'][0]['process_operation_id'];stop_candidate_process(op,active_grant=grant,runtime_root=runtime,now_unix=104)
 print({'ok':True,'suite':'v1338.6-8-service-orchestration-reliability','passed':p[0],'total':7})
if __name__=='__main__':main()
