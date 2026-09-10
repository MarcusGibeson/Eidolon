import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_refactoring_task import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1394_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_refactoring_task(project_root=p,request=REQ,operator_authorized=True);x=q['refactoring_task'];req((p/'src/text_policy.py').is_file(),'module');N+=1
 req('from .text_policy import normalize_display_name' in (p/'src/profile_service.py').read_text(),'boundary');N+=1
 req(x['baseline_tests']['passed'] and x['final_tests']['passed'],'tests');N+=1
 chat=process_ordinary_chat_development_turn('show refactoring task',project_state={'refactoring_task':x});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(not chat['eidolon_source_mutation_authorized'],'source');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1394-integration'})
