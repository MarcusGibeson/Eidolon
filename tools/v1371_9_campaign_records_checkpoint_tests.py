import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from campaign_records import *
from v1371_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 v=build_campaign_record(**BASE)['campaign_record'];req(v['runtime_record_only'] and v['content_free'],'contract');P+=1;s=persist_campaign_record(runtime_root=td,record=v);req(s['ok'],'persist');P+=1;l=load_campaign_record(runtime_root=td,campaign_id='campaign-1',expected_record_digest=v['record_digest']);req(l['ok'],'restore');P+=1;req(not l['source_mutation_authorized'] and not l['work_execution_authorized'],'authority');P+=1;req(not l['chat_history_read'],'chat independent');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1371-checkpoint'})
