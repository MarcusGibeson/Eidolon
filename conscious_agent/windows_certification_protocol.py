from __future__ import annotations

"""v1499 Windows certification/soak evidence protocol.

The browser/source candidate may define and validate the protocol, but only
external native Windows receipts can satisfy the native gates. Even complete
receipts do not install or promote a build automatically.
"""

import hashlib, json
from typing import Any, Iterable, Mapping

from development_authority import is_hex64

CONTRACT_VERSION='v1499.9'
REQUIRED_NATIVE_CHECKS=(
 'windows_fresh_extract','desktop_launch','ordinary_chat','streaming_first_visible',
 'provider_cold_warm','provider_recovery','exactly_once_reconnect','cancellation_restart',
 'source_immutability','source_only_privacy','compile','long_soak',
)


def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def build_windows_certification_protocol(*,candidate_zip_sha256:str,source_manifest_sha256:str)->dict[str,Any]:
 if not is_hex64(candidate_zip_sha256) or not is_hex64(source_manifest_sha256):raise ValueError('windows_protocol_exact_hashes_required')
 row={'contract_version':CONTRACT_VERSION,'candidate_zip_sha256':str(candidate_zip_sha256).casefold(),'source_manifest_sha256':str(source_manifest_sha256).casefold(),'required_checks':list(REQUIRED_NATIVE_CHECKS),'native_windows_required':True,'configured_provider_must_remain_unchanged':True,'model_install_delete_switch_allowed':False,'private_runtime_must_be_external':True,'content_free':True}
 row['protocol_digest']=_digest(row);return row

def seal_windows_receipt(protocol:Mapping[str,Any],*,check:str,passed:bool,platform:str,execution_digest:str,first_visible_ms:float=0.0,total_ms:float=0.0,cold:bool=False)->dict[str,Any]:
 name=str(check or '')
 if name not in set(protocol.get('required_checks') or ()) or not is_hex64(protocol.get('protocol_digest')) or not is_hex64(execution_digest):raise ValueError('windows_receipt_binding_invalid')
 row={'contract_version':CONTRACT_VERSION,'protocol_digest':str(protocol.get('protocol_digest')),'candidate_zip_sha256':str(protocol.get('candidate_zip_sha256')),'check':name,'passed':bool(passed),'platform':str(platform or ''),'execution_digest':str(execution_digest).casefold(),'first_visible_ms':max(0.0,float(first_visible_ms)),'total_ms':max(0.0,float(total_ms)),'cold':bool(cold),'content_free':True}
 row['receipt_digest']=_digest(row);return row

def seal_soak_sample(*,iteration:int,passed:bool,duplicate_operations:int,execution_digest:str)->dict[str,Any]:
 if int(iteration)<0 or int(duplicate_operations)<0 or not is_hex64(execution_digest):raise ValueError('soak_sample_binding_invalid')
 row={'contract_version':CONTRACT_VERSION,'iteration':int(iteration),'passed':bool(passed),'duplicate_operations':int(duplicate_operations),'execution_digest':str(execution_digest).casefold(),'content_free':True}
 row['sample_digest']=_digest(row);return row

def evaluate_windows_receipts(protocol:Mapping[str,Any],receipts:Iterable[Mapping[str,Any]])->dict[str,Any]:
 rows=[dict(x or {}) for x in receipts]
 valid=[];invalid=[]
 for row in rows:
  supplied=str(row.get('receipt_digest') or '');core={k:v for k,v in row.items() if k!='receipt_digest'}
  ok=bool(is_hex64(supplied) and supplied==_digest(core) and row.get('protocol_digest')==protocol.get('protocol_digest') and row.get('candidate_zip_sha256')==protocol.get('candidate_zip_sha256') and is_hex64(row.get('execution_digest')))
  (valid if ok else invalid).append(row)
 names=[str(r.get('check') or '') for r in valid];duplicates=sorted({name for name in names if names.count(name)>1})
 by_name={str(r.get('check') or ''):r for r in valid}
 missing=[name for name in protocol.get('required_checks') or () if name not in by_name]
 failed=[name for name,row in by_name.items() if name in set(protocol.get('required_checks') or ()) and not bool(row.get('passed'))]
 native=all(str(row.get('platform') or '').casefold().startswith('win') for name,row in by_name.items() if name in set(protocol.get('required_checks') or ())) if by_name else False
 timings=[{'check':name,'first_visible_ms':float(row.get('first_visible_ms') or 0.0),'total_ms':float(row.get('total_ms') or 0.0),'cold':bool(row.get('cold'))} for name,row in by_name.items() if name in {'ordinary_chat','provider_cold_warm'}]
 complete=not missing and not failed and native and not invalid and not duplicates
 result={'contract_version':CONTRACT_VERSION,'receipt_count':len(rows),'valid_receipt_count':len(valid),'invalid_receipt_count':len(invalid),'duplicate_checks':duplicates,'missing_checks':missing,'failed_checks':failed,'native_windows_receipts':native,'evidence_complete':complete,'timing_evidence':timings,'certification_granted':False,'installation_authorized':False,'promotion_authorized':False,'operator_certification_decision_required':True,'content_free':True}
 result['certification_evidence_digest']=_digest({'protocol':protocol.get('protocol_digest'),'valid_receipts':sorted(str(r.get('receipt_digest')) for r in valid),'invalid_count':len(invalid),'duplicates':duplicates,'missing':missing,'failed':failed,'native':native,'timings':timings});return result

def soak_summary(samples:Iterable[Mapping[str,Any]])->dict[str,Any]:
 rows=[dict(x or {}) for x in samples]
 valid=[];invalid=[]
 for row in rows:
  supplied=str(row.get('sample_digest') or '');core={k:v for k,v in row.items() if k!='sample_digest'}
  ok=bool(is_hex64(supplied) and supplied==_digest(core) and is_hex64(row.get('execution_digest')) and isinstance(row.get('passed'),bool) and int(row.get('iteration',-1))>=0 and int(row.get('duplicate_operations',-1))>=0)
  (valid if ok else invalid).append(row)
 iterations=[int(r['iteration']) for r in valid];repeated=sorted({i for i in iterations if iterations.count(i)>1})
 duplicate=sum(int(r['duplicate_operations']) for r in valid);failures=sum(1 for r in valid if not r['passed'])
 passed=bool(rows) and not invalid and not repeated and failures==0 and duplicate==0
 return {'sample_count':len(rows),'valid_sample_count':len(valid),'invalid_sample_count':len(invalid),'repeated_iterations':repeated,'failure_count':failures,'duplicate_operation_count':duplicate,'soak_passed':passed,'raw_conversation_content_recorded':False,'provider_payload_recorded':False,'content_free':True,'soak_digest':_digest(sorted(str(r['sample_digest']) for r in valid))}

__all__=['CONTRACT_VERSION','REQUIRED_NATIVE_CHECKS','build_windows_certification_protocol','seal_windows_receipt','seal_soak_sample','evaluate_windows_receipts','soak_summary']
