from __future__ import annotations
import os,sys,tempfile,shutil,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b17-'));BASE=R/'root';BASE.mkdir();(BASE/'safe.txt').write_text('safe')
os.environ['EIDOLON_DATA_DIR']=str(R/'runtime');os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path.insert(0,str(AGENT))
from security_privacy_authority_contract import *
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 tm=threat_model();ck('0161 integrated threat surfaces',set(tm['surfaces'])==set(THREAT_SURFACES) and not tm['independent_authority_granted'],tm)
 private={'status':'failed','prompt':'PRIVATE PROMPT','memory':'PRIVATE MEMORY','provider_payload':'PRIVATE BODY','count':2};pub=public_diagnostic_projection(private);ck('0162 prompt/memory/provider content excluded',all(x not in str(pub) for x in ('PRIVATE PROMPT','PRIVATE MEMORY','PRIVATE BODY')),pub)
 ck('0163 secret detector catches common secret','api_key = hunter2' and contains_secret('api_key = hunter2'))
 err=safe_public_error(RuntimeError('password=private path=/home/private'));ck('0163 public error does not echo secret/path','private' not in str(err).lower() and not err['raw_error_exposed'],err)
 ck('0164 safe path accepted',resolve_within_root(BASE,'safe.txt')==BASE/'safe.txt')
 try:resolve_within_root(BASE,'../escape.txt');escaped=False
 except ValueError:escaped=True
 ck('0164 traversal rejected',escaped)
 # Symlink/junction analogue on POSIX where supported.
 outside=R/'outside';outside.mkdir(); link=BASE/'link'
 try:
  link.symlink_to(outside,target_is_directory=True); 
  try:resolve_within_root(BASE,'link/secret.txt');symlink_rejected=False
  except ValueError:symlink_rejected=True
 except OSError:symlink_rejected=True
 ck('0164 symlink boundary rejected or unsupported safely',symlink_rejected)
 exp=time.time()+60;b=approval_binding(action_id='a1',arguments={'mode':'dry'},artifact_digest='abc',expires_epoch=exp);ck('0165 exact approval binding valid',approval_valid(b,action_id='a1',arguments={'mode':'dry'},artifact_digest='abc',now_epoch=time.time()),b)
 ck('0165 changed args invalidate approval',not approval_valid(b,action_id='a1',arguments={'mode':'apply'},artifact_digest='abc',now_epoch=time.time()))
 ck('0166 stale approval expires',not approval_valid(b,action_id='a1',arguments={'mode':'dry'},artifact_digest='abc',now_epoch=exp+1))
 mm=model_management_authority(operator_confirmed=False,requested_operation='switch');ck('0167 model switching operator-only',mm['operator_confirmation_required'] and not mm['authorized'] and not mm['autonomous_authority'],mm)
 for source in ('conversation','memory','provider_output','project_file'):
  g=injection_authority_guard(source_class=source,requested_capability='promote');ck('0168 injection cannot grant authority '+source,not g['authority_granted'] and not g['approval_bypassed'],g)
 matrix=denied_authority_matrix();ck('0169 denied authority remains denied',matrix and not any(matrix.values()),matrix)
finally:shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}');raise SystemExit(1 if F else 0)
