import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from campaign_records import *
from v1371_test_support import *
P=0;r=build_campaign_record(**BASE);req(r['ok'],'ready');P+=1;v=r['campaign_record'];req(v['remaining_steps']==4 and not v['chat_history_required'],'progress');P+=1;req(v['content_free'] and not v['raw_goal_persisted'] and not v['raw_plan_persisted'],'privacy');P+=1;req(not r['work_execution_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
with tempfile.TemporaryDirectory() as td:
 s=persist_campaign_record(runtime_root=td,record=v);req(s['ok'] and s['runtime_written'],'stored');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1371-foundations'})
