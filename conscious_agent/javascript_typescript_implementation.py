from __future__ import annotations
"""v1342 repository-aware JavaScript/TypeScript implementation skill.

The skill reuses Phase 4 isolation/file/Git/process/reconciliation contracts. It
never installs packages or contacts the network. Public evidence contains only
counts, digests, classifications, and lower-layer receipt identifiers.
"""
import hashlib,re,shutil,time
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
from ordinary_chat_development_campaign import _atomic_json,_read_json,_store_root
from workspace_isolation import create_disposable_workspace,cleanup_disposable_workspace
from structured_file_operations import read_candidate_file,patch_candidate_file
from typed_git_operations import stage_owned_changes,commit_owned_changes
from typed_process_operations import start_candidate_process,monitor_candidate_process,stop_candidate_process
from tool_result_reconciliation import reconcile_tool_result

CONTRACT_VERSION='v1342.8'
SUFFIXES=('.js','.mjs','.cjs','.ts','.mts','.cts','.tsx')
TS_SUFFIXES=('.ts','.mts','.cts','.tsx')
REQUIRED_PRECONDITIONS=('git','file_read','file_patch','shell')
MAX_ANALYSIS_BYTES=2*1024*1024
MAX_FILES=4096
MAX_WAIT_SECONDS=45.0
TERMINAL={'completed','failed','cancelled','interrupted','uncertain'}
JS_TS_DENIED_AUTHORITY={**DENIED_AUTHORITY,'dependency_installation_authorized':False,'network_authorized':False,'source_mutation_authorized':False,'source_application_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
_BUILTINS={'assert','buffer','crypto','events','fs','module','os','path','process','stream','string_decoder','timers','tty','url','util','v8','vm','zlib','node:test','test'}

def _root(runtime_root=None): return _store_root(runtime_root)/'phase5_javascript_typescript_implementation'
def _path(op_id,runtime_root=None):
 if not re.fullmatch(r'jsimpl_[a-f0-9]{24}',str(op_id or '')): raise ValueError('invalid_javascript_typescript_implementation_id')
 return _root(runtime_root)/'records'/f'{op_id}.json'
def _load(op_id,runtime_root=None):
 row=_read_json(_path(op_id,runtime_root));return row if row and row.get('record_digest')==digest({k:v for k,v in row.items() if k!='record_digest'}) else {}
def _save(row,runtime_root=None): row.pop('record_digest',None);row['record_digest']=digest(row);_atomic_json(_path(row['implementation_id'],runtime_root),row);return row

def _safe_rel(relative_path:str)->str:
 text=str(relative_path or '').replace('\\','/').strip();p=PurePosixPath(text)
 if not text or p.is_absolute() or any(x in {'','.','..'} for x in p.parts): raise ValueError('unsafe_javascript_typescript_relative_path')
 if p.suffix.lower() not in SUFFIXES: raise ValueError('javascript_typescript_source_required')
 if any(x.casefold() in {'.git','data','runtime','private','secrets','credentials','node_modules','.venv','venv','__pycache__'} for x in p.parts): raise ValueError('protected_javascript_typescript_path')
 return p.as_posix()

def _imports(text:str)->set[str]:
 out=set()
 for pat in (r"\bfrom\s+['\"]([^'\"]+)['\"]",r"\bimport\s+['\"]([^'\"]+)['\"]",r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"):
  out.update(re.findall(pat,text))
 return out

def _external_imports(text:str)->list[str]:
 rows=[]
 for item in sorted(_imports(text)):
  base=item[5:] if item.startswith('node:') else item
  if item.startswith(('.', '/')) or base in _BUILTINS: continue
  rows.append(item.split('/')[0] if not item.startswith('@') else '/'.join(item.split('/')[:2]))
 return sorted(set(rows))

def _exports(text:str)->tuple[dict[str,str],dict[str,str]]:
 kinds={};sigs={}
 patterns=[
  (r'\bexport\s+(async\s+)?function\s+([A-Za-z_$][\w$]*)\s*(\([^)]*\)(?:\s*:\s*[^\{=;]+)?)','function'),
  (r'\bexport\s+class\s+([A-Za-z_$][\w$]*)','class'),
  (r'\bexport\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)','value'),
 ]
 for pat,kind in patterns:
  for m in re.finditer(pat,text):
   if kind=='function':
    name=m.group(2);k='async_function' if m.group(1) else 'function';shape=re.sub(r'\s+',' ',m.group(3).strip())
   else:
    name=m.group(1);k=kind;shape=k
   kinds[name]=k;sigs[name]=hashlib.sha256(shape.encode()).hexdigest()
 for m in re.finditer(r'\b(?:exports|module\.exports)\.([A-Za-z_$][\w$]*)\s*=\s*(async\s+)?(?:function\s*)?(\([^)]*\)|[A-Za-z_$][\w$]*)?',text):
  name=m.group(1);k='async_function' if m.group(2) else 'value';shape=re.sub(r'\s+',' ',str(m.group(3) or k));kinds.setdefault(name,k);sigs.setdefault(name,hashlib.sha256(shape.encode()).hexdigest())
 return kinds,sigs

def _facts(text:str)->dict[str,Any]:
 raw=text.encode('utf-8')
 if len(raw)>MAX_ANALYSIS_BYTES: raise ValueError('javascript_typescript_analysis_budget_exceeded')
 esm=bool(re.search(r'(^|\n)\s*(?:import\s|export\s)',text));cjs=bool(re.search(r'\brequire\s*\(|\bmodule\.exports\b|\bexports\.',text))
 system='mixed' if esm and cjs else 'esm' if esm else 'commonjs' if cjs else 'script'
 kinds,sigs=_exports(text);external=_external_imports(text)
 return {'module_digest':hashlib.sha256(raw).hexdigest(),'module_system':system,'exported_symbols':sorted(kinds),'export_kinds':{k:kinds[k] for k in sorted(kinds)},'export_signature_digests':{k:sigs[k] for k in sorted(sigs)},'async_export_count':sum(v=='async_function' for v in kinds.values()),'external_imports':external,'browser_api_markers':sum(len(re.findall(rf'\b{x}\b',text)) for x in ('window','document','customElements','HTMLElement')),'state_management_markers':sum(len(re.findall(p,text)) for p in (r'\buseState\s*\(',r'\buseReducer\s*\(',r'\bcreateStore\s*\(',r'\bnew\s+Map\s*\(',r'\bnew\s+Set\s*\(')),'promise_async_markers':len(re.findall(r'\b(?:async|await|Promise)\b',text)),'typescript_annotation_markers':len(re.findall(r'[:]\s*[A-Za-z_$][\w$<>,\[\]| &.?]*',text))}

def _compat(before:Mapping[str,Any],after:Mapping[str,Any],*,allow_export_change:bool,allow_dependency_change:bool,allow_module_system_change:bool)->dict[str,Any]:
 b=set(before.get('exported_symbols') or []);a=set(after.get('exported_symbols') or []);removed=sorted(b-a)
 kind_changes=sorted(n for n in b&a if (before.get('export_kinds') or {}).get(n)!=(after.get('export_kinds') or {}).get(n))
 bs=dict(before.get('export_signature_digests') or {});as_=dict(after.get('export_signature_digests') or {});sig_changes=sorted(n for n in bs.keys()&as_.keys() if bs[n]!=as_[n])
 added_deps=sorted(set(after.get('external_imports') or [])-set(before.get('external_imports') or []));module_change=before.get('module_system')!=after.get('module_system')
 reasons=[]
 if (removed or kind_changes or sig_changes) and not allow_export_change: reasons.append('undeclared_export_contract_change')
 if added_deps and not allow_dependency_change: reasons.append('undeclared_external_dependency')
 if module_change and not allow_module_system_change: reasons.append('undeclared_module_system_change')
 return {'compatible':not reasons,'reasons':reasons,'removed_export_count':len(removed),'export_kind_change_count':len(kind_changes),'export_signature_change_count':len(sig_changes),'added_external_dependency_count':len(added_deps),'module_system_changed':module_change,'before_async_export_count':int(before.get('async_export_count') or 0),'after_async_export_count':int(after.get('async_export_count') or 0),'browser_api_marker_delta':int(after.get('browser_api_markers') or 0)-int(before.get('browser_api_markers') or 0),'state_management_marker_delta':int(after.get('state_management_markers') or 0)-int(before.get('state_management_markers') or 0)}

def inspect_javascript_typescript_project(source_root:str|Path)->dict[str,Any]:
 root=Path(source_root).resolve(strict=True);files=[];js=ts=browser=asyncs=state=0;systems=set();external=set();package=False;tsconfig=False
 for p in sorted(root.rglob('*')):
  if not p.is_file(): continue
  rel=p.relative_to(root)
  if any(x in {'.git','node_modules','data','runtime','private','__pycache__'} for x in rel.parts): continue
  if rel.as_posix()=='package.json': package=True;continue
  if rel.as_posix()=='tsconfig.json': tsconfig=True;continue
  if p.suffix.lower() not in SUFFIXES or p.stat().st_size>MAX_ANALYSIS_BYTES or len(files)>=MAX_FILES: continue
  try:f=_facts(p.read_text(encoding='utf-8'))
  except (OSError,UnicodeDecodeError,ValueError):continue
  files.append(p);js+=p.suffix.lower() not in TS_SUFFIXES;ts+=p.suffix.lower() in TS_SUFFIXES;browser+=f['browser_api_markers'];asyncs+=f['promise_async_markers'];state+=f['state_management_markers'];systems.add(f['module_system']);external.update(f['external_imports'])
 out={'contract_version':CONTRACT_VERSION,'source_file_count':len(files),'javascript_file_count':js,'typescript_file_count':ts,'package_json_present':package,'tsconfig_present':tsconfig,'module_systems':sorted(systems),'external_dependency_count':len(external),'browser_api_marker_count':browser,'async_marker_count':asyncs,'state_management_marker_count':state,'inspection_truncated':len(files)>=MAX_FILES,'source_manifest_digest':digest([(p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),'inspection_only':True,'network_contacted':False,'dependency_installed':False,**JS_TS_DENIED_AUTHORITY};out['inspection_digest']=digest(out);return out

def _wait(pid:str,workspace_digest:str,runtime_root=None):
 deadline=time.monotonic()+MAX_WAIT_SECONDS;obs={}
 while time.monotonic()<deadline:
  obs=monitor_candidate_process(pid,runtime_root=runtime_root);state=(obs.get('process_operation') or {}).get('process_state')
  if state in TERMINAL:break
  time.sleep(.05)
 proc=obs.get('process_operation') or {};passed=proc.get('process_state')=='completed' and proc.get('return_code')==0 and not proc.get('timed_out') and not proc.get('log_limit_exceeded')
 rec=reconcile_tool_result(tool_code='shell',operation_id=pid,wrapper_observation={'wrapper_status':'returned','reported_status':proc.get('process_state')},current_workspace_digest=workspace_digest,runtime_root=runtime_root)
 return passed,str((rec.get('reconciliation') or {}).get('reconciliation_id') or '')

def run_javascript_typescript_implementation(*,source_root:str|Path,source_workspace_digest:str,active_grant:Mapping[str,Any],precondition_record_ids:Mapping[str,str],relative_path:str,expected_content_digest:str,patches:Sequence[Mapping[str,Any]],test_argv:Sequence[str],commit_message:str,allow_export_change:bool=False,allow_dependency_change:bool=False,allow_module_system_change:bool=False,runtime_root=None,now_unix:int|None=None,git_executable:str|None=None,node_executable:str|None=None,tsc_executable:str|None=None,cleanup_on_complete:bool=True)->dict[str,Any]:
 try: rel=_safe_rel(relative_path)
 except ValueError as e:return {'ok':False,'status':str(e),'action_executed':False,**JS_TS_DENIED_AUTHORITY}
 pres={str(k):str(v) for k,v in precondition_record_ids.items()}
 if any(not pres.get(k) for k in REQUIRED_PRECONDITIONS):return {'ok':False,'status':'complete_javascript_typescript_preconditions_required','action_executed':False,**JS_TS_DENIED_AUTHORITY}
 spec={'contract':CONTRACT_VERSION,'source':source_workspace_digest,'grant':active_grant.get('grant_digest'),'preconditions':pres,'path':hashlib.sha256(rel.encode()).hexdigest(),'expected':expected_content_digest,'patches':digest(patches),'tests':digest(list(test_argv)),'commit':hashlib.sha256(str(commit_message).encode()).hexdigest(),'allow_export':allow_export_change,'allow_dependency':allow_dependency_change,'allow_module':allow_module_system_change,'cleanup':cleanup_on_complete}
 op='jsimpl_'+digest(spec)[:24];existing=_load(op,runtime_root)
 if existing:return {'ok':existing.get('implementation_state')=='completed','status':'javascript_typescript_implementation_already_exists','javascript_typescript_implementation':public_javascript_typescript_implementation(existing),'action_executed':False,**JS_TS_DENIED_AUTHORITY}
 row={'contract_version':CONTRACT_VERSION,'implementation_id':op,'source_workspace_digest':source_workspace_digest,'grant_digest':active_grant.get('grant_digest'),'implementation_state':'starting','failure_stage':'','workspace_id':'','file_operation_id':'','git_stage_operation_id':'','git_commit_operation_id':'','language':'typescript' if PurePosixPath(rel).suffix.lower() in TS_SUFFIXES else 'javascript','check_process_id':'','check_reconciliation_id':'','test_process_id':'','test_reconciliation_id':'','compatibility_summary':{},'compatibility_passed':False,'syntax_or_typecheck_passed':False,'tests_passed':False,'workspace_cleaned':False,'host_recoverable':False,'action_executed':False,**JS_TS_DENIED_AUTHORITY};_save(row,runtime_root)
 wid='';pids=[]
 try:
  iso=create_disposable_workspace(source_root=source_root,source_workspace_digest=source_workspace_digest,active_grant=active_grant,precondition_record_id=pres['git'],mode='git_branch_worktree',retention_rule='retain_for_review',runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not iso.get('ok') or not iso.get('workspace_created'):raise RuntimeError('workspace_isolation')
  wid=str(iso['workspace_id']);row['workspace_id']=wid;row['action_executed']=True;_save(row,runtime_root)
  b=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
  if not b.get('ok'):raise RuntimeError('javascript_typescript_read_before')
  before_text=str(b.get('content') or '');before=_facts(before_text)
  if before['module_digest']!=expected_content_digest:raise RuntimeError('stale_javascript_typescript_content_digest')
  patch=patch_candidate_file(wid,rel,expected_content_digest=expected_content_digest,patches=patches,active_grant=active_grant,precondition_record_id=pres['file_patch'],runtime_root=runtime_root,now_unix=now_unix)
  if not patch.get('ok'):raise RuntimeError(str(patch.get('status') or 'javascript_typescript_patch'))
  row['file_operation_id']=str((patch.get('file_operation') or {}).get('operation_id') or '');_save(row,runtime_root)
  a=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
  if not a.get('ok'):raise RuntimeError('javascript_typescript_read_after')
  after=_facts(str(a.get('content') or ''));compat=_compat(before,after,allow_export_change=allow_export_change,allow_dependency_change=allow_dependency_change,allow_module_system_change=allow_module_system_change);row['compatibility_summary']=compat;row['compatibility_passed']=bool(compat['compatible']);_save(row,runtime_root)
  if not compat['compatible']:raise RuntimeError(compat['reasons'][0])
  if row['language']=='typescript':
   exe=str(tsc_executable or shutil.which('tsc') or '');
   if not exe:raise RuntimeError('typescript_compiler_unavailable')
   argv=[exe,'--noEmit','--pretty','false','--strict','--target','ES2022','--module','NodeNext','--moduleResolution','NodeNext',rel]
  else:
   exe=str(node_executable or shutil.which('node') or '')
   if not exe:raise RuntimeError('node_runtime_unavailable')
   argv=[exe,'--check',rel]
  chk=start_candidate_process(wid,argv,active_grant=active_grant,precondition_record_id=pres['shell'],runtime_root=runtime_root,now_unix=now_unix,timeout_seconds=30,invocation_discriminator=f'v1342:{op}:check')
  if not chk.get('ok'):raise RuntimeError('javascript_typescript_check_start')
  pid=str((chk.get('process_operation') or {}).get('process_operation_id') or '');pids.append(pid);row['check_process_id']=pid;_save(row,runtime_root);passed,rec=_wait(pid,source_workspace_digest,runtime_root);row['syntax_or_typecheck_passed']=passed;row['check_reconciliation_id']=rec;_save(row,runtime_root)
  if not passed:raise RuntimeError('javascript_typescript_check_failed')
  if not test_argv:raise RuntimeError('focused_javascript_typescript_tests_required')
  tst=start_candidate_process(wid,list(test_argv),active_grant=active_grant,precondition_record_id=pres['shell'],runtime_root=runtime_root,now_unix=now_unix,timeout_seconds=40,invocation_discriminator=f'v1342:{op}:tests')
  if not tst.get('ok'):raise RuntimeError('javascript_typescript_test_start')
  pid=str((tst.get('process_operation') or {}).get('process_operation_id') or '');pids.append(pid);row['test_process_id']=pid;_save(row,runtime_root);passed,rec=_wait(pid,source_workspace_digest,runtime_root);row['tests_passed']=passed;row['test_reconciliation_id']=rec;_save(row,runtime_root)
  if not passed:raise RuntimeError('javascript_typescript_tests_failed')
  st=stage_owned_changes(wid,owned_file_operation_ids=[row['file_operation_id']],active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not st.get('ok'):raise RuntimeError('javascript_typescript_git_stage')
  row['git_stage_operation_id']=str((st.get('git_operation') or {}).get('operation_id') or '');_save(row,runtime_root)
  cm=commit_owned_changes(wid,stage_operation_id=row['git_stage_operation_id'],commit_message=commit_message,active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not cm.get('ok'):raise RuntimeError('javascript_typescript_git_commit')
  row['git_commit_operation_id']=str((cm.get('git_operation') or {}).get('operation_id') or '');row['implementation_state']='verified_candidate';_save(row,runtime_root)
 except Exception as e: row['implementation_state']='failed';row['failure_stage']=str(e);_save(row,runtime_root)
 finally:
  for pid in pids:
   try:
    obs=monitor_candidate_process(pid,runtime_root=runtime_root)
    if (obs.get('process_operation') or {}).get('process_state') not in TERMINAL:stop_candidate_process(pid,active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix)
   except Exception:pass
  if wid and cleanup_on_complete:
   try:row['workspace_cleaned']=cleanup_disposable_workspace(wid,active_grant=active_grant,discard_owned_changes=True,runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable).get('cleaned') is True
   except Exception:row['workspace_cleaned']=False
  row['host_recoverable']=bool(not cleanup_on_complete or row['workspace_cleaned'])
  if row['implementation_state']=='verified_candidate' and row['host_recoverable']:row['implementation_state']='completed'
  _save(row,runtime_root)
 ok=row['implementation_state']=='completed';return {'ok':ok,'status':'javascript_typescript_implementation_completed' if ok else 'javascript_typescript_implementation_failed','javascript_typescript_implementation':public_javascript_typescript_implementation(row),'action_executed':row['action_executed'] is True,**JS_TS_DENIED_AUTHORITY}

def public_javascript_typescript_implementation(row:Mapping[str,Any])->dict[str,Any]:
 if not row:return {}
 return {'contract_version':CONTRACT_VERSION,'implementation_id':row.get('implementation_id'),'source_workspace_digest':row.get('source_workspace_digest'),'implementation_state':row.get('implementation_state'),'failure_stage':row.get('failure_stage') or '','language':row.get('language'),'workspace_id':row.get('workspace_id') or '','file_operation_id':row.get('file_operation_id') or '','git_stage_operation_id':row.get('git_stage_operation_id') or '','git_commit_operation_id':row.get('git_commit_operation_id') or '','check_process_id':row.get('check_process_id') or '','check_reconciliation_id':row.get('check_reconciliation_id') or '','test_process_id':row.get('test_process_id') or '','test_reconciliation_id':row.get('test_reconciliation_id') or '','compatibility_summary':dict(row.get('compatibility_summary') or {}),'compatibility_passed':row.get('compatibility_passed') is True,'syntax_or_typecheck_passed':row.get('syntax_or_typecheck_passed') is True,'tests_passed':row.get('tests_passed') is True,'workspace_cleaned':row.get('workspace_cleaned') is True,'host_recoverable':row.get('host_recoverable') is True,'candidate_only':True,'selected_source_content_modified':False,'raw_source_exposed':False,'raw_test_command_exposed':False,'dependency_installed':False,'network_contacted':False,'action_executed':row.get('action_executed') is True,**JS_TS_DENIED_AUTHORITY}

def load_javascript_typescript_implementation(op_id:str,*,runtime_root=None):
 row=_load(op_id,runtime_root);return public_javascript_typescript_implementation(row) if row else {}
def process_javascript_typescript_implementation_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show javascript implementation checkpoint','show typescript implementation checkpoint','show javascript typescript implementation','inspect javascript typescript implementation'}:return {'active':False}
 op=str((project_state or {}).get('javascript_typescript_implementation_id') or '');row=load_javascript_typescript_implementation(op,runtime_root=runtime_root) if op else {}
 return {'active':True,'ok':bool(row),'status':'javascript_typescript_implementation_found' if row else 'javascript_typescript_implementation_missing','javascript_typescript_implementation':row,'action_executed':False,**JS_TS_DENIED_AUTHORITY}
__all__=['CONTRACT_VERSION','SUFFIXES','TS_SUFFIXES','REQUIRED_PRECONDITIONS','JS_TS_DENIED_AUTHORITY','inspect_javascript_typescript_project','run_javascript_typescript_implementation','public_javascript_typescript_implementation','load_javascript_typescript_implementation','process_javascript_typescript_implementation_control']
