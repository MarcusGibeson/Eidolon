import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from long_task_heartbeats import *
from v1375_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 record_heartbeat(campaign_record_digest=C,task_id_digest=T,sequence=1,progress_units=4,total_units=10,observed_at_unix=100,runtime_root=td)
 a=assess_long_task(campaign_record_digest=C,task_id_digest=T,now_unix=110,runtime_root=td);req(a['ok'],'checkpoint');P+=1
 req(a['long_task']['progress_basis_points']==4000,'progress');P+=1
 req(a['long_task']['decision']=='continue','decision');P+=1
 req(a['long_task']['content_free'] and a['long_task']['read_only'],'evidence');P+=1
 req(not a['timeout_budget_mutation_authorized'] and not a['independent_authority_granted'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1375-checkpoint'})
