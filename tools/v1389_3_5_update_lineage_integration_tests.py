import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from update_lineage import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1389_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 a=record_update_lineage(**args(td));b=record_update_lineage(**args(td,'rolled_back',a['update_lineage']['lineage_digest']));req(a['ok'] and b['ok'],'two');N+=1
 r=load_update_lineage(runtime_root=td,candidate_id=CID);req(r['record_count']==2,'count');N+=1
 req(r['records'][1]['previous_lineage_digest']==r['records'][0]['lineage_digest'],'generation');N+=1
 chat=process_ordinary_chat_development_turn('show update lineage',project_state={'self_change_candidate_id':CID},runtime_root=td);req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(chat['content_free'] and not chat['source_mutation_authorized'],'boundary');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1389-integration'})
