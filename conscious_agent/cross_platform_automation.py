from __future__ import annotations
"""v1346 explicit Windows/POSIX automation without shell-string authority drift."""
import hashlib, os, re, shlex, shutil, subprocess, time
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json,_read_json,_store_root
from workspace_isolation import create_disposable_workspace,cleanup_disposable_workspace
from structured_file_operations import read_candidate_file,patch_candidate_file
from typed_git_operations import stage_owned_changes,commit_owned_changes
from typed_process_operations import start_candidate_process,monitor_candidate_process,stop_candidate_process
from tool_result_reconciliation import reconcile_tool_result
from windows_automation import windows_command_line, normalize_windows_path, windows_path_within, _powershell_lexical

CONTRACT_VERSION='v1346.8';MAX_ANALYSIS_BYTES=2*1024*1024;MAX_PROCESS_WAIT_SECONDS=45.0
REQUIRED_PRECONDITIONS=('git','file_read','file_patch','shell');TERMINAL={'completed','failed','cancelled','interrupted','uncertain'}
CROSS_PLATFORM_DENIED_AUTHORITY={**DENIED_AUTHORITY,'source_mutation_authorized':False,'source_application_authorized':False,'network_authorized':False,'dependency_installation_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}

def _root(runtime_root=None):return _store_root(runtime_root)/'phase5_cross_platform_automation'
def _path(op,runtime_root=None):
 if not re.fullmatch(r'xplat_[a-f0-9]{24}',str(op or '')):raise ValueError('invalid_cross_platform_operation_id')
 return _root(runtime_root)/'records'/f'{op}.json'
def _load(op,runtime_root=None):
 row=_read_json(_path(op,runtime_root));return row if row and row.get('record_digest')==digest({k:v for k,v in row.items() if k!='record_digest'}) else {}
def _save(row,runtime_root=None):row.pop('record_digest',None);row['record_digest']=digest(row);_atomic_json(_path(row['cross_platform_operation_id'],runtime_root),row);return row

def target_platform(value:str)->str:
 v=str(value or '').strip().lower()
 if v in {'windows','win32','nt'}:return 'windows'
 if v in {'posix','linux','darwin','macos','unix'}:return 'posix'
 raise ValueError('unsupported_target_platform')
def render_argument_vector(argv:Sequence[str],platform:str)->str:
 p=target_platform(platform);args=[str(x) for x in argv]
 if not args:raise ValueError('empty_argument_vector')
 return windows_command_line(args) if p=='windows' else shlex.join(args)
def sanitize_environment(overrides:Mapping[str,str]|None=None,*,platform:str='posix')->dict[str,str]:
 p=target_platform(platform);blocked={'LD_PRELOAD','LD_LIBRARY_PATH','PYTHONPATH','PYTHONHOME','DYLD_INSERT_LIBRARIES','DYLD_LIBRARY_PATH'} if p=='posix' else {'COMSPEC','PATHEXT','PSModulePath'}
 out={}
 for k,v in (overrides or {}).items():
  key=str(k)
  if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',key) or key in blocked:continue
  val=str(v)
  if '\x00' in val or len(val)>4096:continue
  out[key]=val
 return dict(sorted(out.items()))
def normalize_portable_relative(value:str)->str:
 s=str(value or '').replace('\\','/').strip();p=PurePosixPath(s)
 if not s or p.is_absolute() or any(x in {'','.','..'} for x in p.parts):raise ValueError('unsafe_portable_relative_path')
 if any(x.casefold() in {'.git','data','runtime','private','secrets','credentials','node_modules','.venv','venv','__pycache__'} for x in p.parts):raise ValueError('protected_portable_path')
 return p.as_posix()
def platform_capability_record(platform:str)->dict[str,Any]:
 p=target_platform(platform);host='windows' if os.name=='nt' else 'posix';shell=shutil.which('powershell') or shutil.which('pwsh') if p=='windows' else shutil.which('sh')
 row={'contract_version':CONTRACT_VERSION,'target_platform':p,'host_platform':host,'host_matches_target':host==p,'native_shell_available':bool(shell),'native_execution_validated':False,'argument_vector_required':True,'shell_string_execution_allowed':False,'windows_semantics_preserved':True,'inspection_only':True,**CROSS_PLATFORM_DENIED_AUTHORITY};row['capability_digest']=digest(row);return row
def inspect_cross_platform_project(source_root:str|Path)->dict[str,Any]:
 root=Path(source_root).resolve(strict=True);counts={'posix':0,'windows':0};files=[]
 for p in sorted(root.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(root)
  if any(x in {'.git','data','runtime','private','node_modules','__pycache__'} for x in rel.parts) or p.stat().st_size>MAX_ANALYSIS_BYTES:continue
  suf=p.suffix.lower()
  if suf in {'.sh','.bash'}:counts['posix']+=1;files.append(p)
  elif suf in {'.ps1','.psm1','.bat','.cmd'}:counts['windows']+=1;files.append(p)
 out={'contract_version':CONTRACT_VERSION,'posix_script_count':counts['posix'],'windows_script_count':counts['windows'],'host_platform':'windows' if os.name=='nt' else 'posix','source_manifest_digest':digest([(p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),'inspection_only':True,'native_windows_execution_validated':False,'network_contacted':False,**CROSS_PLATFORM_DENIED_AUTHORITY};out['inspection_digest']=digest(out);return out

def _validate_script(path:str,text:str,platform:str)->dict[str,Any]:
 p=target_platform(platform);suffix=PurePosixPath(path).suffix.lower()
 if len(text.encode('utf-8'))>MAX_ANALYSIS_BYTES:return {'valid':False,'reason':'script_analysis_budget_exceeded'}
 if p=='windows':
  if suffix not in {'.ps1','.psm1','.bat','.cmd'}:return {'valid':False,'reason':'windows_script_required'}
  if suffix in {'.ps1','.psm1'}:
   lex=_powershell_lexical(text);return {'valid':bool(lex['syntax_valid']),'reason':'' if lex['syntax_valid'] else 'powershell_lexical_invalid'}
  return {'valid':'\x00' not in text,'reason':'' if '\x00' not in text else 'batch_script_invalid'}
 if suffix not in {'.sh','.bash'}:return {'valid':False,'reason':'posix_script_required'}
 sh=shutil.which('sh')
 if not sh:return {'valid':False,'reason':'posix_shell_unavailable'}
 cp=subprocess.run([sh,'-n'],input=text,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
 return {'valid':cp.returncode==0,'reason':'' if cp.returncode==0 else 'posix_shell_syntax_invalid'}

def _wait(pid:str,workspace_digest:str,runtime_root=None):
 deadline=time.monotonic()+MAX_PROCESS_WAIT_SECONDS;obs={}
 while time.monotonic()<deadline:
  obs=monitor_candidate_process(pid,runtime_root=runtime_root);state=(obs.get('process_operation') or {}).get('process_state')
  if state in TERMINAL:break
  time.sleep(.05)
 proc=obs.get('process_operation') or {};passed=proc.get('process_state')=='completed' and proc.get('return_code')==0 and not proc.get('timed_out') and not proc.get('log_limit_exceeded')
 rec=reconcile_tool_result(tool_code='shell',operation_id=pid,wrapper_observation={'wrapper_status':'returned','reported_status':proc.get('process_state')},current_workspace_digest=workspace_digest,runtime_root=runtime_root)
 return passed,str((rec.get('reconciliation') or {}).get('reconciliation_id') or '')

def run_cross_platform_automation(*,source_root:str|Path,source_workspace_digest:str,active_grant:Mapping[str,Any],precondition_record_ids:Mapping[str,str],relative_path:str,expected_content_digest:str,patches:Sequence[Mapping[str,Any]],target:str,test_argv:Sequence[str],commit_message:str='Refine portable automation',runtime_root=None,now_unix:int|None=None,git_executable:str|None=None,cleanup_on_complete:bool=True)->dict[str,Any]:
 try:rel=normalize_portable_relative(relative_path);plat=target_platform(target)
 except ValueError as e:return {'ok':False,'status':str(e),'action_executed':False,**CROSS_PLATFORM_DENIED_AUTHORITY}
 pres={str(k):str(v) for k,v in precondition_record_ids.items()}
 if any(not pres.get(k) for k in REQUIRED_PRECONDITIONS):return {'ok':False,'status':'complete_cross_platform_preconditions_required','action_executed':False,**CROSS_PLATFORM_DENIED_AUTHORITY}
 spec={'contract':CONTRACT_VERSION,'source':source_workspace_digest,'grant':active_grant.get('grant_digest'),'pre':pres,'path':hashlib.sha256(rel.encode()).hexdigest(),'expected':expected_content_digest,'patch':digest(patches),'platform':plat,'test':digest(list(test_argv)),'commit':hashlib.sha256(commit_message.encode()).hexdigest(),'cleanup':cleanup_on_complete};op='xplat_'+digest(spec)[:24];existing=_load(op,runtime_root)
 if existing:return {'ok':existing.get('implementation_state')=='completed','status':'cross_platform_automation_already_exists','cross_platform_automation':public_cross_platform_automation(existing),'action_executed':False,**CROSS_PLATFORM_DENIED_AUTHORITY}
 row={'contract_version':CONTRACT_VERSION,'cross_platform_operation_id':op,'source_workspace_digest':source_workspace_digest,'target_platform':plat,'implementation_state':'starting','failure_stage':'','workspace_id':'','file_operation_id':'','test_process_id':'','test_reconciliation_id':'','git_stage_operation_id':'','git_commit_operation_id':'','syntax_valid':False,'tests_passed':False,'workspace_cleaned':False,'host_recoverable':False,'native_execution_validated':False,'action_executed':False,**CROSS_PLATFORM_DENIED_AUTHORITY};_save(row,runtime_root);wid='';pids=[]
 try:
  isolated=create_disposable_workspace(source_root=source_root,source_workspace_digest=source_workspace_digest,active_grant=active_grant,precondition_record_id=pres['git'],mode='git_branch_worktree',retention_rule='retain_for_review',runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not isolated.get('ok') or not isolated.get('workspace_created'):raise RuntimeError('workspace_isolation')
  wid=str(isolated['workspace_id']);row['workspace_id']=wid;row['action_executed']=True;_save(row,runtime_root)
  before=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
  if not before.get('ok') or str((before.get('file_operation') or {}).get('before_digest') or '')!=expected_content_digest:raise RuntimeError('stale_portable_content_digest')
  patched=patch_candidate_file(wid,rel,expected_content_digest=expected_content_digest,patches=patches,active_grant=active_grant,precondition_record_id=pres['file_patch'],runtime_root=runtime_root,now_unix=now_unix)
  if not patched.get('ok'):raise RuntimeError(str(patched.get('status') or 'portable_patch'))
  row['file_operation_id']=str((patched.get('file_operation') or {}).get('operation_id') or '')
  after=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
  verdict=_validate_script(rel,str(after.get('content') or ''),plat);row['syntax_valid']=bool(verdict.get('valid'));_save(row,runtime_root)
  if not row['syntax_valid']:raise RuntimeError(str(verdict.get('reason') or 'portable_syntax_invalid'))
  if not test_argv:raise RuntimeError('focused_portable_tests_required')
  started=start_candidate_process(wid,list(test_argv),active_grant=active_grant,precondition_record_id=pres['shell'],runtime_root=runtime_root,now_unix=now_unix,timeout_seconds=40,invocation_discriminator=f'v1346:{op}:tests')
  if not started.get('ok'):raise RuntimeError('portable_test_start')
  pid=str((started.get('process_operation') or {}).get('process_operation_id') or '');pids.append(pid);row['test_process_id']=pid;_save(row,runtime_root);passed,rid=_wait(pid,source_workspace_digest,runtime_root);row['tests_passed']=passed;row['test_reconciliation_id']=rid;row['native_execution_validated']=bool(plat==('windows' if os.name=='nt' else 'posix') and passed);_save(row,runtime_root)
  if not passed:raise RuntimeError('portable_tests_failed')
  staged=stage_owned_changes(wid,owned_file_operation_ids=[row['file_operation_id']],active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not staged.get('ok'):raise RuntimeError('portable_git_stage')
  row['git_stage_operation_id']=str((staged.get('git_operation') or {}).get('operation_id') or '');committed=commit_owned_changes(wid,stage_operation_id=row['git_stage_operation_id'],commit_message=commit_message,active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not committed.get('ok'):raise RuntimeError('portable_git_commit')
  row['git_commit_operation_id']=str((committed.get('git_operation') or {}).get('operation_id') or '');row['implementation_state']='verified_candidate';_save(row,runtime_root)
 except Exception as e:row['implementation_state']='failed';row['failure_stage']=str(e);_save(row,runtime_root)
 finally:
  for pid in pids:
   try:
    if (monitor_candidate_process(pid,runtime_root=runtime_root).get('process_operation') or {}).get('process_state') not in TERMINAL:stop_candidate_process(pid,active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix)
   except Exception:pass
  if wid and cleanup_on_complete:
   try:row['workspace_cleaned']=cleanup_disposable_workspace(wid,active_grant=active_grant,discard_owned_changes=True,runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable).get('cleaned') is True
   except Exception:row['workspace_cleaned']=False
  row['host_recoverable']=bool(not cleanup_on_complete or row.get('workspace_cleaned'))
  if row.get('implementation_state')=='verified_candidate' and row['host_recoverable']:row['implementation_state']='completed'
  _save(row,runtime_root)
 ok=row.get('implementation_state')=='completed';return {'ok':ok,'status':'cross_platform_automation_completed' if ok else 'cross_platform_automation_failed','cross_platform_automation':public_cross_platform_automation(row),'action_executed':row.get('action_executed') is True,**CROSS_PLATFORM_DENIED_AUTHORITY}

def public_cross_platform_automation(row:Mapping[str,Any])->dict[str,Any]:
 if not row:return {}
 return {k:row.get(k) for k in ('contract_version','cross_platform_operation_id','source_workspace_digest','target_platform','implementation_state','failure_stage','workspace_id','file_operation_id','test_process_id','test_reconciliation_id','git_stage_operation_id','git_commit_operation_id','syntax_valid','tests_passed','workspace_cleaned','host_recoverable','native_execution_validated','action_executed')}|{'raw_script_exposed':False,'raw_command_exposed':False,'selected_source_content_modified':False,'candidate_only':True,**CROSS_PLATFORM_DENIED_AUTHORITY}
def load_cross_platform_automation(op:str,*,runtime_root=None):return public_cross_platform_automation(_load(op,runtime_root))
def process_cross_platform_automation_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show cross platform automation','inspect cross platform automation','show cross-platform automation'}:return {'active':False}
 op=str((project_state or {}).get('cross_platform_operation_id') or '');row=load_cross_platform_automation(op,runtime_root=runtime_root) if op else {};return {'active':True,'ok':bool(row),'status':'cross_platform_automation_found' if row else 'cross_platform_automation_missing','cross_platform_automation':row,'action_executed':False,**CROSS_PLATFORM_DENIED_AUTHORITY}
