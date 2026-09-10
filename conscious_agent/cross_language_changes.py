from __future__ import annotations
"""v1349 one-candidate transaction across code, UI, data, and documentation."""
import ast,hashlib,json,re,shutil,subprocess,sys,time,tomllib
from html.parser import HTMLParser
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
from ordinary_chat_development_campaign import _atomic_json,_read_json,_store_root
from workspace_isolation import create_disposable_workspace,cleanup_disposable_workspace
from structured_file_operations import read_candidate_file,patch_candidate_file
from typed_git_operations import stage_owned_changes,commit_owned_changes
from typed_process_operations import start_candidate_process,monitor_candidate_process,stop_candidate_process
from tool_result_reconciliation import reconcile_tool_result
CONTRACT_VERSION='v1349.8';MAX_FILES=24;MAX_WAIT=50.0;TERMINAL={'completed','failed','cancelled','interrupted','uncertain'};REQUIRED_PRECONDITIONS=('git','file_read','file_patch','shell')
CROSS_LANGUAGE_DENIED_AUTHORITY={**DENIED_AUTHORITY,'source_mutation_authorized':False,'source_application_authorized':False,'dependency_installation_authorized':False,'network_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
def _root(runtime_root=None):return _store_root(runtime_root)/'phase5_cross_language_changes'
def _path(op,runtime_root=None):
 if not re.fullmatch(r'xlang_[a-f0-9]{24}',str(op or '')):raise ValueError('invalid_cross_language_change_id')
 return _root(runtime_root)/'records'/f'{op}.json'
def _load(op,runtime_root=None):
 row=_read_json(_path(op,runtime_root));return row if row and row.get('record_digest')==digest({k:v for k,v in row.items() if k!='record_digest'}) else {}
def _save(row,runtime_root=None):row.pop('record_digest',None);row['record_digest']=digest(row);_atomic_json(_path(row['cross_language_change_id'],runtime_root),row);return row
def _safe_rel(value:str)->str:
 s=str(value or '').replace('\\','/').strip();p=PurePosixPath(s)
 if not s or p.is_absolute() or any(x in {'','.','..'} for x in p.parts):raise ValueError('unsafe_cross_language_path')
 if any(x.casefold() in {'.git','data','runtime','private','secrets','credentials','node_modules','.venv','venv','__pycache__'} for x in p.parts):raise ValueError('protected_cross_language_path')
 return p.as_posix()
class _HTMLCheck(HTMLParser):
 def __init__(self):super().__init__();self.stack=[];self.errors=0
 def handle_starttag(self,tag,attrs):
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(tag)
 def handle_endtag(self,tag):
  if tag in self.stack:
   while self.stack:
    x=self.stack.pop()
    if x==tag:break
  else:self.errors+=1
def _validate_content(path:str,text:str)->tuple[bool,str]:
 suffix=PurePosixPath(path).suffix.lower()
 try:
  if suffix=='.py':ast.parse(text)
  elif suffix=='.json':json.loads(text)
  elif suffix=='.toml':tomllib.loads(text)
  elif suffix in {'.html','.htm'}:
   h=_HTMLCheck();h.feed(text)
   if h.errors:raise ValueError('html_structure_invalid')
  elif suffix in {'.js','.mjs','.cjs'}:
   node=shutil.which('node')
   if not node:return False,'node_unavailable'
   cp=subprocess.run([node,'--check'],input=text,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
   if cp.returncode:return False,'javascript_syntax_invalid'
  elif suffix in {'.md','.txt','.css','.yaml','.yml'}:
   if '\x00' in text:raise ValueError('text_contains_nul')
  else:return False,'unsupported_cross_language_file_type'
 except (SyntaxError,ValueError,json.JSONDecodeError,tomllib.TOMLDecodeError):return False,f'{suffix.lstrip(".") or "text"}_structure_invalid'
 return True,'valid'
def inspect_change_set(changes:Sequence[Mapping[str,Any]])->dict[str,Any]:
 if not changes or len(changes)>MAX_FILES:return {'ok':False,'status':'cross_language_change_count_invalid','inspection_only':True,**CROSS_LANGUAGE_DENIED_AUTHORITY}
 paths=[]
 try:paths=[_safe_rel(str(c.get('relative_path') or '')) for c in changes]
 except ValueError as e:return {'ok':False,'status':str(e),'inspection_only':True,**CROSS_LANGUAGE_DENIED_AUTHORITY}
 if len(set(paths))!=len(paths):return {'ok':False,'status':'duplicate_cross_language_path','inspection_only':True,**CROSS_LANGUAGE_DENIED_AUTHORITY}
 types=sorted({PurePosixPath(p).suffix.lower() for p in paths});out={'ok':True,'status':'cross_language_change_set_ready','change_count':len(paths),'file_type_count':len(types),'change_set_digest':digest([(hashlib.sha256(p.encode()).hexdigest(),str(c.get('expected_content_digest') or ''),digest(c.get('patches') or [])) for p,c in zip(paths,changes)]),'inspection_only':True,**CROSS_LANGUAGE_DENIED_AUTHORITY};out['inspection_digest']=digest(out);return out
def _wait(pid:str,workspace_digest:str,runtime_root=None):
 end=time.monotonic()+MAX_WAIT;obs={}
 while time.monotonic()<end:
  obs=monitor_candidate_process(pid,runtime_root=runtime_root);state=(obs.get('process_operation') or {}).get('process_state')
  if state in TERMINAL:break
  time.sleep(.05)
 proc=obs.get('process_operation') or {};ok=proc.get('process_state')=='completed' and proc.get('return_code')==0 and not proc.get('timed_out') and not proc.get('log_limit_exceeded');rec=reconcile_tool_result(tool_code='shell',operation_id=pid,wrapper_observation={'wrapper_status':'returned','reported_status':proc.get('process_state')},current_workspace_digest=workspace_digest,runtime_root=runtime_root);return ok,str((rec.get('reconciliation') or {}).get('reconciliation_id') or '')
def run_cross_language_change(*,source_root:str|Path,source_workspace_digest:str,active_grant:Mapping[str,Any],precondition_record_ids:Mapping[str,str],changes:Sequence[Mapping[str,Any]],verification_commands:Sequence[Sequence[str]],commit_message:str='Coordinate cross-language change',runtime_root=None,now_unix:int|None=None,git_executable:str|None=None,cleanup_on_complete:bool=True)->dict[str,Any]:
 inspected=inspect_change_set(changes)
 if not inspected.get('ok'):return {'ok':False,'status':inspected['status'],'action_executed':False,**CROSS_LANGUAGE_DENIED_AUTHORITY}
 pres={str(k):str(v) for k,v in precondition_record_ids.items()}
 if any(not pres.get(k) for k in REQUIRED_PRECONDITIONS):return {'ok':False,'status':'complete_cross_language_preconditions_required','action_executed':False,**CROSS_LANGUAGE_DENIED_AUTHORITY}
 if not verification_commands:return {'ok':False,'status':'cross_language_verification_required','action_executed':False,**CROSS_LANGUAGE_DENIED_AUTHORITY}
 spec={'contract':CONTRACT_VERSION,'source':source_workspace_digest,'grant':active_grant.get('grant_digest'),'pre':pres,'changes':inspected['change_set_digest'],'verification':digest([list(x) for x in verification_commands]),'commit':hashlib.sha256(commit_message.encode()).hexdigest(),'cleanup':cleanup_on_complete};op='xlang_'+digest(spec)[:24];existing=_load(op,runtime_root)
 if existing:return {'ok':existing.get('transaction_state')=='completed','status':'cross_language_change_already_exists','cross_language_change':public_cross_language_change(existing),'action_executed':False,**CROSS_LANGUAGE_DENIED_AUTHORITY}
 row={'contract_version':CONTRACT_VERSION,'cross_language_change_id':op,'source_workspace_digest':source_workspace_digest,'transaction_state':'starting','failure_stage':'','workspace_id':'','file_operation_ids':[],'validation_passed_count':0,'verification_process_ids':[],'verification_reconciliation_ids':[],'verification_passed_count':0,'git_stage_operation_id':'','git_commit_operation_id':'','workspace_cleaned':False,'host_recoverable':False,'partial_commit_created':False,'action_executed':False,**CROSS_LANGUAGE_DENIED_AUTHORITY};_save(row,runtime_root);wid='';pids=[]
 try:
  isolated=create_disposable_workspace(source_root=source_root,source_workspace_digest=source_workspace_digest,active_grant=active_grant,precondition_record_id=pres['git'],mode='git_branch_worktree',retention_rule='retain_for_review',runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not isolated.get('ok') or not isolated.get('workspace_created'):raise RuntimeError('workspace_isolation')
  wid=str(isolated['workspace_id']);row['workspace_id']=wid;row['action_executed']=True;_save(row,runtime_root)
  for c in changes:
   rel=_safe_rel(str(c.get('relative_path') or ''));expected=str(c.get('expected_content_digest') or '');before=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=False)
   if not before.get('ok') or str((before.get('file_operation') or {}).get('before_digest') or '')!=expected:raise RuntimeError('stale_cross_language_content_digest')
   patched=patch_candidate_file(wid,rel,expected_content_digest=expected,patches=c.get('patches') or [],active_grant=active_grant,precondition_record_id=pres['file_patch'],runtime_root=runtime_root,now_unix=now_unix)
   if not patched.get('ok'):raise RuntimeError(str(patched.get('status') or 'cross_language_patch'))
   fid=str((patched.get('file_operation') or {}).get('operation_id') or '');row['file_operation_ids'].append(fid);after=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True);valid,reason=_validate_content(rel,str(after.get('content') or ''))
   if not valid:raise RuntimeError(reason)
   row['validation_passed_count']+=1;_save(row,runtime_root)
  for i,argv in enumerate(verification_commands):
   started=start_candidate_process(wid,list(argv),active_grant=active_grant,precondition_record_id=pres['shell'],runtime_root=runtime_root,now_unix=now_unix,timeout_seconds=45,invocation_discriminator=f'v1349:{op}:verify:{i}')
   if not started.get('ok'):raise RuntimeError('cross_language_verification_start')
   pid=str((started.get('process_operation') or {}).get('process_operation_id') or '');pids.append(pid);row['verification_process_ids'].append(pid);_save(row,runtime_root);passed,rid=_wait(pid,source_workspace_digest,runtime_root);row['verification_reconciliation_ids'].append(rid);row['verification_passed_count']+=int(passed);_save(row,runtime_root)
   if not passed:raise RuntimeError('cross_language_verification_failed')
  staged=stage_owned_changes(wid,owned_file_operation_ids=list(row['file_operation_ids']),active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not staged.get('ok'):raise RuntimeError('cross_language_git_stage')
  row['git_stage_operation_id']=str((staged.get('git_operation') or {}).get('operation_id') or '');committed=commit_owned_changes(wid,stage_operation_id=row['git_stage_operation_id'],commit_message=commit_message,active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not committed.get('ok'):raise RuntimeError('cross_language_git_commit')
  row['git_commit_operation_id']=str((committed.get('git_operation') or {}).get('operation_id') or '');row['transaction_state']='verified_candidate';_save(row,runtime_root)
 except Exception as e:row['transaction_state']='failed';row['failure_stage']=str(e);row['partial_commit_created']=bool(row.get('git_commit_operation_id'));_save(row,runtime_root)
 finally:
  for pid in pids:
   try:
    if (monitor_candidate_process(pid,runtime_root=runtime_root).get('process_operation') or {}).get('process_state') not in TERMINAL:stop_candidate_process(pid,active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix)
   except Exception:pass
  if wid and cleanup_on_complete:
   try:row['workspace_cleaned']=cleanup_disposable_workspace(wid,active_grant=active_grant,discard_owned_changes=True,runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable).get('cleaned') is True
   except Exception:row['workspace_cleaned']=False
  row['host_recoverable']=bool(not cleanup_on_complete or row.get('workspace_cleaned'))
  if row['transaction_state']=='verified_candidate' and row['host_recoverable']:row['transaction_state']='completed'
  _save(row,runtime_root)
 ok=row['transaction_state']=='completed';return {'ok':ok,'status':'cross_language_change_completed' if ok else 'cross_language_change_failed','cross_language_change':public_cross_language_change(row),'action_executed':row['action_executed'],**CROSS_LANGUAGE_DENIED_AUTHORITY}
def public_cross_language_change(row:Mapping[str,Any])->dict[str,Any]:
 if not row:return {}
 return {k:row.get(k) for k in ('contract_version','cross_language_change_id','source_workspace_digest','transaction_state','failure_stage','workspace_id','file_operation_ids','validation_passed_count','verification_process_ids','verification_reconciliation_ids','verification_passed_count','git_stage_operation_id','git_commit_operation_id','workspace_cleaned','host_recoverable','partial_commit_created','action_executed')}|{'raw_paths_exposed':False,'raw_content_exposed':False,'raw_commands_exposed':False,'selected_source_content_modified':False,'candidate_only':True,**CROSS_LANGUAGE_DENIED_AUTHORITY}
def load_cross_language_change(op:str,*,runtime_root=None):return public_cross_language_change(_load(op,runtime_root))
def process_cross_language_change_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show cross language change','inspect cross language change','show cross-language change'}:return {'active':False}
 op=str((project_state or {}).get('cross_language_change_id') or '');row=load_cross_language_change(op,runtime_root=runtime_root) if op else {};return {'active':True,'ok':bool(row),'status':'cross_language_change_found' if row else 'cross_language_change_missing','cross_language_change':row,'action_executed':False,**CROSS_LANGUAGE_DENIED_AUTHORITY}
