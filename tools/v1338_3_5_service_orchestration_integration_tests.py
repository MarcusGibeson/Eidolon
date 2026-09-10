from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1338_service_orchestration_test_support import *
from service_orchestration import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,sp,pp=service_candidate(Path(td));defs=[definition('db'),definition('api',deps=('db',))]
  r=start_service_stack(wid,defs,active_grant=grant,service_precondition_record_id=sp,process_precondition_record_id=pp,runtime_root=runtime,now_unix=101);row=r['service_stack'];req(r['ok'] and row['dependency_order']==['db','api'] and row['ready_count']==2,'dependency_order_and_readiness')
  old=next(x for x in row['services'] if x['service_code']=='api')['process_operation_id'];rr=restart_service(row['service_stack_id'],definition('api',deps=('db',)),active_grant=grant,process_precondition_record_id=pp,runtime_root=runtime,now_unix=101);new=next(x for x in rr['service_stack']['services'] if x['service_code']=='api');req(rr['ok'] and new['restart_count']==1 and new['process_operation_id']!=old and new['readiness_state']=='ready','fresh_generation_restart')
  chat=process_ordinary_chat_development_turn('show service stack',project_state={'service_stack_id':row['service_stack_id']},runtime_root=runtime);req(chat.get('active') and chat.get('service_stack',{}).get('service_stack_id')==row['service_stack_id'] and chat.get('action_executed') is False,'ordinary_chat_inspection_only')
  observed=inspect_service_stack(row['service_stack_id'],runtime_root=runtime);req(observed['ok'] and observed['action_executed'] is False,'read_only_status_reconciliation')
  stopped=stop_service_stack(row['service_stack_id'],active_grant=grant,runtime_root=runtime,now_unix=101);req(stopped['ok'] and stopped['service_stack']['orphaned_service_count']==0,'multi_service_cleanup')
 print({'ok':True,'suite':'v1338.3-5-service-orchestration-integration','passed':p[0],'total':5})
if __name__=='__main__':main()
