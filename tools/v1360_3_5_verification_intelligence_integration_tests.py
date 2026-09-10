import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from verification_intelligence_checkpoint import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1360_test_support import *
P=0
r=build_verification_intelligence_scorecard(source_manifest_digest=S,evidence_surfaces=SURF,benchmark_cases=CASES);v=r['verification_intelligence'];req(r['ok'],'score');P+=1;c=process_ordinary_chat_development_turn('show verification checkpoint',project_state={'verification_intelligence':v});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'],'readonly');P+=1;req(v['benchmark_case_count']==6,'cases');P+=1;req(not v['raw_test_payloads_persisted'],'privacy');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1360.3-5-verification-intelligence-integration'})
