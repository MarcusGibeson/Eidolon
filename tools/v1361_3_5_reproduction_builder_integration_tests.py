import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from reproduction_builder import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1361_test_support import *
P=0;r=build_reproduction(source_manifest_digest=S,evidence_inputs=EVID,candidates=CANDS,environment_digest=ENV);v=r['reproduction'];req(r['ok'],'build');P+=1;c=process_ordinary_chat_development_turn('show reproduction',project_state={'reproduction':v});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'],'readonly');P+=1;req(v['evidence_count']==3,'evidence');P+=1;req(all('target_id' not in x for x in v['steps']),'content minimized');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1361.3-5-reproduction-builder-integration'})
