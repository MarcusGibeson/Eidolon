import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from root_cause_analysis import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1363_test_support import *
P=0;r=analyze_root_cause(source_manifest_digest=S,reproduction_digest=R,localization_digest=L,facts=FACTS);v=r['root_cause_analysis'];req(r['status']=='root_cause_resolved','status');P+=1;c=process_ordinary_chat_development_turn('show root cause',project_state={'root_cause_analysis':v});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'],'readonly');P+=1;req(v['fact_count']==4,'facts');P+=1;req(v['content_free'],'privacy');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1363.3-5-root-cause-integration'})
