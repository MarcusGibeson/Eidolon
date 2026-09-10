from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1343_html_css_test_support import *
from html_css_implementation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);a=args(src,runtime,grant,pres,git);r=run_html_css_implementation(**a);row=r['html_css_implementation'];req(r['ok'] and row['implementation_state']=='completed' and row['change_count']==2,'multi_file_ui_candidate_completed');req(row['compatibility_passed'] and row['browser_passed'] and row['screenshot_captured'] and len(row['screenshot_digest'])==64,'real_browser_visual_evidence');req(len(row['file_operation_ids'])==2 and row['preview_operation_id'] and row['git_commit_operation_id'],'owned_changes_preview_commit_lineage');req(row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before,'cleanup_source_immutable');chat=process_ordinary_chat_development_turn('show ui implementation checkpoint',project_state={'html_css_implementation_id':row['implementation_id']},runtime_root=runtime);req(chat['active'] and chat['ok'] and not chat['action_executed'],'ordinary_chat_read_only');again=run_html_css_implementation(**a);req(again['status']=='html_css_implementation_already_exists' and not again['action_executed'],'duplicate_suppressed')
 print({'ok':True,'suite':'v1343.3-5-html-css-integration','passed':p[0],'total':6})
if __name__=='__main__':main()
