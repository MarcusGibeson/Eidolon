import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from fault_localization import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1362_test_support import *
P=0;r=localize_fault(source_manifest_digest=S,reproduction_digest=R,candidates=C);v=r['fault_localization'];req(r['ok'],'rank');P+=1;c=process_ordinary_chat_development_turn('show likely causes',project_state={'fault_localization':v});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'],'readonly');P+=1;req(v['candidate_count']==3,'count');P+=1;req(v['content_free'],'privacy');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1362.3-5-fault-localization-integration'})
