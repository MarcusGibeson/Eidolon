from __future__ import annotations
import shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1337_browser_validation_test_support import *
from browser_validation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn

def main():
 p=[0]
 def req(x,n): assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,pre=browser_candidate(Path(td));browser=shutil.which('chromium')
  result=validate_browser_candidate(wid,target={'kind':'offline_document','html_relative_path':'ui.html'},active_grant=grant,precondition_record_id=pre,checks=[{'kind':'visible','selector':'#go'}],browser_executable=browser,runtime_root=runtime,now_unix=101);row=result['browser_validation'];req(result['ok'] and row['validation_status']=='passed','ordinary_product_workflow')
  dup=validate_browser_candidate(wid,target={'kind':'offline_document','html_relative_path':'ui.html'},active_grant=grant,precondition_record_id=pre,checks=[{'kind':'visible','selector':'#go'}],browser_executable=browser,runtime_root=runtime,now_unix=101);req(dup['status']=='browser_validation_duplicate' and dup['action_executed'] is False,'duplicate_converges')
  chat=process_ordinary_chat_development_turn('show browser validation',project_state={'browser_validation_id':row['browser_validation_id']},runtime_root=runtime);req(chat.get('active') and chat.get('browser_validation',{}).get('browser_validation_id')==row['browser_validation_id'] and chat.get('action_executed') is False,'ordinary_chat_read_only')
  req(row['screenshot_path_exposed'] is False and row['candidate_workspace_only'] is True,'runtime_private_evidence')
 print({'ok':True,'suite':'v1337.3-5-browser-validation-integration','passed':p[0],'total':4})
if __name__=='__main__':main()
