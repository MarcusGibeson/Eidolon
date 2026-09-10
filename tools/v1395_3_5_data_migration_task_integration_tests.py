import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_data_migration_task import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1395_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=db(Path(td));before=read_profiles_compatible(db_path=p);q=run_data_migration_task(db_path=p,operator_authorized=True);x=q['data_migration'];rb=rollback_data_migration(db_path=p,migration=x,expected_migration_digest=x['migration_digest'],operator_authorized=True);req(rb['ok'],'rollback');N+=1
 after=read_profiles_compatible(db_path=p);req(after['schema_version']==1,'version');N+=1
 req(before['data_digest']==after['data_digest'],'exact data');N+=1
 chat=process_ordinary_chat_development_turn('show data migration task',project_state={'data_migration':x});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(not chat['eidolon_source_mutation_authorized'],'source');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1395-integration'})
