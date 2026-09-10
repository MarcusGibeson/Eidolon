from __future__ import annotations
"""v1388 operator-bounded self-update transaction with automatic rollback.

Transactions may target only an explicitly external installed-source fixture/tree,
never the source tree executing this module. A failed post-install health check
restores the exact prior manifest and returns content-free diagnostic evidence.
"""
import hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
from typing import Any,Mapping,Sequence
from self_change_isolation import _manifest,_eligible
CONTRACT_VERSION='v1388.8';TX=re.compile(r'^selftx_[a-f0-9]{12,64}$');SCRIPT=re.compile(r'^(?:health|canary)/[A-Za-z0-9_.-]+\.py$')
DENIED={'release_authorized':False,'promotion_authorized':False,'independent_authority_granted':False,'unreviewed_source_mutation_authorized':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _under(c:Path,p:Path)->bool:
 try:c.relative_to(p);return True
 except ValueError:return False
def _copy_tree(src:Path,dst:Path):
 dst.mkdir(parents=True,exist_ok=True)
 for p,rel in _eligible(src):
  q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def _wipe_tree(root:Path):
 for p in root.rglob('*'):
  if p.is_file():
   try:p.chmod(0o600)
   except OSError:pass
 for child in list(root.iterdir()):
  if child.is_dir():shutil.rmtree(child)
  else:child.unlink(missing_ok=True)
def _sealed_canary(c:Mapping[str,Any],expected:str)->bool:
 row=dict(c or {});sup=str(row.pop('canary_digest',''));return bool(sup==expected and sup==_d(row) and c.get('canary_passed') and c.get('eligible_for_install_review'))
def execute_self_update_with_auto_rollback(*,installed_root:str|Path,candidate_work_root:str|Path,runtime_root:str|Path,transaction_id:str,canary_self_update:Mapping[str,Any],expected_canary_digest:str,health_scenarios:Sequence[str],operator_authorized:bool,python_executable:str|None=None,timeout_seconds:int=20)->dict[str,Any]:
 installed=Path(installed_root).expanduser().resolve();candidate=Path(candidate_work_root).expanduser().resolve();runtime=Path(runtime_root).expanduser().resolve();active=Path(__file__).resolve().parents[1]
 if not TX.fullmatch(str(transaction_id or '')) or not operator_authorized or not installed.is_dir() or not candidate.is_dir() or installed.is_symlink() or candidate.is_symlink():return {'ok':False,'status':'self_update_transaction_not_authorized','action_executed':False,**DENIED}
 if installed==active or _under(installed,active) or _under(active,installed) or _under(runtime,installed) or _under(runtime,active):return {'ok':False,'status':'self_update_live_source_or_runtime_boundary_blocked','action_executed':False,**DENIED}
 if not _sealed_canary(canary_self_update,expected_canary_digest):return {'ok':False,'status':'self_update_canary_evidence_invalid','action_executed':False,**DENIED}
 if not health_scenarios or len(health_scenarios)>16 or not 1<=int(timeout_seconds)<=120:return {'ok':False,'status':'self_update_health_plan_invalid','action_executed':False,**DENIED}
 for rel in health_scenarios:
  x=str(rel or '').replace('\\','/')
  if not SCRIPT.fullmatch(x) or '..' in Path(x).parts:return {'ok':False,'status':'self_update_health_path_invalid','action_executed':False,**DENIED}
 txroot=runtime/'self_update_transactions'/transaction_id
 if txroot.exists():return {'ok':False,'status':'self_update_transaction_already_exists','action_executed':False,**DENIED}
 backup=txroot/'previous';stage=txroot/'candidate';txroot.mkdir(parents=True)
 before=_manifest(installed);candidate_manifest=_manifest(candidate)
 _copy_tree(installed,backup);_copy_tree(candidate,stage)
 if _manifest(backup)['manifest_digest']!=before['manifest_digest'] or _manifest(stage)['manifest_digest']!=candidate_manifest['manifest_digest']:
  shutil.rmtree(txroot,ignore_errors=True);return {'ok':False,'status':'self_update_staging_verification_failed','action_executed':False,**DENIED}
 replaced=False;rows=[];rollback=False;rollback_verified=False;py=python_executable or sys.executable
 try:
  _wipe_tree(installed);_copy_tree(stage,installed);replaced=True
  if _manifest(installed)['manifest_digest']!=candidate_manifest['manifest_digest']:raise RuntimeError('installed candidate manifest mismatch')
  for rel in health_scenarios:
   st=time.monotonic();p=(installed/rel).resolve()
   try:p.relative_to(installed)
   except ValueError:raise RuntimeError('health path escaped')
   if not p.is_file():raise RuntimeError('health scenario missing')
   try:
    cp=subprocess.run([py,rel],cwd=installed,capture_output=True,timeout=timeout_seconds,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});blob=(cp.stdout or b'')+(cp.stderr or b'')
    rows.append({'scenario_path':rel,'passed':cp.returncode==0,'exit_code':cp.returncode,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'duration_ms':int((time.monotonic()-st)*1000)})
   except subprocess.TimeoutExpired as e:
    blob=(e.stdout or b'')+(e.stderr or b'');rows.append({'scenario_path':rel,'passed':False,'timed_out':True,'exit_code':None,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'duration_ms':int((time.monotonic()-st)*1000)})
   if not rows[-1]['passed']:raise RuntimeError('post-install health failed')
  final=_manifest(installed)
  core={'contract_version':CONTRACT_VERSION,'transaction_id':transaction_id,'canary_digest':expected_canary_digest,'previous_manifest_digest':before['manifest_digest'],'candidate_manifest_digest':candidate_manifest['manifest_digest'],'active_manifest_digest':final['manifest_digest'],'health':rows,'health_passed':True,'rollback_performed':False,'rollback_verified':False,'operator_authorized':True,'diagnostic_evidence_retained':True,'external_installed_tree_only':True,'action_executed':True,**DENIED};core['transaction_digest']=_d(core)
  return {'ok':True,'status':'self_update_installed_health_passed','self_update_transaction':core,'action_executed':True,**DENIED}
 except Exception as exc:
  if replaced:
   try:
    _wipe_tree(installed);_copy_tree(backup,installed);rollback=True;rollback_verified=_manifest(installed)['manifest_digest']==before['manifest_digest']
   except Exception:rollback=True;rollback_verified=False
  core={'contract_version':CONTRACT_VERSION,'transaction_id':transaction_id,'canary_digest':expected_canary_digest,'previous_manifest_digest':before['manifest_digest'],'candidate_manifest_digest':candidate_manifest['manifest_digest'],'active_manifest_digest':_manifest(installed)['manifest_digest'] if installed.is_dir() else '','health':rows,'health_passed':False,'rollback_performed':rollback,'rollback_verified':rollback_verified,'failure_digest':_d(str(exc)[:160]),'operator_authorized':True,'diagnostic_evidence_retained':True,'external_installed_tree_only':True,'action_executed':True,**DENIED};core['transaction_digest']=_d(core)
  return {'ok':False,'status':'self_update_failed_rolled_back' if rollback_verified else 'self_update_failed_rollback_unverified','self_update_transaction':core,'action_executed':True,**DENIED}
def process_automatic_self_rollback_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show self update transaction','inspect self rollback','show automatic self rollback'}:return {'active':False}
 rec=dict((project_state or {}).get('self_update_transaction') or {});return {'active':True,'ok':bool(rec),'status':'self_update_transaction_found' if rec else 'self_update_transaction_missing','self_update_transaction':rec,'action_executed':False,**DENIED}
