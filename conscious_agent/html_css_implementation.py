from __future__ import annotations
"""v1343 accessible responsive HTML/CSS implementation over Phase 4 isolation."""
import hashlib,re
from html.parser import HTMLParser
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
from ordinary_chat_development_campaign import _atomic_json,_read_json,_store_root
from workspace_isolation import create_disposable_workspace,cleanup_disposable_workspace
from structured_file_operations import read_candidate_file,patch_candidate_file,update_generated_file
from typed_git_operations import stage_owned_changes,commit_owned_changes
from browser_validation import validate_browser_candidate

CONTRACT_VERSION='v1343.8';SUFFIXES=('.html','.htm','.css');MAX_CHANGES=8;MAX_ANALYSIS_BYTES=2*1024*1024;REQUIRED_PRECONDITIONS=('git','file_read','file_patch','browser')
HTML_CSS_DENIED_AUTHORITY={**DENIED_AUTHORITY,'network_authorized':False,'source_mutation_authorized':False,'source_application_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}

def _root(runtime_root=None):return _store_root(runtime_root)/'phase5_html_css_implementation'
def _path(op_id,runtime_root=None):
 if not re.fullmatch(r'uiimpl_[a-f0-9]{24}',str(op_id or '')):raise ValueError('invalid_html_css_implementation_id')
 return _root(runtime_root)/'records'/f'{op_id}.json'
def _load(op_id,runtime_root=None):
 row=_read_json(_path(op_id,runtime_root));return row if row and row.get('record_digest')==digest({k:v for k,v in row.items() if k!='record_digest'}) else {}
def _save(row,runtime_root=None):row.pop('record_digest',None);row['record_digest']=digest(row);_atomic_json(_path(row['implementation_id'],runtime_root),row);return row

def _safe_rel(value:str)->str:
 text=str(value or '').replace('\\','/').strip();p=PurePosixPath(text)
 if not text or p.is_absolute() or any(x in {'','.','..'} for x in p.parts):raise ValueError('unsafe_html_css_relative_path')
 if p.suffix.lower() not in SUFFIXES:raise ValueError('html_css_source_required')
 if any(x.casefold() in {'.git','data','runtime','private','secrets','credentials','node_modules','.venv','venv','__pycache__'} for x in p.parts):raise ValueError('protected_html_css_path')
 return p.as_posix()

class _A11y(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.viewport=False;self.images=0;self.missing_alt=0;self.form_ids=set();self.label_for=set();self.label_depth=0;self.wrapped_controls=0;self.keyboard_issues=0;self.interactive=0
 def handle_starttag(self,tag,attrs):
  a={str(k).lower():str(v or '') for k,v in attrs};tag=tag.lower()
  if tag=='meta' and a.get('name','').lower()=='viewport':self.viewport=True
  if tag=='img':self.images+=1;self.missing_alt+=int('alt' not in a)
  if tag=='label':self.label_depth+=1;self.label_for.add(a.get('for','')) if a.get('for') else None
  if tag in {'input','select','textarea'}:
   self.interactive+=1
   if a.get('id'):self.form_ids.add(a['id'])
   if self.label_depth:self.wrapped_controls+=1
  if tag in {'button','a'} or (tag=='input' and a.get('type','').lower() in {'button','submit','checkbox','radio'}):self.interactive+=1
  if any(k in a for k in ('onclick','onkeydown','onkeypress','onkeyup')) and tag not in {'button','a','input','select','textarea'}:
   if a.get('tabindex') not in {'0','1'} and not a.get('role'):self.keyboard_issues+=1
 def handle_endtag(self,tag):
  if tag.lower()=='label' and self.label_depth:self.label_depth-=1

def _html_facts(text:str)->dict[str,Any]:
 if len(text.encode())>MAX_ANALYSIS_BYTES:raise ValueError('html_analysis_budget_exceeded')
 p=_A11y();p.feed(text);unlabelled=max(0,len(p.form_ids-p.label_for)-p.wrapped_controls);issues=p.missing_alt+unlabelled+p.keyboard_issues+int(not p.viewport)
 return {'content_digest':hashlib.sha256(text.encode()).hexdigest(),'accessibility_issue_count':issues,'missing_alt_count':p.missing_alt,'unlabelled_control_count':unlabelled,'keyboard_issue_count':p.keyboard_issues,'viewport_meta_present':p.viewport,'interactive_control_count':p.interactive,'inline_style_count':len(re.findall(r'<style\b',text,flags=re.I)),'inline_script_count':len(re.findall(r'<script\b',text,flags=re.I))}
def _css_facts(text:str)->dict[str,Any]:
 if len(text.encode())>MAX_ANALYSIS_BYTES:raise ValueError('css_analysis_budget_exceeded')
 responsive=sum(len(re.findall(p,text,flags=re.I)) for p in (r'@media\b',r'\bmax-width\s*:',r'\bmin-width\s*:',r'\bclamp\s*\(',r'\b\d+(?:\.\d+)?(?:%|vw|vh|rem)\b'))
 fixed=len(re.findall(r'\b(?:width|min-width|max-width)\s*:\s*\d+(?:\.\d+)?px\b',text,flags=re.I))
 focus=len(re.findall(r':focus(?:-visible)?\b',text,flags=re.I));reduced=len(re.findall(r'prefers-reduced-motion',text,flags=re.I))
 return {'content_digest':hashlib.sha256(text.encode()).hexdigest(),'responsive_signal_count':responsive,'fixed_pixel_width_count':fixed,'focus_style_count':focus,'reduced_motion_count':reduced}
def _facts(path:str,text:str):return _css_facts(text) if PurePosixPath(path).suffix.lower()=='.css' else _html_facts(text)

def inspect_html_css_project(source_root:str|Path)->dict[str,Any]:
 root=Path(source_root).resolve(strict=True);html=css=issues=responsive=fixed=focus=reduced=0;files=[]
 for p in sorted(root.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(root)
  if any(x in {'.git','data','runtime','private','node_modules','__pycache__'} for x in rel.parts) or p.suffix.lower() not in SUFFIXES or p.stat().st_size>MAX_ANALYSIS_BYTES:continue
  try:f=_facts(rel.as_posix(),p.read_text(encoding='utf-8'))
  except (OSError,UnicodeDecodeError,ValueError):continue
  files.append(p)
  if p.suffix.lower()=='.css':css+=1;responsive+=f['responsive_signal_count'];fixed+=f['fixed_pixel_width_count'];focus+=f['focus_style_count'];reduced+=f['reduced_motion_count']
  else:html+=1;issues+=f['accessibility_issue_count']
 out={'contract_version':CONTRACT_VERSION,'html_file_count':html,'css_file_count':css,'accessibility_issue_count':issues,'responsive_signal_count':responsive,'fixed_pixel_width_count':fixed,'focus_style_count':focus,'reduced_motion_count':reduced,'source_manifest_digest':digest([(p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),'inspection_only':True,'browser_launched':False,'network_contacted':False,**HTML_CSS_DENIED_AUTHORITY};out['inspection_digest']=digest(out);return out

def _compat(path,before,after,*,allow_accessibility_regression,allow_responsive_regression,allow_fixed_layout_increase):
 reasons=[]
 if path.endswith(('.html','.htm')):
  if after['accessibility_issue_count']>before['accessibility_issue_count'] and not allow_accessibility_regression:reasons.append('accessibility_regression')
 else:
  responsive_lost=after['responsive_signal_count']<before['responsive_signal_count']
  responsive_removed=before['responsive_signal_count']>0 and after['responsive_signal_count']==0
  rigid_increased=after['fixed_pixel_width_count']>before['fixed_pixel_width_count']
  # Complete responsive-contract loss is the strongest signal.  Otherwise, a
  # newly introduced rigid width is more diagnostic than the responsive tokens
  # it displaced; partial responsive loss without new rigidity remains its own
  # regression class.
  if responsive_removed and not allow_responsive_regression:reasons.append('responsive_contract_regression')
  elif rigid_increased and not allow_fixed_layout_increase:reasons.append('rigid_layout_regression')
  elif responsive_lost and not allow_responsive_regression:reasons.append('responsive_contract_regression')
 return {'compatible':not reasons,'reasons':reasons,'accessibility_issue_delta':int(after.get('accessibility_issue_count') or 0)-int(before.get('accessibility_issue_count') or 0),'responsive_signal_delta':int(after.get('responsive_signal_count') or 0)-int(before.get('responsive_signal_count') or 0),'fixed_pixel_width_delta':int(after.get('fixed_pixel_width_count') or 0)-int(before.get('fixed_pixel_width_count') or 0)}

def run_html_css_implementation(*,source_root:str|Path,source_workspace_digest:str,active_grant:Mapping[str,Any],precondition_record_ids:Mapping[str,str],changes:Sequence[Mapping[str,Any]],preview_html_relative_path:str,preview_css_relative_paths:Sequence[str]=(),browser_interactions:Sequence[Mapping[str,Any]]=(),browser_checks:Sequence[Mapping[str,Any]]=(),expected_screenshot_digest:str='',commit_message:str='Update accessible responsive interface',allow_accessibility_regression:bool=False,allow_responsive_regression:bool=False,allow_fixed_layout_increase:bool=False,runtime_root=None,now_unix:int|None=None,git_executable:str|None=None,browser_executable:str|None=None,cleanup_on_complete:bool=True)->dict[str,Any]:
 pres={str(k):str(v) for k,v in precondition_record_ids.items()}
 if any(not pres.get(k) for k in REQUIRED_PRECONDITIONS):return {'ok':False,'status':'complete_html_css_preconditions_required','action_executed':False,**HTML_CSS_DENIED_AUTHORITY}
 if not changes or len(changes)>MAX_CHANGES:return {'ok':False,'status':'html_css_change_count_invalid','action_executed':False,**HTML_CSS_DENIED_AUTHORITY}
 try:
  normalized=[{'relative_path':_safe_rel(c.get('relative_path','')),'expected_content_digest':str(c.get('expected_content_digest') or ''),'patches':list(c.get('patches') or [])} for c in changes];preview=_safe_rel(preview_html_relative_path);css_paths=[_safe_rel(x) for x in preview_css_relative_paths]
  if not preview.endswith(('.html','.htm')) or any(not x.endswith('.css') for x in css_paths):raise ValueError('preview_html_css_contract_invalid')
 except ValueError as e:return {'ok':False,'status':str(e),'action_executed':False,**HTML_CSS_DENIED_AUTHORITY}
 spec={'contract':CONTRACT_VERSION,'source':source_workspace_digest,'grant':active_grant.get('grant_digest'),'preconditions':pres,'changes':digest(normalized),'preview':hashlib.sha256(preview.encode()).hexdigest(),'css':digest(css_paths),'interactions':digest(browser_interactions),'checks':digest(browser_checks),'expected_screenshot':expected_screenshot_digest,'flags':[allow_accessibility_regression,allow_responsive_regression,allow_fixed_layout_increase],'commit':hashlib.sha256(commit_message.encode()).hexdigest(),'cleanup':cleanup_on_complete};op='uiimpl_'+digest(spec)[:24];existing=_load(op,runtime_root)
 if existing:return {'ok':existing.get('implementation_state')=='completed','status':'html_css_implementation_already_exists','html_css_implementation':public_html_css_implementation(existing),'action_executed':False,**HTML_CSS_DENIED_AUTHORITY}
 row={'contract_version':CONTRACT_VERSION,'implementation_id':op,'source_workspace_digest':source_workspace_digest,'implementation_state':'starting','failure_stage':'','workspace_id':'','file_operation_ids':[],'preview_operation_id':'','browser_validation_id':'','git_stage_operation_id':'','git_commit_operation_id':'','change_count':len(normalized),'compatibility_passed':False,'browser_passed':False,'screenshot_captured':False,'screenshot_digest':'','visual_baseline_checked':bool(expected_screenshot_digest),'visual_baseline_matched':False,'workspace_cleaned':False,'host_recoverable':False,'action_executed':False,**HTML_CSS_DENIED_AUTHORITY};_save(row,runtime_root)
 wid=''
 try:
  iso=create_disposable_workspace(source_root=source_root,source_workspace_digest=source_workspace_digest,active_grant=active_grant,precondition_record_id=pres['git'],mode='git_branch_worktree',retention_rule='retain_for_review',runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not iso.get('ok') or not iso.get('workspace_created'):raise RuntimeError('workspace_isolation')
  wid=str(iso['workspace_id']);row['workspace_id']=wid;row['action_executed']=True;_save(row,runtime_root);all_compat=[]
  for c in normalized:
   rel=c['relative_path'];b=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
   if not b.get('ok'):raise RuntimeError('html_css_read_before')
   before_text=str(b.get('content') or '');before=_facts(rel,before_text)
   if before['content_digest']!=c['expected_content_digest']:raise RuntimeError('stale_html_css_content_digest')
   patched=patch_candidate_file(wid,rel,expected_content_digest=c['expected_content_digest'],patches=c['patches'],active_grant=active_grant,precondition_record_id=pres['file_patch'],runtime_root=runtime_root,now_unix=now_unix)
   if not patched.get('ok'):raise RuntimeError(str(patched.get('status') or 'html_css_patch'))
   row['file_operation_ids'].append(str((patched.get('file_operation') or {}).get('operation_id') or ''));_save(row,runtime_root)
   a=read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
   if not a.get('ok'):raise RuntimeError('html_css_read_after')
   comp=_compat(rel,before,_facts(rel,str(a.get('content') or '')),allow_accessibility_regression=allow_accessibility_regression,allow_responsive_regression=allow_responsive_regression,allow_fixed_layout_increase=allow_fixed_layout_increase);all_compat.append(comp)
   if not comp['compatible']:raise RuntimeError(comp['reasons'][0])
  row['compatibility_passed']=True;row['compatibility_digest']=digest(all_compat);_save(row,runtime_root)
  h=read_candidate_file(wid,preview,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
  if not h.get('ok'):raise RuntimeError('preview_html_missing')
  html=str(h.get('content') or '');styles=[]
  for css in css_paths:
   c=read_candidate_file(wid,css,active_grant=active_grant,precondition_record_id=pres['file_read'],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
   if not c.get('ok'):raise RuntimeError('preview_css_missing')
   styles.append(str(c.get('content') or ''))
  merged=html.replace('</head>','<style>\n'+'\n'.join(styles)+'\n</style></head>',1) if '</head>' in html else '<style>\n'+'\n'.join(styles)+'\n</style>'+html
  preview_path='.eidolon-preview-v1343.html';gen=update_generated_file(wid,preview_path,merged,expected_absent=True,active_grant=active_grant,precondition_record_id=pres['file_patch'],runtime_root=runtime_root,now_unix=now_unix)
  if not gen.get('ok'):raise RuntimeError('preview_generation_failed')
  row['preview_operation_id']=str((gen.get('file_operation') or {}).get('operation_id') or '');_save(row,runtime_root)
  br=validate_browser_candidate(wid,target={'kind':'offline_document','html_relative_path':preview_path},active_grant=active_grant,precondition_record_id=pres['browser'],interactions=browser_interactions,checks=browser_checks,browser_executable=browser_executable,runtime_root=runtime_root,now_unix=now_unix);brow=br.get('browser_validation') or {};row['browser_validation_id']=str(brow.get('browser_validation_id') or '');row['browser_passed']=br.get('ok') is True;row['screenshot_captured']=brow.get('screenshot_captured') is True;row['screenshot_digest']=str(brow.get('screenshot_digest') or '');_save(row,runtime_root)
  if not row['browser_passed'] or not row['screenshot_captured']:raise RuntimeError('html_css_browser_validation_failed')
  if expected_screenshot_digest:
   row['visual_baseline_matched']=row['screenshot_digest']==expected_screenshot_digest;_save(row,runtime_root)
   if not row['visual_baseline_matched']:raise RuntimeError('visual_regression_detected')
  st=stage_owned_changes(wid,owned_file_operation_ids=row['file_operation_ids'],active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not st.get('ok'):raise RuntimeError('html_css_git_stage')
  row['git_stage_operation_id']=str((st.get('git_operation') or {}).get('operation_id') or '');_save(row,runtime_root);cm=commit_owned_changes(wid,stage_operation_id=row['git_stage_operation_id'],commit_message=commit_message,active_grant=active_grant,precondition_record_id=pres['git'],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
  if not cm.get('ok'):raise RuntimeError('html_css_git_commit')
  row['git_commit_operation_id']=str((cm.get('git_operation') or {}).get('operation_id') or '');row['implementation_state']='verified_candidate';_save(row,runtime_root)
 except Exception as e:row['implementation_state']='failed';row['failure_stage']=str(e);_save(row,runtime_root)
 finally:
  if wid and cleanup_on_complete:
   try:row['workspace_cleaned']=cleanup_disposable_workspace(wid,active_grant=active_grant,discard_owned_changes=True,runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable).get('cleaned') is True
   except Exception:row['workspace_cleaned']=False
  row['host_recoverable']=bool(not cleanup_on_complete or row['workspace_cleaned'])
  if row['implementation_state']=='verified_candidate' and row['host_recoverable']:row['implementation_state']='completed'
  _save(row,runtime_root)
 ok=row['implementation_state']=='completed';return {'ok':ok,'status':'html_css_implementation_completed' if ok else 'html_css_implementation_failed','html_css_implementation':public_html_css_implementation(row),'action_executed':row['action_executed'] is True,**HTML_CSS_DENIED_AUTHORITY}

def public_html_css_implementation(row:Mapping[str,Any])->dict[str,Any]:
 if not row:return {}
 return {'contract_version':CONTRACT_VERSION,'implementation_id':row.get('implementation_id'),'source_workspace_digest':row.get('source_workspace_digest'),'implementation_state':row.get('implementation_state'),'failure_stage':row.get('failure_stage') or '','workspace_id':row.get('workspace_id') or '','file_operation_ids':list(row.get('file_operation_ids') or []),'preview_operation_id':row.get('preview_operation_id') or '','browser_validation_id':row.get('browser_validation_id') or '','git_stage_operation_id':row.get('git_stage_operation_id') or '','git_commit_operation_id':row.get('git_commit_operation_id') or '','change_count':int(row.get('change_count') or 0),'compatibility_passed':row.get('compatibility_passed') is True,'browser_passed':row.get('browser_passed') is True,'screenshot_captured':row.get('screenshot_captured') is True,'screenshot_digest':row.get('screenshot_digest') or '','visual_baseline_checked':row.get('visual_baseline_checked') is True,'visual_baseline_matched':row.get('visual_baseline_matched') is True,'workspace_cleaned':row.get('workspace_cleaned') is True,'host_recoverable':row.get('host_recoverable') is True,'candidate_only':True,'selected_source_content_modified':False,'raw_html_css_exposed':False,'screenshot_path_exposed':False,'network_contacted':False,'action_executed':row.get('action_executed') is True,**HTML_CSS_DENIED_AUTHORITY}
def load_html_css_implementation(op_id:str,*,runtime_root=None):
 row=_load(op_id,runtime_root);return public_html_css_implementation(row) if row else {}
def process_html_css_implementation_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show html css implementation','show ui implementation checkpoint','inspect html css implementation'}:return {'active':False}
 op=str((project_state or {}).get('html_css_implementation_id') or '');row=load_html_css_implementation(op,runtime_root=runtime_root) if op else {};return {'active':True,'ok':bool(row),'status':'html_css_implementation_found' if row else 'html_css_implementation_missing','html_css_implementation':row,'action_executed':False,**HTML_CSS_DENIED_AUTHORITY}
__all__=['CONTRACT_VERSION','REQUIRED_PRECONDITIONS','HTML_CSS_DENIED_AUTHORITY','inspect_html_css_project','run_html_css_implementation','public_html_css_implementation','load_html_css_implementation','process_html_css_implementation_control']
