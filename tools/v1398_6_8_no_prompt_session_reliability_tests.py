import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from no_prompt_gamma_session import run_no_prompt_session
from v1398_test_support import *
passed=0
with tempfile.TemporaryDirectory() as td:
 g=active_grant();g['expires_unix']=101;ex,_=executor_factory(Path(td));r=run_no_prompt_session(grant=g,backlog=BACKLOG,executor=ex,now_unix=102);require(not r['ok'] and not r['action_executed'],'tampered grant rejected');passed+=1
with tempfile.TemporaryDirectory() as td:
 g=active_grant();ex,_=executor_factory(Path(td));r=run_no_prompt_session(grant=g,backlog=BACKLOG,executor=ex,now_unix=999);require(not r['ok'] and r['status']=='no_prompt_session_grant_expired','expired');passed+=1
with tempfile.TemporaryDirectory() as td:
 g=active_grant();ex,calls=executor_factory(Path(td));bad=[{'task_id':'backlog_publish','kind':'publish','action_class':'external_publish','value':100,'risk':'low','dependencies':[]}]+BACKLOG;r=run_no_prompt_session(grant=g,backlog=bad,executor=ex,now_unix=102,max_items=3);s=r['no_prompt_session'];require(r['ok'] and s['skipped_boundary_count']==1 and 'backlog_publish' not in calls,'protected skip');passed+=1
with tempfile.TemporaryDirectory() as td:
 g=active_grant();ex,calls=executor_factory(Path(td),fail_kind='test_marker');r=run_no_prompt_session(grant=g,backlog=BACKLOG,executor=ex,now_unix=102,max_items=3);s=r['no_prompt_session'];require(not r['ok'] and s['operator_intervention_required'] and s['failed_count']==1,'failure stops');passed+=1
 require(calls==['backlog_docs_index','backlog_test_marker'],'no unsafe continuation');passed+=1
with tempfile.TemporaryDirectory() as td:
 g=active_grant();ex,calls=executor_factory(Path(td));high=[{'task_id':'backlog_highrisk','kind':'x','action_class':'file_write','value':100,'risk':'high','dependencies':[]}]+BACKLOG;r=run_no_prompt_session(grant=g,backlog=high,executor=ex,now_unix=102,max_items=2);require(r['ok'] and r['no_prompt_session']['skipped_boundary_count']==1,'high risk skip');passed+=1
 require(not r['no_prompt_session']['external_publish_authorized'] and not r['no_prompt_session']['workspace_expansion_authorized'],'denied authority');passed+=1
with tempfile.TemporaryDirectory() as td:
 g=active_grant();r=run_no_prompt_session(grant=g,backlog=BACKLOG,executor=lambda task:{'ok':True},now_unix=102,max_items=3);require(not r['ok'] and r['no_prompt_session']['operator_intervention_required'],'evidence-free completion rejected');passed+=1
with tempfile.TemporaryDirectory() as td:
 g=active_grant();malformed=[{'task_id':'backlog_bad','kind':'x','action_class':'file_write','value':'not-a-number','risk':'low','dependencies':[]}];r=run_no_prompt_session(grant=g,backlog=malformed,executor=lambda task:{'ok':True,'evidence_digest':'a'*64},now_unix=102);require(not r['ok'] and not r['action_executed'],'malformed backlog fails closed');passed+=1
print({'ok':passed==9,'passed':passed,'total':9,'suite':'v1398-reliability'})
