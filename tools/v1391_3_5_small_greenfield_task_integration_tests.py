import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_greenfield_task import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1391_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 q=run_small_greenfield_task(request=REQ,runtime_root=td,task_id=TID);x=q['greenfield_task'];p=Path(x['workspace_path']);req((p/'index.html').is_file(),'entry');N+=1
 req('CalculatorCore' in (p/'app.js').read_text(),'logic');N+=1
 req('node test.js' in (p/'README.md').read_text(),'handoff');N+=1
 chat=process_ordinary_chat_development_turn('show greenfield task',project_state={'greenfield_task':x});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(not chat['eidolon_source_mutation_authorized'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1391-integration'})
