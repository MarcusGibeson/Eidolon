import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from no_prompt_gamma_session import run_no_prompt_session
from v1398_test_support import *
passed=0
with tempfile.TemporaryDirectory() as td:
 ex,calls=executor_factory(Path(td));r=run_no_prompt_session(grant=active_grant(),backlog=BACKLOG,executor=ex,now_unix=102,max_items=3);require(r['ok'],'session');passed+=1;s=r['no_prompt_session']
 require(s['completed_count']==3 and calls==['backlog_docs_index','backlog_test_marker','backlog_cleanup_note'],'multiple dependency tasks');passed+=1
 require(s['prompt_count']==0 and s['clarification_count']==0,'no prompt');passed+=1
 require(not s['protected_action_executed'] and not s['standing_grant_reused_outside_scope'],'boundary');passed+=1
 require(s['raw_executor_output_retained'] is False and s['private_task_content_retained'] is False,'report privacy');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1398-foundations'})
