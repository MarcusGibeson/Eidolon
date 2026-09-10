from __future__ import annotations
"""v1385 bounded self-dogfood verification inside an isolated candidate tree."""
import hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
from typing import Any,Mapping,Sequence
from self_change_isolation import verify_self_change_isolation
CONTRACT_VERSION='v1385.8';TEST=re.compile(r'^tools/[A-Za-z0-9_.-]+_tests?\.py$|^tools/[A-Za-z0-9_.-]+test[A-Za-z0-9_.-]*\.py$');DIGEST=re.compile(r'^[a-f0-9]{64}$')
DENIED={'source_mutation_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def run_dogfood_verification(*,private_workspace:Mapping[str,Any],expected_lineage_digest:str,protected_scope:Mapping[str,Any],expected_scope_digest:str,test_paths:Sequence[str],python_executable:str|None=None,timeout_seconds:int=30)->dict[str,Any]:
 iso=verify_self_change_isolation(private_workspace=private_workspace,expected_lineage_digest=expected_lineage_digest)
 if not iso.get('ok'):return {'ok':False,'status':'dogfood_isolation_invalid','action_executed':False,**DENIED}
 scope=dict(protected_scope or {});sup=str(scope.pop('scope_digest',''))
 # Scope is already sealed by v1384; bind to its exact supplied digest without granting review/apply authority.
 from protected_core import _d as _scope_d
 if sup!=expected_scope_digest or sup!=_scope_d(scope):return {'ok':False,'status':'dogfood_scope_invalid','action_executed':False,**DENIED}
 if not test_paths or len(test_paths)>32 or not 1<=int(timeout_seconds)<=120:return {'ok':False,'status':'dogfood_test_plan_invalid','action_executed':False,**DENIED}
 tests=[]
 for raw in test_paths:
  p=str(raw or '').replace('\\','/')
  if not TEST.fullmatch(p) or '..' in Path(p).parts:return {'ok':False,'status':'dogfood_test_path_invalid','action_executed':False,**DENIED}
  tests.append(p)
 work=Path(str(private_workspace.get('work_root') or '')).resolve();py=python_executable or sys.executable;rows=[]
 for rel in tests:
  path=(work/rel).resolve()
  try:path.relative_to(work)
  except ValueError:return {'ok':False,'status':'dogfood_test_path_escape','action_executed':False,**DENIED}
  if not path.is_file():return {'ok':False,'status':'dogfood_test_missing','action_executed':False,**DENIED}
  started=time.monotonic()
  try:
   cp=subprocess.run([py,rel],cwd=work,capture_output=True,text=False,timeout=timeout_seconds,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
   blob=(cp.stdout or b'')+(cp.stderr or b'');rows.append({'test_path':rel,'exit_code':cp.returncode,'passed':cp.returncode==0,'output_digest':hashlib.sha256(blob[:1024*1024]).hexdigest(),'output_truncated':len(blob)>1024*1024,'duration_ms':int((time.monotonic()-started)*1000)})
  except subprocess.TimeoutExpired as exc:
   blob=(exc.stdout or b'')+(exc.stderr or b'');rows.append({'test_path':rel,'exit_code':None,'passed':False,'timed_out':True,'output_digest':hashlib.sha256(blob[:1024*1024]).hexdigest(),'duration_ms':int((time.monotonic()-started)*1000)})
 passed=sum(bool(x['passed']) for x in rows);core={'contract_version':CONTRACT_VERSION,'candidate_id':iso['verification'].get('candidate_id'),'lineage_digest':expected_lineage_digest,'scope_digest':expected_scope_digest,'change_set_digest':protected_scope.get('change_set_digest'),'protected_core_touched':bool(protected_scope.get('protected_core_touched')),'test_count':len(rows),'passed':passed,'failed':len(rows)-passed,'tests':rows,'same_pipeline_required':True,'isolated_candidate_only':True,'candidate_installable':passed==len(rows),'installation_authorized':False,'release_authorized':False,'content_free':True,'action_executed':True,**DENIED};core['verification_digest']=_d(core)
 return {'ok':passed==len(rows),'status':'dogfood_verification_passed' if passed==len(rows) else 'dogfood_verification_failed','dogfood_verification':core,'action_executed':True,**DENIED}
def process_dogfood_verification_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show dogfood verification','inspect dogfood verification','show self verification'}:return {'active':False}
 rec=dict((project_state or {}).get('dogfood_verification') or {});return {'active':True,'ok':bool(rec),'status':'dogfood_verification_found' if rec else 'dogfood_verification_missing','dogfood_verification':rec,'action_executed':False,**DENIED}
