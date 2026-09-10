import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_bug_report_task import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1393_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_bug_report_task(project_root=p,bug_report=REPORT,visual_evidence_digest=V,operator_authorized=True);x=q['bug_report_task'];req('-${abs(amount)' in (p/'money.py').read_text(),'patch');N+=1
 req((p/'tests/test_negative_currency.py').is_file(),'regression');N+=1
 req(x['target_before_digest']!=x['target_after_digest'],'changed');N+=1
 chat=process_ordinary_chat_development_turn('show bug report task',project_state={'bug_report_task':x});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(not chat['eidolon_source_mutation_authorized'],'source');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1393-integration'})
