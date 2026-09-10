from __future__ import annotations
import sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1336_process_operations_test_support import *
from typed_process_operations import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
def main():
    passed=[0]
    def req(x,n):
          assert x,n;passed[0]+=1
    with tempfile.TemporaryDirectory() as td:
     src,runtime,grant,wid,candidate,pre=process_candidate(Path(td))
     started=start_candidate_process(wid,[sys.executable,'-c','import time;print("ready",flush=True);time.sleep(30)'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101);op=started['process_operation']['process_operation_id'];req(started['ok'],'long_process_started')
     seen=monitor_candidate_process(op,runtime_root=runtime,include_log_tail=True);req('ready' in (seen.get('log_tail') or {}).get('stdout','') or seen['process_operation']['process_state'] in {'running','starting'},'bounded_internal_log_visibility')
     chat=process_ordinary_chat_development_turn('show process operation',project_state={'process_operation_id':op},runtime_root=runtime);req(chat.get('active') and chat.get('action_executed') is False and (chat.get('process_operation') or {}).get('raw_command_exposed') is False,'ordinary_chat_read_only_inspection')
     stopped=stop_candidate_process(op,active_grant=grant,runtime_root=runtime,now_unix=101);req(stopped['ok'] and stopped['process_operation']['process_state'] in {'cancelled','failed','interrupted','uncertain','completed'},'exact_stop_reconciled')
    print({'ok':True,'suite':'v1336.3-5-process-operations-integration','passed':passed[0],'total':4})

if __name__ == "__main__":
    main()
