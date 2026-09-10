from __future__ import annotations
"""v1376 private partial-artifact retention with explicit verification state."""
import hashlib,json,re
from pathlib import Path
from typing import Any,Sequence
CONTRACT_VERSION="v1376.8"
DENIED={"project_mutation_authorized":False,"source_mutation_authorized":False,"application_authorized":False,"release_authorized":False,"independent_authority_granted":False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _b(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def _root(runtime_root=None)->Path:
 p=Path(runtime_root or 'data')/'partial_results';p.mkdir(parents=True,exist_ok=True);return p
def _dir(c,a,runtime_root=None):return _root(runtime_root)/c/a
def retain_partial_result(*,campaign_record_digest:str,task_id_digest:str,artifact_id:str,artifact_kind:str,artifact_bytes:bytes,remaining_check_codes:Sequence[str],retention_authorized:bool,producer_evidence_digest:str,max_bytes:int=4*1024*1024,runtime_root=None)->dict[str,Any]:
 if not retention_authorized:return {'ok':False,'status':'retention_authority_required','action_executed':False,**DENIED}
 if not re.fullmatch(r'[a-f0-9]{64}',str(campaign_record_digest or '')) or not re.fullmatch(r'[a-f0-9]{64}',str(task_id_digest or '')) or not re.fullmatch(r'[a-f0-9]{64}',str(producer_evidence_digest or '')):return {'ok':False,'status':'partial_result_lineage_invalid','action_executed':False,**DENIED}
 if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',str(artifact_id or '')) or artifact_kind not in {'patch','report','test-output','build-artifact','generated-file','other'}:return {'ok':False,'status':'partial_result_identity_invalid','action_executed':False,**DENIED}
 if not isinstance(artifact_bytes,(bytes,bytearray)) or len(artifact_bytes)>max_bytes:return {'ok':False,'status':'partial_result_size_invalid','action_executed':False,**DENIED}
 checks=[str(x) for x in remaining_check_codes]
 if not checks or len(checks)>64 or any(not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',x) for x in checks):return {'ok':False,'status':'partial_result_remaining_checks_required','action_executed':False,**DENIED}
 aid=_d(artifact_id);d=_dir(campaign_record_digest,aid,runtime_root);desc=d/'record.json';blob=d/'artifact.bin';digest=_b(bytes(artifact_bytes))
 row={'contract_version':CONTRACT_VERSION,'campaign_record_digest':campaign_record_digest,'task_id_digest':task_id_digest,'artifact_id_digest':aid,'artifact_kind':artifact_kind,'artifact_sha256':digest,'artifact_byte_count':len(artifact_bytes),'producer_evidence_digest':producer_evidence_digest,'verification_status':'partial_unverified','remaining_check_digests':[_d(x) for x in checks],'remaining_check_count':len(checks),'usable_as_verified_evidence':False,'content_free':True,'raw_artifact_public':False}
 row['record_digest']=_d(row)
 if desc.exists():
  prior=json.loads(desc.read_text())
  if prior==row and blob.exists() and _b(blob.read_bytes())==digest:return {'ok':True,'status':'partial_result_duplicate','partial_result':row,'action_executed':False,**DENIED}
  return {'ok':False,'status':'partial_result_conflict','action_executed':False,**DENIED}
 d.mkdir(parents=True,exist_ok=True);tmp=blob.with_suffix('.tmp');tmp.write_bytes(bytes(artifact_bytes));tmp.replace(blob);td=desc.with_suffix('.tmp');td.write_text(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');td.replace(desc)
 return {'ok':True,'status':'partial_result_retained','partial_result':row,'action_executed':False,**DENIED}
def load_partial_result(*,campaign_record_digest:str,artifact_id:str,expected_record_digest:str,runtime_root=None,include_private_artifact:bool=False)->dict[str,Any]:
 aid=_d(artifact_id);d=_dir(campaign_record_digest,aid,runtime_root);desc=d/'record.json';blob=d/'artifact.bin'
 if not desc.exists() or not blob.exists():return {'ok':False,'status':'partial_result_missing','action_executed':False,**DENIED}
 try:row=json.loads(desc.read_text())
 except Exception:return {'ok':False,'status':'partial_result_invalid','action_executed':False,**DENIED}
 rd=row.get('record_digest');base=dict(row);base.pop('record_digest',None)
 if rd!=_d(base) or rd!=expected_record_digest or _b(blob.read_bytes())!=row.get('artifact_sha256'):return {'ok':False,'status':'partial_result_tampered_or_stale','action_executed':False,**DENIED}
 out={'ok':True,'status':'partial_result_loaded','partial_result':row,'action_executed':False,**DENIED}
 if include_private_artifact:out['private_artifact_bytes']=blob.read_bytes()
 return out
def process_partial_result_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show partial results','inspect partial results','show retained work'}:return {'active':False}
 rec=dict((project_state or {}).get('partial_result') or {})
 return {'active':True,'ok':bool(rec),'status':'partial_result_found' if rec else 'partial_result_missing','partial_result':rec,'action_executed':False,**DENIED}
