from __future__ import annotations
"""Content-free continuity for structured action clarification.

Stores only bounded identifiers, digests, field names, lifecycle state, and time.
It never stores request/answer text, arguments, conversation content, approval, or
execution authority.
"""
import hashlib, json, os, time
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION='1'
CONTRACT_VERSION='v1176.8'
MAX_PENDING=32
MAX_FIELDS=4
MAX_AGE_SECONDS=86400
TERMINAL={'consumed','cancelled','expired','superseded'}


def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()

def _clean_digest(v:Any)->str:
    s=str(v or '')
    return s if len(s)==64 and all(c in '0123456789abcdef' for c in s) else ''

def _default()->dict[str,Any]:
    return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'revision':0,'records':[]}

def _load(path:Path)->dict[str,Any]:
    try:
        raw=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw,dict) or not isinstance(raw.get('records'),list): return _default()
        return raw
    except Exception: return _default()

def _save(path:Path,state:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(state,sort_keys=True,separators=(',',':')),encoding='utf-8')
    os.replace(tmp,path)

def register_clarification(path:Path|str, request:Mapping[str,Any], *, now:float|None=None)->dict[str,Any]:
    now=float(time.time() if now is None else now); p=Path(path); state=_load(p)
    rd=_clean_digest(request.get('request_digest')); pd=_clean_digest(request.get('source_projection_digest')); bd=_clean_digest(request.get('source_binding_digest'))
    cap=str(request.get('capability_id') or '')[:80]
    fields=[str(x)[:80] for x in list(request.get('requested_fields') or [])[:MAX_FIELDS]]
    eligible=bool(request.get('state')=='awaiting_structured_answer' and rd and pd and bd and cap and fields)
    duplicate=next((r for r in state['records'] if r.get('request_digest')==rd and r.get('state')=='pending'),None)
    if not eligible:
        return {'ok':False,'state':'rejected','reason':'invalid_bounded_request','persisted':False,'authority_granted':False,'execution_performed':False}
    if duplicate:
        return {'ok':True,'state':'duplicate_pending','continuity_id':duplicate['continuity_id'],'request_digest':rd,'persisted':False,'authority_granted':False,'execution_performed':False}
    for r in state['records']:
        if r.get('capability_id')==cap and r.get('source_projection_digest')==pd and r.get('state')=='pending': r['state']='superseded'; r['terminal_at']=now
    record={'continuity_id':_digest({'request_digest':rd,'created_at':now})[:32],'request_digest':rd,'source_projection_digest':pd,'source_binding_digest':bd,'capability_id':cap,'requested_fields':fields,'state':'pending','created_at':now,'updated_at':now,'expires_at':now+MAX_AGE_SECONDS,'answer_stored':False,'raw_content_stored':False,'authority_granted':False,'approval_created':False,'execution_performed':False}
    state['records'].append(record); state['records']=state['records'][-MAX_PENDING:]; state['revision']=int(state.get('revision',0))+1; _save(p,state)
    return {'ok':True,'state':'pending','continuity_id':record['continuity_id'],'request_digest':rd,'persisted':True,'authority_granted':False,'execution_performed':False}

def resume_clarification(path:Path|str, *, request_digest:str, source_projection_digest:str, source_binding_digest:str, now:float|None=None)->dict[str,Any]:
    now=float(time.time() if now is None else now); p=Path(path); state=_load(p)
    rd=_clean_digest(request_digest); pd=_clean_digest(source_projection_digest); bd=_clean_digest(source_binding_digest)
    matches=[r for r in state['records'] if r.get('request_digest')==rd]
    r=matches[-1] if matches else None
    if not r: return {'ok':False,'state':'missing','resumable':False,'authority_granted':False,'execution_performed':False}
    if r.get('state')=='pending' and now>float(r.get('expires_at',0)): r['state']='expired'; r['terminal_at']=now; state['revision']=int(state.get('revision',0))+1; _save(p,state)
    exact=bool(r.get('source_projection_digest')==pd and r.get('source_binding_digest')==bd)
    resumable=bool(exact and r.get('state')=='pending')
    return {'ok':resumable,'state':r.get('state'),'resumable':resumable,'continuity_id':r.get('continuity_id',''),'capability_id':r.get('capability_id','') if exact else '', 'requested_fields':list(r.get('requested_fields') or []) if exact else [],'request_digest':rd if exact else '','exact_digest_binding':exact,'answer_stored':False,'raw_content_stored':False,'authority_granted':False,'approval_created':False,'execution_performed':False}

def transition_clarification(path:Path|str, *, request_digest:str, transition:str, now:float|None=None)->dict[str,Any]:
    now=float(time.time() if now is None else now); p=Path(path); state=_load(p); rd=_clean_digest(request_digest)
    if transition not in {'consumed','cancelled'}: return {'ok':False,'state':'rejected','reason':'unsupported_transition','authority_granted':False,'execution_performed':False}
    r=next((x for x in reversed(state['records']) if x.get('request_digest')==rd),None)
    if not r: return {'ok':False,'state':'missing','authority_granted':False,'execution_performed':False}
    if r.get('state') in TERMINAL: return {'ok':False,'state':r.get('state'),'duplicate_terminal_transition':True,'authority_granted':False,'execution_performed':False}
    r['state']=transition; r['terminal_at']=now; r['updated_at']=now; state['revision']=int(state.get('revision',0))+1; _save(p,state)
    return {'ok':True,'state':transition,'continuity_id':r.get('continuity_id',''),'request_digest':rd,'authority_granted':False,'approval_created':False,'execution_performed':False}

def inspect_clarification_continuity(path:Path|str, *, now:float|None=None)->dict[str,Any]:
    now=float(time.time() if now is None else now); state=_load(Path(path)); counts={}
    for r in state['records']:
        s=str(r.get('state') or 'unknown'); counts[s]=counts.get(s,0)+1
    out={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'revision':int(state.get('revision',0)),'record_count':len(state['records']),'state_counts':counts,'pending_count':counts.get('pending',0),'expired_due_count':sum(1 for r in state['records'] if r.get('state')=='pending' and now>float(r.get('expires_at',0))),'raw_content_exposed':False,'answers_exposed':False,'authority_granted':False,'approval_created':False,'execution_performed':False}
    out['inspection_digest']=_digest(out); return out
