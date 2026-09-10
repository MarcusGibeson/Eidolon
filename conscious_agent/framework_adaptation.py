from __future__ import annotations
"""v1347 repository-convention adaptation layered over verified language execution."""
import ast, hashlib, re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
from ordinary_chat_development_campaign import _atomic_json,_read_json,_store_root
from python_implementation import run_python_implementation

CONTRACT_VERSION='v1347.8';MAX_FILES=4096;MAX_BYTES=2*1024*1024
FRAMEWORK_DENIED_AUTHORITY={**DENIED_AUTHORITY,'source_mutation_authorized':False,'source_application_authorized':False,'dependency_installation_authorized':False,'architecture_rewrite_authorized':False,'network_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
KNOWN_FRAMEWORKS={'flask','django','fastapi','starlette','quart','aiohttp','tornado','pyramid','bottle'}
def _root(runtime_root=None):return _store_root(runtime_root)/'phase5_framework_adaptation'
def _path(op,runtime_root=None):
 if not re.fullmatch(r'fwadapt_[a-f0-9]{24}',str(op or '')):raise ValueError('invalid_framework_adaptation_id')
 return _root(runtime_root)/'records'/f'{op}.json'
def _load(op,runtime_root=None):
 row=_read_json(_path(op,runtime_root));return row if row and row.get('record_digest')==digest({k:v for k,v in row.items() if k!='record_digest'}) else {}
def _save(row,runtime_root=None):row.pop('record_digest',None);row['record_digest']=digest(row);_atomic_json(_path(row['framework_adaptation_id'],runtime_root),row);return row

def _safe_rel(value:str)->str:
 s=str(value or '').replace('\\','/').strip();p=PurePosixPath(s)
 if not s or p.is_absolute() or any(x in {'','.','..'} for x in p.parts):raise ValueError('unsafe_framework_relative_path')
 if p.suffix!='.py':raise ValueError('python_source_file_required')
 if any(x.casefold() in {'.git','data','runtime','private','secrets','credentials','node_modules','.venv','venv','__pycache__'} for x in p.parts):raise ValueError('protected_framework_path')
 return p.as_posix()
def _module_import_facts(text:str)->dict[str,Any]:
 try:tree=ast.parse(text)
 except SyntaxError:return {'syntax_valid':False,'relative_import_count':0,'absolute_import_count':0,'frameworks':[],'top_level_import_digest':''}
 relative=absolute=0;frameworks=set();imports=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):
   for a in n.names:
    top=a.name.split('.')[0];absolute+=1;imports.append(('import',top));frameworks|={top} & KNOWN_FRAMEWORKS
  elif isinstance(n,ast.ImportFrom):
   mod=(n.module or '').split('.')[0];relative+=int(n.level>0);absolute+=int(n.level==0);imports.append(('from_rel' if n.level else 'from_abs',mod));frameworks|={mod} & KNOWN_FRAMEWORKS
 return {'syntax_valid':True,'relative_import_count':relative,'absolute_import_count':absolute,'frameworks':sorted(frameworks),'top_level_import_digest':digest(sorted(imports))}
def inspect_framework_conventions(source_root:str|Path)->dict[str,Any]:
 root=Path(source_root).resolve(strict=True);py=[];tests=0;relative=absolute=0;frameworks=set();src_layout=(root/'src').is_dir();package_init=0
 for p in sorted(root.rglob('*.py')):
  rel=p.relative_to(root)
  if any(x in {'.git','data','runtime','private','node_modules','.venv','venv','__pycache__'} for x in rel.parts) or p.stat().st_size>MAX_BYTES:continue
  if len(py)>=MAX_FILES:break
  py.append(p);tests+=int(p.name.startswith('test_') or p.name.endswith('_test.py') or 'tests' in rel.parts);package_init+=int(p.name=='__init__.py')
  try:f=_module_import_facts(p.read_text(encoding='utf-8'))
  except (OSError,UnicodeDecodeError):continue
  relative+=int(f['relative_import_count']);absolute+=int(f['absolute_import_count']);frameworks.update(f['frameworks'])
 metadata=[]
 for name in ('pyproject.toml','setup.cfg','requirements.txt','package.json'):
  if (root/name).is_file():metadata.append(name)
 style='mixed' if relative and absolute else ('relative' if relative else 'absolute' if absolute else 'none')
 layout='src' if src_layout else ('package' if package_init else 'flat')
 out={'contract_version':CONTRACT_VERSION,'layout_style':layout,'import_style':style,'python_file_count':len(py),'test_file_count':tests,'frameworks':sorted(frameworks),'metadata_files':metadata,'source_manifest_digest':digest([(p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in py]),'inspection_only':True,'convention_inferred':True,'network_contacted':False,**FRAMEWORK_DENIED_AUTHORITY};out['convention_digest']=digest(out);return out

def _apply_patches(text:str,patches:Sequence[Mapping[str,Any]])->str:
 out=text
 for patch in patches:
  if patch.get('type')!='replace_text':raise ValueError('unsupported_framework_patch_type')
  old=str(patch.get('old') or '');new=str(patch.get('new') or '');expected=int(patch.get('expected_occurrences',1))
  if not old or out.count(old)!=expected:raise ValueError('framework_patch_precondition_failed')
  out=out.replace(old,new)
 return out
def evaluate_framework_change(*,source_root:str|Path,relative_path:str,patches:Sequence[Mapping[str,Any]],architecture_change_declared:bool=False)->dict[str,Any]:
 try:rel=_safe_rel(relative_path);root=Path(source_root).resolve(strict=True);before_text=(root/rel).read_text(encoding='utf-8');after_text=_apply_patches(before_text,patches)
 except (ValueError,OSError,UnicodeDecodeError) as e:return {'ok':False,'status':str(e),'compatible':False,'inspection_only':True,**FRAMEWORK_DENIED_AUTHORITY}
 project=inspect_framework_conventions(root);before=_module_import_facts(before_text);after=_module_import_facts(after_text);reasons=[]
 if not after['syntax_valid']:reasons.append('python_syntax_invalid')
 new_frameworks=sorted(set(after['frameworks'])-set(project['frameworks']))
 if new_frameworks and not architecture_change_declared:reasons.append('undeclared_framework_introduction')
 if before['relative_import_count']>after['relative_import_count'] and after['absolute_import_count']>before['absolute_import_count'] and not architecture_change_declared:reasons.append('undeclared_import_style_drift')
 if before['absolute_import_count']>after['absolute_import_count'] and after['relative_import_count']>before['relative_import_count'] and not architecture_change_declared:reasons.append('undeclared_import_style_drift')
 out={'ok':not reasons,'status':'framework_change_compatible' if not reasons else reasons[0],'compatible':not reasons,'reasons':reasons,'layout_style':project['layout_style'],'import_style':project['import_style'],'new_framework_count':len(new_frameworks),'architecture_change_declared':bool(architecture_change_declared),'before_facts_digest':digest(before),'after_facts_digest':digest(after),'project_convention_digest':project['convention_digest'],'inspection_only':True,**FRAMEWORK_DENIED_AUTHORITY};out['evaluation_digest']=digest(out);return out

def run_framework_adaptation(*,source_root:str|Path,source_workspace_digest:str,active_grant:Mapping[str,Any],precondition_record_ids:Mapping[str,str],relative_path:str,expected_content_digest:str,patches:Sequence[Mapping[str,Any]],test_argv:Sequence[str],commit_message:str='Follow project conventions',architecture_change_declared:bool=False,runtime_root=None,now_unix:int|None=None,git_executable:str|None=None,python_executable:str|None=None,cleanup_on_complete:bool=True)->dict[str,Any]:
 try:rel=_safe_rel(relative_path)
 except ValueError as e:return {'ok':False,'status':str(e),'action_executed':False,**FRAMEWORK_DENIED_AUTHORITY}
 spec={'contract':CONTRACT_VERSION,'source':source_workspace_digest,'grant':active_grant.get('grant_digest'),'pre':dict(precondition_record_ids),'path':hashlib.sha256(rel.encode()).hexdigest(),'expected':expected_content_digest,'patch':digest(patches),'tests':digest(list(test_argv)),'architecture_declared':bool(architecture_change_declared),'cleanup':cleanup_on_complete};op='fwadapt_'+digest(spec)[:24];existing=_load(op,runtime_root)
 if existing:return {'ok':existing.get('adaptation_state')=='completed','status':'framework_adaptation_already_exists','framework_adaptation':public_framework_adaptation(existing),'action_executed':False,**FRAMEWORK_DENIED_AUTHORITY}
 evaluation=evaluate_framework_change(source_root=source_root,relative_path=rel,patches=patches,architecture_change_declared=architecture_change_declared)
 row={'contract_version':CONTRACT_VERSION,'framework_adaptation_id':op,'source_workspace_digest':source_workspace_digest,'adaptation_state':'blocked' if not evaluation.get('ok') else 'starting','failure_stage':'' if evaluation.get('ok') else str(evaluation.get('status')),'evaluation_digest':evaluation.get('evaluation_digest',''),'project_convention_digest':evaluation.get('project_convention_digest',''),'layout_style':evaluation.get('layout_style',''),'import_style':evaluation.get('import_style',''),'architecture_change_declared':bool(architecture_change_declared),'nested_python_implementation_id':'','nested_python_state':'','tests_passed':False,'workspace_cleaned':False,'host_recoverable':False,'action_executed':False,**FRAMEWORK_DENIED_AUTHORITY};_save(row,runtime_root)
 if not evaluation.get('ok'):return {'ok':False,'status':'framework_adaptation_blocked','framework_adaptation':public_framework_adaptation(row),'action_executed':False,**FRAMEWORK_DENIED_AUTHORITY}
 nested=run_python_implementation(source_root=source_root,source_workspace_digest=source_workspace_digest,active_grant=active_grant,precondition_record_ids=precondition_record_ids,relative_path=rel,expected_content_digest=expected_content_digest,patches=patches,test_argv=test_argv,commit_message=commit_message,allow_public_api_change=architecture_change_declared,package_boundary_change_declared=architecture_change_declared,runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable,python_executable=python_executable,cleanup_on_complete=cleanup_on_complete)
 n=dict(nested.get('python_implementation') or {});row['nested_python_implementation_id']=str(n.get('python_implementation_id') or '');row['nested_python_state']=str(n.get('implementation_state') or '');row['tests_passed']=n.get('tests_passed') is True;row['workspace_cleaned']=n.get('workspace_cleaned') is True;row['host_recoverable']=n.get('host_recoverable') is True;row['action_executed']=nested.get('action_executed') is True
 if nested.get('ok') and row['tests_passed'] and row['host_recoverable']:row['adaptation_state']='completed';row['failure_stage']=''
 else:row['adaptation_state']='failed';row['failure_stage']=str(n.get('failure_stage') or nested.get('status') or 'nested_python_implementation_failed')
 _save(row,runtime_root);ok=row['adaptation_state']=='completed';return {'ok':ok,'status':'framework_adaptation_completed' if ok else 'framework_adaptation_failed','framework_adaptation':public_framework_adaptation(row),'action_executed':row['action_executed'],**FRAMEWORK_DENIED_AUTHORITY}
def public_framework_adaptation(row:Mapping[str,Any])->dict[str,Any]:
 if not row:return {}
 return {k:row.get(k) for k in ('contract_version','framework_adaptation_id','source_workspace_digest','adaptation_state','failure_stage','evaluation_digest','project_convention_digest','layout_style','import_style','architecture_change_declared','nested_python_implementation_id','nested_python_state','tests_passed','workspace_cleaned','host_recoverable','action_executed')}|{'raw_source_exposed':False,'raw_test_command_exposed':False,'selected_source_content_modified':False,'candidate_only':True,**FRAMEWORK_DENIED_AUTHORITY}
def load_framework_adaptation(op:str,*,runtime_root=None):return public_framework_adaptation(_load(op,runtime_root))
def process_framework_adaptation_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show framework adaptation','inspect framework adaptation','show framework conventions'}:return {'active':False}
 op=str((project_state or {}).get('framework_adaptation_id') or '');row=load_framework_adaptation(op,runtime_root=runtime_root) if op else {};return {'active':True,'ok':bool(row),'status':'framework_adaptation_found' if row else 'framework_adaptation_missing','framework_adaptation':row,'action_executed':False,**FRAMEWORK_DENIED_AUTHORITY}
