import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from long_task_heartbeats import *
from v1375_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=record_heartbeat(campaign_record_digest=C,task_id_digest=T,sequence=1,progress_units=1,total_units=10,observed_at_unix=100,runtime_root=td);req(r['ok'],'record');P+=1
 h=r['heartbeat'];req(h['progress_basis_points']==1000 and h['content_free'],'progress');P+=1
 a=assess_long_task(campaign_record_digest=C,task_id_digest=T,now_unix=110,silence_timeout_seconds=30,runtime_root=td);req(a['long_task']['decision']=='continue','continue');P+=1
 req(a['long_task']['timeout_extension_recommended_seconds']>0 and not a['long_task']['timeout_extension_applied'],'extension');P+=1
 req(not a['process_stop_authorized'] and not a['timeout_budget_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1375-foundations'})
