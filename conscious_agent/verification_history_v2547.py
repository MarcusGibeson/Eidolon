from __future__ import annotations
"""v2547 bounded verification outcome history.

Stores content-minimized per-test observations derived from tiered verification
receipts. History is advisory evidence only and never weakens required tests.
"""
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

CONTRACT_VERSION='v2547.0'
MAX_HISTORY_PER_TEST=64
AUTHORITY={'source_mutation_authorized':False,'project_mutation_authorized':False,'approval_granted':False,'release_authorized':False,'certification_authorized':False,'required_test_waiver_authorized':False,'independent_authority_granted':False}

def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()

def _safe_test_id(value:Any)->str:
    token=str(value or '').replace('\\','/').strip()
    if not token or token.startswith('/') or '..' in token.split('/') or len(token)>240:
        raise ValueError('safe_test_id_required')
    return token

def observations_from_tiered_receipt(receipt:Mapping[str,Any], *, observed_at:str='')->list[dict[str,Any]]:
    if not str(receipt.get('status') or '').startswith('tiered_verification_'):
        raise ValueError('tiered_receipt_required')
    out=[]
    parent=str(receipt.get('receipt_digest') or '')
    for tier_row in list(receipt.get('receipts') or [])[:3]:
        if not isinstance(tier_row,Mapping): continue
        tier=int(tier_row.get('tier',-1))
        for row in list(tier_row.get('tests') or [])[:16]:
            if not isinstance(row,Mapping): continue
            test=_safe_test_id(row.get('test'))
            status=str(row.get('status') or '')[:48]
            rec={'contract_version':CONTRACT_VERSION,'test':test,'tier':tier,'ok':bool(row.get('ok')),
                 'status':status,'timed_out':bool(row.get('timed_out')),'observed_at':str(observed_at or '')[:48],
                 'parent_receipt_digest':parent if len(parent)==64 else '', 'raw_output_stored':False, **AUTHORITY}
            try: rec['elapsed_seconds']=round(max(0.0,float(row.get('elapsed_seconds') or 0.0)),3)
            except Exception: rec['elapsed_seconds']=0.0
            rec['observation_digest']=_digest(rec); out.append(rec)
    return out

def append_observations(history_path:str|Path, observations:list[Mapping[str,Any]])->dict[str,Any]:
    path=Path(history_path)
    if path.exists() and path.is_symlink(): raise ValueError('symlink_history_rejected')
    path.parent.mkdir(parents=True,exist_ok=True)
    existing=load_history(path)
    for row in observations:
        if str(row.get('contract_version') or '')!=CONTRACT_VERSION: raise ValueError('observation_contract_required')
        test=_safe_test_id(row.get('test'))
        compact={k:row.get(k) for k in ('contract_version','test','tier','ok','status','timed_out','observed_at','parent_receipt_digest','elapsed_seconds','raw_output_stored','observation_digest')}
        existing.setdefault(test,[]).append(compact)
        existing[test]=existing[test][-MAX_HISTORY_PER_TEST:]
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(existing,sort_keys=True,separators=(',',':'),ensure_ascii=True),encoding='utf-8')
    tmp.replace(path)
    return {'ok':True,'contract_version':CONTRACT_VERSION,'test_count':len(existing),'observation_count':sum(len(v) for v in existing.values()),'history_digest':_digest(existing),**AUTHORITY}

def load_history(history_path:str|Path)->dict[str,list[dict[str,Any]]]:
    path=Path(history_path)
    if not path.exists(): return {}
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict): raise ValueError('history_object_required')
    out={}
    for key,rows in data.items():
        test=_safe_test_id(key)
        if not isinstance(rows,list): continue
        out[test]=[dict(r) for r in rows[-MAX_HISTORY_PER_TEST:] if isinstance(r,dict)]
    return out

__all__=['CONTRACT_VERSION','MAX_HISTORY_PER_TEST','observations_from_tiered_receipt','append_observations','load_history']
