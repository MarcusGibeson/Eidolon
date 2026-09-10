from __future__ import annotations
"""v1345 Windows-first automation semantics without fabricated native evidence."""
import codecs, hashlib, ntpath, os, re, shutil, subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json,_read_json,_store_root
from workspace_isolation import create_disposable_workspace,cleanup_disposable_workspace
from structured_file_operations import read_candidate_file,patch_candidate_file
from typed_git_operations import stage_owned_changes,commit_owned_changes

CONTRACT_VERSION='v1345.8';SUFFIXES=('.ps1','.psm1','.psd1','.bat','.cmd');REQUIRED_PRECONDITIONS=('git','file_read','file_patch');MAX_ANALYSIS_BYTES=2*1024*1024
WINDOWS_AUTOMATION_DENIED_AUTHORITY={**DENIED_AUTHORITY,'source_mutation_authorized':False,'source_application_authorized':False,'installer_execution_authorized':False,'service_mutation_authorized':False,'elevation_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'network_authorized':False,'independent_authority_granted':False}

def _root(runtime_root=None):return _store_root(runtime_root)/'phase5_windows_automation'
def _path(op,runtime_root=None):
 if not re.fullmatch(r'winimpl_[a-f0-9]{24}',str(op or '')):raise ValueError('invalid_windows_automation_id')
 return _root(runtime_root)/'records'/f'{op}.json'
def _load(op,runtime_root=None):
 row=_read_json(_path(op,runtime_root));return row if row and row.get('record_digest')==digest({k:v for k,v in row.items() if k!='record_digest'}) else {}
def _save(row,runtime_root=None):row.pop('record_digest',None);row['record_digest']=digest(row);_atomic_json(_path(row['windows_automation_id'],runtime_root),row);return row

def quote_powershell_literal(value:str)->str:return "'"+str(value).replace("'","''")+"'"
def windows_command_line(argv:Sequence[str])->str:return subprocess.list2cmdline([str(x) for x in argv])
def _reject_windows_path(raw:str):
 s=str(raw or '').strip()
 if not s:raise ValueError('empty_windows_path')
 low=s.casefold()
 if low.startswith(('\\\\?\\','\\\\.\\','\\?\\','\\.\\')):raise ValueError('windows_device_path_rejected')
 # Alternate data streams are not path components. Preserve the drive colon only.
 tail=s[2:] if re.match(r'^[A-Za-z]:',s) else s
 if ':' in tail:raise ValueError('windows_alternate_data_stream_rejected')
 return s
def normalize_windows_path(raw:str)->str:
 s=_reject_windows_path(raw);return ntpath.normpath(s.replace('/','\\'))
def windows_path_within(root:str,candidate:str)->bool:
 try:r=normalize_windows_path(root);c=normalize_windows_path(candidate);common=ntpath.commonpath([r,c]);return ntpath.normcase(common)==ntpath.normcase(r)
 except (ValueError,OSError):return False
def build_windows_service_argv(action:str,service_name:str)->list[str]:
 a=str(action or '').lower();name=str(service_name or '')
 if a not in {'query','start','stop'}:raise ValueError('unsupported_windows_service_action')
 if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',name):raise ValueError('invalid_windows_service_name')
 return ['sc.exe',a,name]
def build_windows_process_tree_stop_argv(pid:int,*,force:bool=True)->list[str]:
 p=int(pid)
 if p<=0:raise ValueError('invalid_windows_pid')
 return ['taskkill.exe','/PID',str(p),'/T']+(['/F'] if force else [])
def classify_installer_argv(argv:Sequence[str])->dict[str,Any]:
 words=[str(x) for x in argv];exe=PureWindowsPath(words[0]).name.casefold() if words else ''
 installer=exe in {'msiexec.exe','msiexec','winget.exe','winget','choco.exe','choco','scoop.cmd','scoop','setup.exe','installer.exe'} or any(x.casefold().endswith(('.msi','.msix','.appx','.appxbundle')) for x in words)
 elevating=any(x.casefold() in {'runas','-verb'} for x in words) and any(x.casefold()=='runas' for x in words)
 return {'installer_detected':installer,'elevation_detected':elevating,'argv_digest':digest(words),'execution_authorized':False,**WINDOWS_AUTOMATION_DENIED_AUTHORITY}

def _safe_rel(value:str)->str:
 s=str(value or '').replace('\\','/').strip();p=PurePosixPath(s)
 if not s or p.is_absolute() or any(x in {'','.','..'} for x in p.parts):raise ValueError('unsafe_windows_script_relative_path')
 if p.suffix.lower() not in SUFFIXES:raise ValueError('windows_script_required')
 if any(x.casefold() in {'.git','data','runtime','private','secrets','credentials','node_modules','.venv','venv','__pycache__'} for x in p.parts):raise ValueError('protected_windows_script_path')
 return p.as_posix()
def _powershell_lexical(text:str)->dict[str,Any]:
 if len(text.encode('utf-8'))>MAX_ANALYSIS_BYTES:raise ValueError('windows_script_analysis_budget_exceeded')
 stack=[];pairs={')':'(',']':'[','}':'{'};opens=set(pairs.values());single=double=False;i=0;line_comment=False
 while i<len(text):
  ch=text[i]
  if line_comment:
   if ch=='\n':line_comment=False
   i+=1;continue
  if single:
   if ch=="'":
    if i+1<len(text) and text[i+1]=="'":i+=2;continue
    single=False
   i+=1;continue
  if double:
   if ch=='`':i+=2;continue
   if ch=='"':double=False
   i+=1;continue
  if ch=='#':line_comment=True;i+=1;continue
  if ch=="'":single=True;i+=1;continue
  if ch=='"':double=True;i+=1;continue
  if ch in opens:stack.append(ch)
  elif ch in pairs:
   if not stack or stack.pop()!=pairs[ch]:return {'syntax_valid':False,'balance_depth':len(stack),'unterminated_quote':False}
  i+=1
 return {'syntax_valid':not stack and not single and not double,'balance_depth':len(stack),'unterminated_quote':single or double}
def _script_facts(path:str,text:str)->dict[str,Any]:
 suffix=PurePosixPath(path).suffix.lower();ps=suffix in {'.ps1','.psm1','.psd1'};lex=_powershell_lexical(text) if ps else {'syntax_valid':'\x00' not in text,'balance_depth':0,'unterminated_quote':False}
 installer=bool(re.search(r'(?i)\b(msiexec|winget|choco|scoop|setup\.exe)\b|\.msi\b',text));elevation=bool(re.search(r'(?i)-Verb\s+RunAs|Start-Process[^\n]+RunAs|#requires\s+-RunAsAdministrator',text));service=bool(re.search(r'(?i)\b(Start-Service|Stop-Service|Set-Service|sc(?:\.exe)?\s+(?:start|stop|config))\b',text));destructive=bool(re.search(r'(?i)\b(Remove-Item\b[^\n]*-Recurse[^\n]*-Force|Format-Volume|Clear-Disk)\b',text))
 return {'format':'powershell' if ps else 'batch','syntax_valid':bool(lex['syntax_valid']),'installer_marker':installer,'elevation_marker':elevation,'service_mutation_marker':service,'destructive_system_marker':destructive,'content_digest':hashlib.sha256(text.encode()).hexdigest(),'fact_digest':digest({'lex':lex,'installer':installer,'elevation':elevation,'service':service,'destructive':destructive})}
def _decode_script_bytes(data:bytes)->str:
 if data.startswith(codecs.BOM_UTF8):return data[len(codecs.BOM_UTF8):].decode('utf-8')
 if data.startswith(codecs.BOM_UTF16_LE):return data[len(codecs.BOM_UTF16_LE):].decode('utf-16-le')
 if data.startswith(codecs.BOM_UTF16_BE):return data[len(codecs.BOM_UTF16_BE):].decode('utf-16-be')
 return data.decode('utf-8')

def inspect_windows_automation_project(source_root:str|Path)->dict[str,Any]:
 root=Path(source_root).resolve(strict=True);counts={'powershell':0,'batch':0};invalid=installer=elev=service=0;files=[]
 for p in sorted(root.rglob('*')):
  if not p.is_file() or p.suffix.lower() not in SUFFIXES:continue
  rel=p.relative_to(root)
  if any(x in {'.git','data','runtime','private','node_modules','__pycache__'} for x in rel.parts) or p.stat().st_size>MAX_ANALYSIS_BYTES:continue
  try:f=_script_facts(rel.as_posix(),_decode_script_bytes(p.read_bytes()))
  except (OSError,UnicodeDecodeError,ValueError):invalid+=1;continue
  files.append(p);counts[f['format']]+=1;invalid+=int(not f['syntax_valid']);installer+=int(f['installer_marker']);elev+=int(f['elevation_marker']);service+=int(f['service_mutation_marker'])
 out={'contract_version':CONTRACT_VERSION,'powershell_file_count':counts['powershell'],'batch_file_count':counts['batch'],'invalid_script_count':invalid,'installer_marker_file_count':installer,'elevation_marker_file_count':elev,'service_mutation_marker_file_count':service,'native_windows_host':os.name=='nt','powershell_runtime_available':bool(shutil.which('pwsh') or shutil.which('powershell')),'native_windows_execution_validated':False,'source_manifest_digest':digest([(p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),'inspection_only':True,**WINDOWS_AUTOMATION_DENIED_AUTHORITY};out['inspection_digest']=digest(out);return out

def run_windows_automation_implementation(*,source_root:str|Path,source_workspace_digest:str,active_grant:Mapping[str,Any],precondition_record_ids:Mapping[str,str],relative_path:str,expected_content_digest:str,patches:Sequence[Mapping[str,Any]],commit_message:str='Refine Windows automation',installer_behavior_declared:bool=False,service_behavior_declared:bool=False,elevation_behavior_declared:bool=False,runtime_root=None,now_unix:int|None=None,git_executable:str|None=None,cleanup_on_complete:bool=True)->dict[str,Any]:
 try:rel=_safe_rel(relative_path)
 except ValueError as e:return {'ok':False,'status':str(e),'action_executed':False,**WINDOWS_AUTOMATION_DENIED_AUTHORITY}
 pres={str(k):str(v) for k,v in precondition_record_ids.items()}
 if any(not pres.get(k) for k in REQUIRED_PRECONDITIONS):return {'ok':False,'status':'complete_windows_automation_preconditions_required','action_executed':False,**WINDOWS_AUTOMATION_DENIED_AUTHORITY}
 spec={'contract':CONTRACT_VERSION,'source':source_workspace_digest,'grant':active_grant.get('grant_digest'),'pre':pres,'path':hashlib.sha256(rel.encode()).hexdigest(),'expected':expected_content_digest,'patch':digest(patches),'commit':hashlib.sha256(commit_message.encode()).hexdigest(),'flags':[installer_behavior_declared,service_behavior_declared,elevation_behavior_declared],'cleanup':cleanup_on_complete};op='winimpl_'+digest(spec)[:24];existing=_load(op,runtime_root)
 if existing:return {'ok':existing.get('implementation_state')=='completed','status':'windows_automation_already_exists','windows_automation':public_windows_automation(existing),'action_executed':False,**WINDOWS_AUTOMATION_DENIED_AUTHORITY}
 row={'contract_version':CONTRACT_VERSION,'windows_automation_id':op,'source_workspace_digest':source_workspace_digest,'implementation_state':'starting','failure_stage':'','workspace_id':'','file_operation_id':'','git_stage_operation_id':'','git_commit_operation_id':'','format':PurePosixPath(rel).suffix.lower(),'portable_validation_passed':False,'encoding_preserved':False,'native_windows_host':os.name=='nt','powershell_runtime_available':bool(shutil.which('pwsh') or shutil.which('powershell')),'native_windows_execution_validated':False,'workspace_cleaned':False,'host_recoverable':False,'action_executed':False,**WINDOWS_AUTOMATION_DENIED_AUTHORITY};_save(row,runtime_root);wid=''
 try:
  iso=create_disposable_workspace(source_root=source_root,source_workspace_digest=source_workspace_digest,active_grant=active_grant,precondition_record_id=pres['git'],mode='git_branch_worktree',retention_rule='retain_for_review',runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not iso.get('ok') or not iso.get('workspace_created'):raise RuntimeError('workspace_isolation')
  wid=str(iso['workspace_id']);row['workspace_id']=wid;row['action_executed']=True;_save(row,runtime_root)
  before=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
  if not before.get('ok'):raise RuntimeError('windows_script_read_before')
  bop=before.get('file_operation') or {};text=str(before.get('content') or '');facts_before=_script_facts(rel,text)
  if str(bop.get('before_digest') or '')!=expected_content_digest:raise RuntimeError('stale_windows_script_digest')
  patched=patch_candidate_file(wid,rel,expected_content_digest=expected_content_digest,patches=patches,active_grant=active_grant,precondition_record_id=pres['file_patch'],runtime_root=runtime_root,now_unix=now_unix)
  if not patched.get('ok'):raise RuntimeError(str(patched.get('status') or 'windows_script_patch_failed'))
  row['file_operation_id']=str((patched.get('file_operation') or {}).get('operation_id') or '');_save(row,runtime_root)
  after=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
  if not after.get('ok'):raise RuntimeError('windows_script_read_after')
  aop=after.get('file_operation') or {};facts_after=_script_facts(rel,str(after.get('content') or ''))
  row['encoding_preserved']=str(bop.get('encoding_code') or '')==str(aop.get('encoding_code') or '');_save(row,runtime_root)
  if not row['encoding_preserved']:raise RuntimeError('windows_script_encoding_regression')
  if not facts_after['syntax_valid']:raise RuntimeError('powershell_portable_syntax_invalid')
  if facts_after['installer_marker'] and not facts_before['installer_marker'] and not installer_behavior_declared:raise RuntimeError('undeclared_installer_behavior')
  if facts_after['service_mutation_marker'] and not facts_before['service_mutation_marker'] and not service_behavior_declared:raise RuntimeError('undeclared_service_behavior')
  if facts_after['elevation_marker'] and not facts_before['elevation_marker'] and not elevation_behavior_declared:raise RuntimeError('undeclared_elevation_behavior')
  if facts_after['destructive_system_marker'] and not facts_before['destructive_system_marker']:raise RuntimeError('destructive_windows_system_behavior_rejected')
  row['portable_validation_passed']=True;row['validation_digest']=facts_after['fact_digest'];_save(row,runtime_root)
  st=stage_owned_changes(wid,owned_file_operation_ids=[row['file_operation_id']],active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not st.get('ok'):raise RuntimeError('windows_automation_git_stage')
  row['git_stage_operation_id']=str((st.get('git_operation') or {}).get('operation_id') or '');_save(row,runtime_root)
  cm=commit_owned_changes(wid,stage_operation_id=row['git_stage_operation_id'],commit_message=commit_message,active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not cm.get('ok'):raise RuntimeError('windows_automation_git_commit')
  row['git_commit_operation_id']=str((cm.get('git_operation') or {}).get('operation_id') or '');row['implementation_state']='verified_candidate';_save(row,runtime_root)
 except Exception as e:row['implementation_state']='failed';row['failure_stage']=str(e);_save(row,runtime_root)
 finally:
  if wid and cleanup_on_complete:
   try:row['workspace_cleaned']=cleanup_disposable_workspace(wid,active_grant=active_grant,discard_owned_changes=True,runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable).get('cleaned') is True
   except Exception:row['workspace_cleaned']=False
  row['host_recoverable']=bool(not cleanup_on_complete or row['workspace_cleaned'])
  if row['implementation_state']=='verified_candidate' and row['host_recoverable']:row['implementation_state']='completed'
  _save(row,runtime_root)
 ok=row['implementation_state']=='completed';return {'ok':ok,'status':'windows_automation_completed' if ok else 'windows_automation_failed','windows_automation':public_windows_automation(row),'action_executed':row['action_executed'] is True,**WINDOWS_AUTOMATION_DENIED_AUTHORITY}

def public_windows_automation(row:Mapping[str,Any])->dict[str,Any]:
 if not row:return {}
 return {'contract_version':CONTRACT_VERSION,'windows_automation_id':row.get('windows_automation_id'),'source_workspace_digest':row.get('source_workspace_digest'),'implementation_state':row.get('implementation_state'),'failure_stage':row.get('failure_stage') or '','workspace_id':row.get('workspace_id') or '','file_operation_id':row.get('file_operation_id') or '','git_stage_operation_id':row.get('git_stage_operation_id') or '','git_commit_operation_id':row.get('git_commit_operation_id') or '','format':row.get('format') or '','portable_validation_passed':row.get('portable_validation_passed') is True,'encoding_preserved':row.get('encoding_preserved') is True,'native_windows_host':row.get('native_windows_host') is True,'powershell_runtime_available':row.get('powershell_runtime_available') is True,'native_windows_execution_validated':False,'workspace_cleaned':row.get('workspace_cleaned') is True,'host_recoverable':row.get('host_recoverable') is True,'candidate_only':True,'selected_source_content_modified':False,'raw_script_exposed':False,'action_executed':row.get('action_executed') is True,**WINDOWS_AUTOMATION_DENIED_AUTHORITY}
def load_windows_automation(op:str,*,runtime_root=None):row=_load(op,runtime_root);return public_windows_automation(row) if row else {}
def process_windows_automation_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show windows automation','inspect windows automation','show windows automation checkpoint'}:return {'active':False}
 op=str((project_state or {}).get('windows_automation_id') or '');row=load_windows_automation(op,runtime_root=runtime_root) if op else {};return {'active':True,'ok':bool(row),'status':'windows_automation_found' if row else 'windows_automation_missing','windows_automation':row,'action_executed':False,**WINDOWS_AUTOMATION_DENIED_AUTHORITY}
__all__=['CONTRACT_VERSION','REQUIRED_PRECONDITIONS','WINDOWS_AUTOMATION_DENIED_AUTHORITY','quote_powershell_literal','windows_command_line','normalize_windows_path','windows_path_within','build_windows_service_argv','build_windows_process_tree_stop_argv','classify_installer_argv','inspect_windows_automation_project','run_windows_automation_implementation','public_windows_automation','load_windows_automation','process_windows_automation_control']
