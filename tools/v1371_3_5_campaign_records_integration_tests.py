import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from campaign_records import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1371_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_campaign_record(**BASE);v=r['campaign_record'];s=persist_campaign_record(runtime_root=td,record=v);req(s['runtime_written'],'stored');P+=1;l=load_campaign_record(runtime_root=td,campaign_id='campaign-1',expected_record_digest=v['record_digest']);req(l['ok'] and l['record_loaded'] and not l['chat_history_read'],'load');P+=1;c=process_ordinary_chat_development_turn('show campaign state',project_state={'campaign_record':v});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'] and not c['project_mutation_authorized'],'readonly');P+=1;req(c['campaign_record']['record_digest']==v['record_digest'],'same');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1371-integration'})
