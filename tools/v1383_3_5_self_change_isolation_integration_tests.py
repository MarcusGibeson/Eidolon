import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_change_isolation import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1383_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);s=source(r);x=create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);pw=x['private_workspace'];lin=x['self_change_workspace']['lineage_digest']
 v=verify_self_change_isolation(private_workspace=pw,expected_lineage_digest=lin);req(v['ok'],'verify');N+=1
 (Path(pw['work_root'])/'app.py').write_text('VALUE = 2\n');v=verify_self_change_isolation(private_workspace=pw,expected_lineage_digest=lin);req(v['ok'] and v['verification']['work_changed'],'work');N+=1
 req((s/'app.py').read_text()=='VALUE = 1\n','source untouched');N+=1
 chat=process_ordinary_chat_development_turn('show self change isolation',project_state={'self_change_workspace':x['self_change_workspace']});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req('private_workspace' not in chat and not chat['source_mutation_authorized'],'projection');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1383-integration'})
