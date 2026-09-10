from __future__ import annotations
"""v1387 bounded canary execution for isolated self-update candidates."""
import hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
from typing import Any,Mapping,Sequence
from self_change_isolation import verify_self_change_isolation
CONTRACT_VERSION='v1387.8';SCRIPT=re.compile(r'^(?:tools|canary)/[A-Za-z0-9_.-]+\.py$')
DENIED={'source_replacement_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _sealed(record:Mapping[str,Any],digest_field:str,expected:str)->bool:
 row=dict(record or {});sup=str(row.pop(digest_field,''));return bool(expected and sup==expected and sup==_d(row))
def run_canary_self_update(*,private_workspace:Mapping[str,Any],expected_lineage_digest:str,dogfood_verification:Mapping[str,Any],expected_dogfood_digest:str,shadow_execution:Mapping[str,Any],expected_shadow_digest:str,health_scenarios:Sequence[str],python_executable:str|None=None,timeout_seconds:int=20)->dict[str,Any]:
 iso=verify_self_change_isolation(private_workspace=private_workspace,expected_lineage_digest=expected_lineage_digest)
 if not iso.get('ok'):return {'ok':False,'status':'canary_isolation_invalid','action_executed':False,**DENIED}
 if not _sealed(dogfood_verification,'verification_digest',expected_dogfood_digest) or dogfood_verification.get('failed') or not dogfood_verification.get('candidate_installable'):
  return {'ok':False,'status':'canary_dogfood_evidence_invalid','action_executed':False,**DENIED}
 if not _sealed(shadow_execution,'shadow_digest',expected_shadow_digest) or int(shadow_execution.get('regression_count') or 0)>0 or not shadow_execution.get('shadow_only'):
  return {'ok':False,'status':'canary_shadow_evidence_invalid','action_executed':False,**DENIED}
 if dogfood_verification.get('candidate_id')!=shadow_execution.get('candidate_id') or dogfood_verification.get('candidate_id')!=iso['verification'].get('candidate_id'):
  return {'ok':False,'status':'canary_candidate_lineage_mismatch','action_executed':False,**DENIED}
 if not health_scenarios or len(health_scenarios)>16 or not 1<=int(timeout_seconds)<=120:return {'ok':False,'status':'canary_plan_invalid','action_executed':False,**DENIED}
 root=Path(str(private_workspace.get('work_root') or '')).resolve();py=python_executable or sys.executable;rows=[]
 for raw in health_scenarios:
  rel=str(raw or '').replace('\\','/')
  if not SCRIPT.fullmatch(rel) or '..' in Path(rel).parts:return {'ok':False,'status':'canary_scenario_invalid','action_executed':False,**DENIED}
  p=(root/rel).resolve()
  try:p.relative_to(root)
  except ValueError:return {'ok':False,'status':'canary_path_escape','action_executed':False,**DENIED}
  if not p.is_file():return {'ok':False,'status':'canary_scenario_missing','action_executed':False,**DENIED}
  st=time.monotonic()
  try:
   cp=subprocess.run([py,rel],cwd=root,capture_output=True,timeout=timeout_seconds,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});blob=(cp.stdout or b'')+(cp.stderr or b'')
   rows.append({'scenario_path':rel,'passed':cp.returncode==0,'exit_code':cp.returncode,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'duration_ms':int((time.monotonic()-st)*1000)})
  except subprocess.TimeoutExpired as e:
   blob=(e.stdout or b'')+(e.stderr or b'');rows.append({'scenario_path':rel,'passed':False,'exit_code':None,'timed_out':True,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'duration_ms':int((time.monotonic()-st)*1000)})
 passed=sum(bool(x['passed']) for x in rows);core={'contract_version':CONTRACT_VERSION,'candidate_id':iso['verification'].get('candidate_id'),'lineage_digest':expected_lineage_digest,'dogfood_digest':expected_dogfood_digest,'shadow_digest':expected_shadow_digest,'scenario_count':len(rows),'passed':passed,'failed':len(rows)-passed,'scenarios':rows,'canary_passed':passed==len(rows),'eligible_for_install_review':passed==len(rows),'candidate_was_live_source':False,'content_free':True,'action_executed':True,**DENIED};core['canary_digest']=_d(core)
 return {'ok':passed==len(rows),'status':'canary_self_update_passed' if passed==len(rows) else 'canary_self_update_failed','canary_self_update':core,'action_executed':True,**DENIED}
def process_canary_self_update_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show canary self update','inspect canary self update','show self update canary'}:return {'active':False}
 rec=dict((project_state or {}).get('canary_self_update') or {});return {'active':True,'ok':bool(rec),'status':'canary_self_update_found' if rec else 'canary_self_update_missing','canary_self_update':rec,'action_executed':False,**DENIED}
