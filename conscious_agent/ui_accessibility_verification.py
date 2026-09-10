from __future__ import annotations
"""v1356 structural + real-browser UI/accessibility verification."""
import hashlib,re
from html.parser import HTMLParser
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Sequence
from browser_validation import validate_browser_candidate
from cognitive_coding_foundations import digest
from ordinary_chat_development_campaign import _read_json
from workspace_isolation import _record_path as _workspace_record_path

CONTRACT_VERSION='v1356.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False}
class _Audit(HTMLParser):
 def __init__(self):super().__init__();self.labels=0;self.controls=[];self.label_for=set();self.landmarks=0;self.viewport=False;self.lang=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);tag=tag.lower()
  if tag=='html' and a.get('lang'):self.lang=True
  if tag=='meta' and str(a.get('name','')).lower()=='viewport':self.viewport=True
  if tag=='label':
   self.labels+=1
   if a.get('for'):self.label_for.add(a['for'])
  if tag in {'input','select','textarea','button'}:
   self.controls.append({'tag':tag,'id':a.get('id',''),'aria':bool(a.get('aria-label') or a.get('aria-labelledby')),'button_named':tag=='button'})
  if tag in {'main','nav','header','footer','aside'} or a.get('role') in {'main','navigation','banner','contentinfo','complementary'}:self.landmarks+=1

def _candidate_path(workspace_id:str,relative:str,runtime_root=None)->Path:
 try:ws=_read_json(_workspace_record_path(workspace_id,runtime_root))
 except Exception:raise ValueError('accessibility_workspace_required')
 root=Path(str(ws.get('candidate_private_path') or '')).resolve();p=PurePosixPath(str(relative or '').replace('\\','/'))
 if p.is_absolute() or not p.parts or any(x in {'','..'} for x in p.parts):raise ValueError('unsafe_accessibility_artifact_path')
 out=(root/Path(*p.parts)).resolve()
 if root not in out.parents or not out.is_file():raise ValueError('accessibility_artifact_missing')
 return out

def analyze_accessibility_structure(html_text:str,css_text:str='')->dict[str,Any]:
 a=_Audit();a.feed(html_text)
 unlabeled=0
 for c in a.controls:
  if c['tag']=='button':continue
  if not c['aria'] and (not c['id'] or c['id'] not in a.label_for):unlabeled+=1
 text=(html_text+'\n'+css_text).lower()
 checks={
  'document_language_present':a.lang,
  'viewport_declared':a.viewport,
  'landmark_present':a.landmarks>0,
  'controls_labeled':unlabeled==0,
  'focus_visible_signal':(':focus-visible' in text or ':focus{' in text or ':focus {' in text),
  'reduced_motion_signal':('prefers-reduced-motion' in text),
  'narrow_layout_signal':('@media' in text or 'max-width' in text or 'min(' in text or 'clamp(' in text),
  'scroll_structure_signal':('overflow' in text or 'scroll' in text),
 }
 return {'ok':all(checks.values()),'checks':checks,'control_count':len(a.controls),'unlabeled_control_count':unlabeled,'landmark_count':a.landmarks,'structural_evidence_only':True,'screen_reader_runtime_validated':False,'content_digest':hashlib.sha256((html_text+'\n'+css_text).encode()).hexdigest()}

def run_ui_accessibility_verification(workspace_id:str,*,html_relative_path:str,active_grant:Mapping[str,Any],browser_precondition_record_id:str,css_relative_path:str|None=None,browser_executable:str|None=None,runtime_root=None,now_unix:int|None=None,interactions:Sequence[Mapping[str,Any]]=(),checks:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
 try:
  hp=_candidate_path(workspace_id,html_relative_path,runtime_root);html=hp.read_text(encoding='utf-8-sig')
  css=''
  if css_relative_path:css=_candidate_path(workspace_id,css_relative_path,runtime_root).read_text(encoding='utf-8-sig')
 except (OSError,UnicodeError,ValueError) as exc:return {'ok':False,'status':str(exc),'action_executed':False,**DENIED}
 structural=analyze_accessibility_structure(html,css)
 if not structural['ok']:
  return {'ok':False,'status':'accessibility_structure_blocked','structural':structural,'browser_validation_performed':False,'action_executed':False,**DENIED}
 browser=validate_browser_candidate(workspace_id,target={'kind':'offline_document','html_relative_path':html_relative_path},active_grant=active_grant,precondition_record_id=browser_precondition_record_id,interactions=interactions,checks=checks,browser_executable=browser_executable,runtime_root=runtime_root,now_unix=now_unix)
 b=browser.get('browser_validation') or browser
 passed=browser.get('ok') is True and b.get('page_rendered') is True and int(b.get('checks_failed') or 0)==0
 rec={'contract_version':CONTRACT_VERSION,'workspace_id':workspace_id,'html_digest':hashlib.sha256(html.encode()).hexdigest(),'css_digest':hashlib.sha256(css.encode()).hexdigest() if css else '', 'structural_checks':structural['checks'],'structural_passed':structural['ok'],'browser_validation_id':b.get('browser_validation_id'),'real_browser_evidence':b.get('browser_launched') is True,'keyboard_and_input_checks_requested':len(interactions)>0,'browser_checks_passed':int(b.get('checks_passed') or 0),'browser_checks_failed':int(b.get('checks_failed') or 0),'screenshot_captured':b.get('screenshot_captured') is True,'screen_reader_runtime_validated':False,'screen_reader_structure_evidence':structural['checks']['controls_labeled'] and structural['checks']['landmark_present'],'verification_passed':passed,'content_free':True,'action_executed':b.get('browser_launched') is True,**DENIED};rec['record_digest']=digest(rec)
 return {'ok':passed,'status':'ui_accessibility_verification_passed' if passed else 'ui_accessibility_browser_failed','ui_accessibility_verification':rec,'action_executed':rec['action_executed'],**DENIED}

def process_ui_accessibility_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show ui accessibility verification','inspect ui accessibility verification','show accessibility tests'}:return {'active':False}
 rec=dict((project_state or {}).get('ui_accessibility_verification') or {})
 return {'active':True,'ok':bool(rec),'status':'ui_accessibility_verification_found' if rec else 'ui_accessibility_verification_missing','ui_accessibility_verification':rec,'action_executed':False,**DENIED}
