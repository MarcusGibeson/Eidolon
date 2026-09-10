import sys,tempfile,json;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from long_task_heartbeats import *
from v1375_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 req(not record_heartbeat(campaign_record_digest='bad',task_id_digest=T,sequence=1,progress_units=0,total_units=1,runtime_root=td)['ok'],'lineage');P+=1
 r=record_heartbeat(campaign_record_digest=C,task_id_digest=T,sequence=1,progress_units=3,total_units=10,observed_at_unix=100,runtime_root=td);req(r['ok'],'seed');P+=1
 req(not record_heartbeat(campaign_record_digest=C,task_id_digest=T,sequence=2,progress_units=2,total_units=10,observed_at_unix=120,runtime_root=td)['ok'],'regress');P+=1
 req(not request_task_cancellation(campaign_record_digest=C,task_id_digest=T,request_id='x',cancellation_authorized=False,runtime_root=td)['ok'],'cancel auth');P+=1
 a=assess_long_task(campaign_record_digest=C,task_id_digest=T,now_unix=250,silence_timeout_seconds=100,runtime_root=td);req(a['long_task']['decision']=='silence_detected','silence');P+=1
 a=assess_long_task(campaign_record_digest=C,task_id_digest=T,now_unix=101,extension_count=2,max_extensions=2,runtime_root=td);req(a['long_task']['timeout_extension_recommended_seconds']==0,'extension cap');P+=1
 p=Path(td)/'long_task_heartbeats'/C/T/'heartbeat.json';x=json.loads(p.read_text());x['progress_units']=9;p.write_text(json.dumps(x));req(not assess_long_task(campaign_record_digest=C,task_id_digest=T,now_unix=101,runtime_root=td)['ok'],'tamper');P+=1
 req(not record_heartbeat(campaign_record_digest=C,task_id_digest=T,sequence=0,progress_units=0,total_units=0,runtime_root=td)['ok'],'fields');P+=1
print({'ok':P==8,'passed':P,'total':8,'suite':'v1375-reliability'})
