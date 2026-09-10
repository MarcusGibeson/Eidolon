from __future__ import annotations
"""v1189.3-v1189.5 durable replay defense and long-session campaign evidence."""
import hashlib,json,os,re,tempfile
from pathlib import Path
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1189.5';SCHEMA_VERSION='1';MAX_BYTES=262144
ID_RE=re.compile(r'^[A-Za-z0-9._:-]{8,128}$');DIGEST_RE=re.compile(r'^[0-9a-f]{64}$')

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode())<=MAX_BYTES
def _safe_root(root:str|Path)->Path:
 p=Path(root).expanduser().resolve();p.mkdir(parents=True,exist_ok=True);return p

def create_long_session_evidence(*,hardening_receipt:Mapping[str,Any],session_id:str,session_index:int,started_at_ms:int,observed_at_ms:int,checkpoint_count:int,interruption_count:int,source_digest:str)->dict[str,Any]:
 h=dict(hardening_receipt);errors=[]
 hd=str(h.get('hardening_receipt_digest','')).lower()
 if not DIGEST_RE.fullmatch(hd):errors.append('invalid_hardening_digest')
 if h.get('status')!='operator_review_required':errors.append('hardening_not_reviewable')
 if not ID_RE.fullmatch(str(session_id or '')):errors.append('invalid_session_id')
 if not isinstance(session_index,int) or session_index<1:errors.append('invalid_session_index')
 if not all(isinstance(x,int) and x>=0 for x in (started_at_ms,observed_at_ms,checkpoint_count,interruption_count)):errors.append('invalid_session_metrics')
 if isinstance(started_at_ms,int) and isinstance(observed_at_ms,int) and observed_at_ms<started_at_ms:errors.append('non_monotonic_time')
 sd=str(source_digest).lower()
 if not DIGEST_RE.fullmatch(sd):errors.append('invalid_source_digest')
 if not _bounded(h):errors.append('oversized_contract')
 errors=sorted(set(errors));duration=max(0,observed_at_ms-started_at_ms) if isinstance(observed_at_ms,int) and isinstance(started_at_ms,int) else 0
 out={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'evidence_id':'adversarial-campaign-long-session:v1189.5','campaign_id':h.get('campaign_id',''),'work_item_id':h.get('work_item_id',''),'hardening_receipt_digest':hd,'session_id':session_id,'session_index':session_index,'started_at_ms':started_at_ms,'observed_at_ms':observed_at_ms,'duration_ms':duration,'checkpoint_count':checkpoint_count,'interruption_count':interruption_count,'source_digest':sd,'status':'review_required' if not errors else 'blocked','errors':errors,'error_count':len(errors),'content_free':True,'automatic_resume':False,'execution_invoked':False,'authority_granted':False}
 out['long_session_evidence_digest']=_digest(out);return out

def register_review_nonce(*,runtime_root:str|Path,campaign_id:str,review_nonce:str,operator_review_digest:str,expected_generation:int)->dict[str,Any]:
 errors=[]
 if not ID_RE.fullmatch(str(campaign_id or '')):errors.append('invalid_campaign_id')
 if not ID_RE.fullmatch(str(review_nonce or '')):errors.append('invalid_review_nonce')
 od=str(operator_review_digest).lower()
 if not DIGEST_RE.fullmatch(od):errors.append('invalid_operator_review_digest')
 if not isinstance(expected_generation,int) or expected_generation<0:errors.append('invalid_expected_generation')
 if errors:return {'contract_version':CONTRACT_VERSION,'status':'blocked','errors':sorted(set(errors)),'content_free':True,'authority_granted':False}
 root=_safe_root(runtime_root);safe=campaign_id.replace(':','_');path=root/f'{safe}.review_nonces.json';lock=root/f'{safe}.review_nonces.lock'
 try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 except FileExistsError:return {'contract_version':CONTRACT_VERSION,'status':'blocked','errors':['writer_lock_conflict'],'content_free':True,'authority_granted':False}
 try:
  os.close(fd);record={'generation':0,'nonces':[]}
  if path.exists():
   try:record=json.loads(path.read_text())
   except Exception:return {'contract_version':CONTRACT_VERSION,'status':'blocked','errors':['malformed_nonce_ledger'],'content_free':True,'authority_granted':False}
  if record.get('generation')!=expected_generation:return {'contract_version':CONTRACT_VERSION,'status':'blocked','errors':['stale_nonce_generation'],'content_free':True,'authority_granted':False}
  nonces=list(record.get('nonces',[]))
  if review_nonce in nonces:return {'contract_version':CONTRACT_VERSION,'status':'blocked','errors':['replayed_review_nonce'],'content_free':True,'authority_granted':False,'generation':expected_generation}
  nonces.append(review_nonce);new={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'campaign_id':campaign_id,'generation':expected_generation+1,'nonces':nonces,'operator_review_digest':od,'content_free':True}
  new['nonce_ledger_digest']=_digest(new)
  with tempfile.NamedTemporaryFile('w',dir=root,delete=False,encoding='utf-8') as f:json.dump(new,f,sort_keys=True,separators=(',',':'));tmp=f.name
  os.replace(tmp,path)
  return {'contract_version':CONTRACT_VERSION,'status':'registered','generation':new['generation'],'nonce_ledger_digest':new['nonce_ledger_digest'],'review_nonce':review_nonce,'content_free':True,'authority_granted':False,'automatic_resume':False,'execution_invoked':False}
 finally:
  try:lock.unlink()
  except OSError:pass

def public_summary(row:Mapping[str,Any])->dict[str,Any]:
 return {'contract_version':CONTRACT_VERSION,'status':row.get('status',''),'campaign_id':row.get('campaign_id',''),'session_index':row.get('session_index',0),'duration_ms':row.get('duration_ms',0),'error_count':row.get('error_count',0),'content_free':True,'authority_granted':False}
