import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from long_task_heartbeats import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1375_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 record_heartbeat(campaign_record_digest=C,task_id_digest=T,sequence=1,progress_units=1,total_units=10,observed_at_unix=100,runtime_root=td)
 s=record_heartbeat(campaign_record_digest=C,task_id_digest=T,sequence=2,progress_units=1,total_units=10,observed_at_unix=105,minimum_interval_seconds=15,runtime_root=td);req(s['status']=='heartbeat_suppressed_no_material_change' and not s['persisted'],'throttle');P+=1
 m=record_heartbeat(campaign_record_digest=C,task_id_digest=T,sequence=3,progress_units=2,total_units=10,observed_at_unix=106,minimum_interval_seconds=15,runtime_root=td);req(m['persisted'],'material');P+=1
 q=request_task_cancellation(campaign_record_digest=C,task_id_digest=T,request_id='cancel-1',cancellation_authorized=True,requested_at_unix=107,runtime_root=td);req(q['ok'],'cancel');P+=1
 a=assess_long_task(campaign_record_digest=C,task_id_digest=T,now_unix=108,runtime_root=td);req(a['long_task']['decision']=='cancel_requested','decision');P+=1
 c=process_ordinary_chat_development_turn('show task heartbeat',project_state={'long_task':a['long_task']});req(c.get('active') and c.get('ok'),'chat');P+=1
 req(not c['action_executed'] and not c['process_stop_authorized'],'readonly');P+=1
print({'ok':P==6,'passed':P,'total':6,'suite':'v1375-integration'})
