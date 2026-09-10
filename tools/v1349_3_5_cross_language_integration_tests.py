from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from cross_language_changes import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1349_cross_language_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_cross_language_change(**args(src,runtime,grant,pres,git));row=r['cross_language_change'];req(r['ok'] and row['transaction_state']=='completed');req(row['validation_passed_count']==5);req(row['verification_passed_count']==3 and len(row['verification_process_ids'])==3);req(len(row['file_operation_ids'])==5 and bool(row['git_commit_operation_id']));req(row['workspace_cleaned'] and manifest(src)==before);chat=process_ordinary_chat_development_turn('show cross language change',project_state={'cross_language_change_id':row['cross_language_change_id']},runtime_root=runtime);req(chat.get('active') and chat.get('ok') and not chat.get('action_executed'))
 print({'ok':True,'suite':'v1349.3-5-cross-language-integration','passed':p,'total':6})
if __name__=='__main__':main()
