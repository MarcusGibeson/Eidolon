from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1344_data_schema_test_support import *
from data_schema_implementation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 for rel in ('config/settings.json','config/settings.yaml','config/settings.toml','db/schema.sql'):
  with tempfile.TemporaryDirectory() as td:
   src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,relative_path=rel));row=r['data_schema_implementation'];req(r['ok'] and row['compatibility_passed'] and row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before,f'{rel}_candidate')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_data_schema_implementation(**args(src,runtime,grant,pres,git));op=r['data_schema_implementation']['data_schema_implementation_id'];loaded=load_data_schema_implementation(op,runtime_root=runtime);req(loaded['implementation_state']=='completed' and not loaded['raw_schema_content_exposed'] and not loaded['schema_identifiers_exposed'],'content_minimized')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_data_schema_implementation(**args(src,runtime,grant,pres,git));r2=run_data_schema_implementation(**args(src,runtime,grant,pres,git));req(r2['status']=='data_schema_implementation_already_exists' and not r2['action_executed'],'duplicate_suppressed')
  op=r['data_schema_implementation']['data_schema_implementation_id'];chat=process_ordinary_chat_development_turn('show data schema implementation',project_state={'data_schema_implementation_id':op},runtime_root=runtime);req(chat.get('active') and chat.get('ok') and not chat.get('action_executed'),'ordinary_chat_read_only')
 print({'ok':True,'suite':'v1344.3-5-data-schema-integration','passed':p[0],'total':7})
if __name__=='__main__':main()
