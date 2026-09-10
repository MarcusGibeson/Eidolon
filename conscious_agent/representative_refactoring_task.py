from __future__ import annotations
"""v1394 representative ownership-boundary refactoring task."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
from typing import Any
CONTRACT_VERSION='v1394.8'
DENIED={'eidolon_source_mutation_authorized':False,'release_authorized':False,'promotion_authorized':False,'independent_authority_granted':False}
POLICY_EXPR='" ".join(value.strip().split())'
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _tests(root:Path,timeout:int):
 st=time.monotonic();cp=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=root,capture_output=True,timeout=timeout,env={'PYTHONDONTWRITEBYTECODE':'1'});blob=(cp.stdout or b'')+(cp.stderr or b'');return {'passed':cp.returncode==0,'exit_code':cp.returncode,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'duration_ms':int((time.monotonic()-st)*1000)}
def _behavior(root:Path,timeout:int):
 code='import json; from src.profile_service import create_profile, update_profile, normalize_display_name; p=create_profile("  Ada   Lovelace "); q=update_profile(p," Grace   Hopper "); print(json.dumps([p,q,normalize_display_name(" A   B ")],sort_keys=True),end="")';cp=subprocess.run([sys.executable,'-c',code],cwd=root,capture_output=True,timeout=timeout,env={'PYTHONDONTWRITEBYTECODE':'1'});return {'exit_code':cp.returncode,'behavior_digest':hashlib.sha256(cp.stdout or b'').hexdigest(),'error_digest':hashlib.sha256(cp.stderr or b'').hexdigest()}
def run_refactoring_task(*,project_root:str|Path,request:str,operator_authorized:bool,timeout_seconds:int=30)->dict[str,Any]:
 root=Path(project_root).expanduser().resolve();active=Path(__file__).resolve().parents[1];text=' '.join(str(request or '').split())
 if not operator_authorized or not re.search(r'refactor|ownership|extract',text,re.I):return {'ok':False,'status':'refactor_not_authorized_or_unsupported','action_executed':False,**DENIED}
 try:root.relative_to(active);return {'ok':False,'status':'refactor_eidolon_source_blocked','action_executed':False,**DENIED}
 except ValueError:pass
 target=root/'src'/'profile_service.py';policy=root/'src'/'text_policy.py'
 if not target.is_file() or policy.exists():return {'ok':False,'status':'refactor_project_state_invalid','action_executed':False,**DENIED}
 original=target.read_text(encoding='utf-8');dupes=original.count(POLICY_EXPR)
 if dupes<3:return {'ok':False,'status':'refactor_ownership_smell_not_grounded','action_executed':False,**DENIED}
 baseline=_tests(root,timeout_seconds);before_behavior=_behavior(root,timeout_seconds)
 if not baseline['passed'] or before_behavior['exit_code']!=0:return {'ok':False,'status':'refactor_baseline_invalid','action_executed':False,**DENIED}
 # Compatibility is preserved because profile_service imports the extracted function into its existing module namespace.
 new_policy='''def normalize_display_name(value: str) -> str:\n    """Own display-name whitespace policy in one place."""\n    return " ".join(value.strip().split())\n'''
 modified=original
 # Remove the local function and replace duplicate expressions with the policy call.
 modified=re.sub(r'def normalize_display_name\(value: str\) -> str:\n\s+return " "\.join\(value\.strip\(\)\.split\(\)\)\n\n','from .text_policy import normalize_display_name\n\n',modified,count=1)
 modified=modified.replace(POLICY_EXPR,'normalize_display_name(value)')
 try:
  target.write_text(modified,encoding='utf-8');policy.write_text(new_policy,encoding='utf-8');after_behavior=_behavior(root,timeout_seconds);final=_tests(root,timeout_seconds)
  parity=after_behavior['exit_code']==0 and after_behavior['behavior_digest']==before_behavior['behavior_digest'];compat='from .text_policy import normalize_display_name' in modified
  if not parity or not compat or not final['passed']:raise RuntimeError('refactor verification failed')
 except Exception as e:
  target.write_text(original,encoding='utf-8');policy.unlink(missing_ok=True);return {'ok':False,'status':'refactor_failed_rolled_back','failure_digest':_d(type(e).__name__),'action_executed':True,**DENIED}
 after_dupes=target.read_text(encoding='utf-8').count(POLICY_EXPR);core={'contract_version':CONTRACT_VERSION,'request_digest':_d(text),'project_root_digest':_d(str(root)),'baseline_tests':baseline,'final_tests':final,'behavior_before':before_behavior,'behavior_after':after_behavior,'behavioral_parity':parity,'compatibility_import_preserved':compat,'ownership_module_created':'src/text_policy.py','service_duplicate_policy_count_before':dupes,'service_duplicate_policy_count_after':after_dupes,'duplicate_reduction':dupes-after_dupes,'maintenance_benefit_measured':dupes-after_dupes>=3,'migration_safe_api_surface':True,'rollback_boundary_retained':True,'action_executed':True,**DENIED};core['task_digest']=_d(core)
 return {'ok':True,'status':'refactoring_task_complete','refactoring_task':core,'action_executed':True,**DENIED}
def process_refactoring_task_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show refactoring task','inspect refactoring task','show gamma refactor'}:return {'active':False}
 rec=dict((project_state or {}).get('refactoring_task') or {});return {'active':True,'ok':bool(rec),'status':'refactoring_task_found' if rec else 'refactoring_task_missing','refactoring_task':rec,'action_executed':False,**DENIED}
