from __future__ import annotations
"""Structured verification evidence helpers for v1489 Bundle 18."""
from pathlib import Path
from typing import Any,Iterable,Mapping
import hashlib,json,tempfile,zipfile,shutil,time

FAILURE_CLASSES=frozenset({'product_defect','stale_fixture','wrapper_timeout','provider_unavailable','environmental_cleanup','optional_certification'})

def classify_verification_failure(*,return_code:int,assertions_failed:int=0,timed_out:bool=False,provider_available:bool=True,baseline_same:bool=False,cleanup_dirty:bool=False,certification_only:bool=False)->str:
    if certification_only:return 'optional_certification'
    if not provider_available:return 'provider_unavailable'
    if cleanup_dirty:return 'environmental_cleanup'
    if timed_out:return 'wrapper_timeout'
    if baseline_same and return_code:return 'stale_fixture'
    return 'product_defect' if return_code or assertions_failed else 'pass'

def synthetic_record(*,record_id:str,provenance:str='user',state:str='active')->dict[str,Any]:
    return {'record_id':str(record_id),'provenance':str(provenance),'state':str(state),'content_digest':hashlib.sha256(str(record_id).encode()).hexdigest(),'synthetic':True}

def verification_receipt(*,suite:str,passed:int,failed:int,duration_ms:int,authority_unchanged:bool=True)->dict[str,Any]:
    row={'suite':str(suite),'passed':max(0,int(passed)),'failed':max(0,int(failed)),'duration_ms':max(0,int(duration_ms)),'authority_unchanged':bool(authority_unchanged),'content_free':True}
    row['receipt_digest']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest();return row

def parity_receipt(streaming:Mapping[str,Any],nonstreaming:Mapping[str,Any],keys:Iterable[str])->dict[str,Any]:
    ks=[str(k) for k in keys]; mismatches=[k for k in ks if streaming.get(k)!=nonstreaming.get(k)]
    return {'parity':not mismatches,'compared_key_count':len(ks),'mismatch_count':len(mismatches),'content_free':True}

def source_snapshot(root:Path|str)->dict[str,str]:
    r=Path(root).resolve();out={}
    for p in sorted(r.rglob('*')):
        if p.is_file() and not any(x in p.parts for x in ('data','__pycache__','.git','.venv')) and p.suffix not in {'.pyc','.pyo'}:
            out[p.relative_to(r).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def immutable(before:Mapping[str,str],after:Mapping[str,str])->bool:return dict(before)==dict(after)

def soak_profile(name:str)->dict[str,Any]:
    profiles={'short':{'turns':25,'restarts':1,'reconnects':2},'long':{'turns':200,'restarts':5,'reconnects':20},'restart':{'turns':40,'restarts':10,'reconnects':5}}
    row=dict(profiles.get(str(name),profiles['short']));row.update({'profile':str(name) if str(name) in profiles else 'short','content_free':True});return row

def human_verification_summary(receipts:Iterable[Mapping[str,Any]])->str:
    rows=list(receipts);passed=sum(int(r.get('passed') or 0) for r in rows);failed=sum(int(r.get('failed') or 0) for r in rows);return f"{len(rows)} suites recorded; {passed} checks passed; {failed} checks failed. Authority unchanged unless explicitly reported otherwise."
