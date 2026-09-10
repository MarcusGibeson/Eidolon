import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from performance_verification import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1357_test_support import *
P=0
r=evaluate_performance(source_manifest_digest=SOURCE,observations=obs(),budgets=B,hardware_profile=HW,evidence_digest=E);v=r['performance_verification'];req(r['ok'],'eval');P+=1
for m in METRICS:req(v['metrics'][m]['passed'],m)
P+=1
c=process_ordinary_chat_development_turn('show performance tests',project_state={'performance_verification':v});req(c['active'] and c['ok'],'chat');P+=1
req(not c['action_executed'] and not c['release_authorized'],'readonly');P+=1
req(v['hardware_profile_digest'] and v['evidence_digest']==E,'lineage');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1357.3-5-performance-integration'})
