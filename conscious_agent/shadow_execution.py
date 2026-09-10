from __future__ import annotations
"""v1386 bounded baseline-versus-candidate shadow execution."""
import hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
from typing import Any,Mapping,Sequence
from self_change_isolation import verify_self_change_isolation
CONTRACT_VERSION='v1386.8';SCRIPT=re.compile(r'^(?:tools|shadow)/[A-Za-z0-9_.-]+\.py$')
DENIED={'live_authority_granted':False,'source_mutation_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _run(root:Path,rel:str,py:str,timeout:int)->dict[str,Any]:
 p=(root/rel).resolve()
 try:p.relative_to(root)
 except ValueError:return {'ok':False,'status':'path_escape'}
 if not p.is_file():return {'ok':False,'status':'script_missing'}
 st=time.monotonic()
 try:
  cp=subprocess.run([py,rel],cwd=root,capture_output=True,timeout=timeout,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  blob=(cp.stdout or b'')+(cp.stderr or b'');return {'ok':True,'exit_code':cp.returncode,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'output_truncated':len(blob)>1048576,'duration_ms':int((time.monotonic()-st)*1000)}
 except subprocess.TimeoutExpired as e:
  blob=(e.stdout or b'')+(e.stderr or b'');return {'ok':True,'exit_code':None,'timed_out':True,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'duration_ms':int((time.monotonic()-st)*1000)}
def run_shadow_execution(*,baseline_root:str|Path,private_workspace:Mapping[str,Any],expected_lineage_digest:str,scenario_paths:Sequence[str],python_executable:str|None=None,timeout_seconds:int=20)->dict[str,Any]:
 iso=verify_self_change_isolation(private_workspace=private_workspace,expected_lineage_digest=expected_lineage_digest)
 base=Path(baseline_root).expanduser().resolve();work=Path(str(private_workspace.get('work_root') or '')).resolve()
 if not iso.get('ok') or not base.is_dir():return {'ok':False,'status':'shadow_context_invalid','action_executed':False,**DENIED}
 if not scenario_paths or len(scenario_paths)>24 or not 1<=int(timeout_seconds)<=120:return {'ok':False,'status':'shadow_plan_invalid','action_executed':False,**DENIED}
 py=python_executable or sys.executable;rows=[]
 for raw in scenario_paths:
  rel=str(raw or '').replace('\\','/')
  if not SCRIPT.fullmatch(rel) or '..' in Path(rel).parts:return {'ok':False,'status':'shadow_scenario_invalid','action_executed':False,**DENIED}
  b=_run(base,rel,py,timeout_seconds);c=_run(work,rel,py,timeout_seconds)
  if not b.get('ok') or not c.get('ok'):return {'ok':False,'status':'shadow_scenario_missing','action_executed':False,**DENIED}
  parity=b.get('exit_code')==c.get('exit_code') and b.get('output_digest')==c.get('output_digest') and bool(b.get('timed_out'))==bool(c.get('timed_out'))
  regression=(b.get('exit_code')==0 and c.get('exit_code')!=0) or (not b.get('timed_out') and c.get('timed_out'))
  rows.append({'scenario_path':rel,'baseline':b,'candidate':c,'behavior_parity':parity,'regression_detected':regression})
 regressions=sum(bool(r['regression_detected']) for r in rows);changed=sum(not r['behavior_parity'] for r in rows)
 core={'contract_version':CONTRACT_VERSION,'candidate_id':iso['verification'].get('candidate_id'),'lineage_digest':expected_lineage_digest,'scenario_count':len(rows),'behavior_changed_count':changed,'regression_count':regressions,'scenarios':rows,'baseline_remained_live_authority':True,'candidate_had_live_authority':False,'shadow_only':True,'content_free':True,'action_executed':True,**DENIED};core['shadow_digest']=_d(core)
 return {'ok':regressions==0,'status':'shadow_execution_passed' if regressions==0 else 'shadow_execution_regression','shadow_execution':core,'action_executed':True,**DENIED}
def process_shadow_execution_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show shadow execution','inspect shadow execution','show shadow comparison'}:return {'active':False}
 rec=dict((project_state or {}).get('shadow_execution') or {});return {'active':True,'ok':bool(rec),'status':'shadow_execution_found' if rec else 'shadow_execution_missing','shadow_execution':rec,'action_executed':False,**DENIED}
