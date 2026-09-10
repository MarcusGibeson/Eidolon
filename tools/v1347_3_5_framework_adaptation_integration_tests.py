from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from framework_adaptation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1347_framework_adaptation_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_framework_adaptation(**args(src,runtime,grant,pres,git));row=r['framework_adaptation'];req(r['ok'] and row['adaptation_state']=='completed');req(row['tests_passed'] and row['workspace_cleaned']);req(row['nested_python_state']=='completed' and manifest(src)==before);chat=process_ordinary_chat_development_turn('show framework adaptation',project_state={'framework_adaptation_id':row['framework_adaptation_id']},runtime_root=runtime);req(chat.get('active') and chat.get('ok') and not chat.get('action_executed'));req(not row['selected_source_content_modified'])
 print({'ok':True,'suite':'v1347.3-5-framework-adaptation-integration','passed':p,'total':5})
if __name__=='__main__':main()
