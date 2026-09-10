import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from no_prompt_gamma_session import run_no_prompt_session,process_no_prompt_session_control
from v1398_test_support import *
passed=0
with tempfile.TemporaryDirectory() as td:
 ex,calls=executor_factory(Path(td));r=run_no_prompt_session(grant=active_grant(),backlog=BACKLOG,executor=ex,now_unix=102,max_items=3);s=r['no_prompt_session']
 require([x['decision'] for x in s['material_decisions']]==['completed']*3,'material decisions');passed+=1
 require(all(len(x['result_digest'])==64 for x in s['results']),'result evidence');passed+=1
 c=process_no_prompt_session_control('show no prompt session',project_state={'no_prompt_session':s});require(c['active'] and c['ok'] and not c['action_executed'],'inspection');passed+=1
 require(not s['operator_intervention_required'] and s['failed_count']==0,'ordinary completion');passed+=1
 require(not s['release_authorized'] and not s['independent_authority_granted'],'authority');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1398-integration'})
