import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_existing_project_feature import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1392_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_existing_project_feature(project_root=p,request=REQ,operator_authorized=True);x=q['existing_project_feature'];req('def slugify(text: str) -> str' in (p/'src/text_utils.py').read_text(),'implementation');N+=1
 req((p/'tests/test_slugify.py').is_file(),'new tests');N+=1
 req('def normalize_text' in (p/'src/text_utils.py').read_text(),'existing code');N+=1
 chat=process_ordinary_chat_development_turn('show existing project feature',project_state={'existing_project_feature':x});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(not chat['eidolon_source_mutation_authorized'],'source');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1392-integration'})
