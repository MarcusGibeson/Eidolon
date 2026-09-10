import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from repair_proposal import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1364_test_support import *
P=0;r=propose_repair(source_manifest_digest=S,root_cause_digest=R,root_cause_resolved=True,root_cause_ambiguous=False,candidates=C);v=r['repair_proposal'];req(r['ok'],'proposal');P+=1;c=process_ordinary_chat_development_turn('show proposed repair',project_state={'repair_proposal':v});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'],'readonly');P+=1;req(v['narrowest_sufficient_candidate'],'selection');P+=1;req(v['content_free'],'privacy');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1364.3-5-repair-proposal-integration'})
