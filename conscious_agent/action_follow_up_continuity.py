from __future__ import annotations
"""Content-free governed action follow-up continuity across restart.

Persists only bounded proposal identity, lifecycle state, digests, and the next
operator-facing governed step. It never discovers private ledgers, stores raw
content, retries work, or grants approval, authorization, or execution.
"""
import hashlib, json, os, time
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION='1'
CONTRACT_VERSION='v1179.5'
MAX_RECORDS=32
MAX_AGE_SECONDS=7*86400
TERMINAL={'closed','cancelled','expired','superseded'}
ALLOWED_STATES={'proposed','awaiting_approval','approved','rejected','cancelled','expired','superseded','execution_admitted','execution_in_progress','execution_succeeded','execution_failed','execution_cancelled','execution_timed_out'}

def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def _hex(v:Any)->str:
    s=str(v or '').lower(); return s if len(s)==64 and all(c in '0123456789abcdef' for c in s) else ''
def _id(v:Any)->str:
    s=str(v or '').strip().lower(); return s if 0<len(s)<=80 and all(c.isalnum() or c in '_-' for c in s) else ''
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'revision':0,'records':[]}
def _load(p:Path):
    try:
        d=json.loads(p.read_text(encoding='utf-8'))
        return d if isinstance(d,dict) and isinstance(d.get('records'),list) else _default()
    except Exception: return _default()
def _save(p:Path,d:dict):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(d,sort_keys=True,separators=(',',':')),encoding='utf-8'); os.replace(t,p)

def register_action_follow_up(path:Path|str, review:Mapping[str,Any], *, now:float|None=None)->dict[str,Any]:
    now=float(time.time() if now is None else now); selected=review.get('selected_status') if isinstance(review.get('selected_status'),Mapping) else {}
    pid=_id(selected.get('proposal_id')); cap=_id(selected.get('capability_id')); state=str(selected.get('state') or '')
    pd=_hex(selected.get('proposal_digest')); rd=_hex(review.get('review_digest')); next_step=str((review.get('follow_through') or {}).get('next_governed_step') or '')[:120]
    eligible=bool(review.get('exact_status_reference') is True and pid and cap and state in ALLOWED_STATES and pd and rd and next_step)
    if not eligible: return {'ok':False,'state':'rejected','reason':'invalid_exact_status_review','persisted':False,'authority_granted':False,'execution_invoked':False}
    p=Path(path); data=_load(p)
    existing=next((r for r in reversed(data['records']) if r.get('proposal_id')==pid and r.get('review_digest')==rd and r.get('state')=='pending'),None)
    if existing: return {'ok':True,'state':'duplicate_pending','continuity_id':existing['continuity_id'],'persisted':False,'authority_granted':False,'execution_invoked':False}
    for r in data['records']:
        if r.get('proposal_id')==pid and r.get('state')=='pending': r['state']='superseded'; r['terminal_at']=now
    rec={'continuity_id':_digest({'proposal_id':pid,'review_digest':rd,'created_at':now})[:32],'proposal_id':pid,'capability_id':cap,'lifecycle_state':state,'proposal_digest':pd,'review_digest':rd,'next_governed_step':next_step,'state':'pending','created_at':now,'updated_at':now,'expires_at':now+MAX_AGE_SECONDS,'raw_content_stored':False,'authority_granted':False,'execution_invoked':False}
    data['records'].append(rec); data['records']=data['records'][-MAX_RECORDS:]; data['revision']=int(data.get('revision',0))+1; _save(p,data)
    return {'ok':True,'state':'pending','continuity_id':rec['continuity_id'],'proposal_id':pid,'persisted':True,'authority_granted':False,'execution_invoked':False}

def resume_action_follow_up(path:Path|str, *, proposal_id:str, review_digest:str, proposal_digest:str, now:float|None=None)->dict[str,Any]:
    now=float(time.time() if now is None else now); p=Path(path); data=_load(p); pid=_id(proposal_id); rd=_hex(review_digest); pd=_hex(proposal_digest)
    r=next((x for x in reversed(data['records']) if x.get('proposal_id')==pid),None)
    if not r: return {'ok':False,'state':'missing','resumable':False,'authority_granted':False,'execution_invoked':False}
    if r.get('state')=='pending' and now>float(r.get('expires_at',0)): r['state']='expired'; r['terminal_at']=now; data['revision']=int(data.get('revision',0))+1; _save(p,data)
    exact=bool(r.get('review_digest')==rd and r.get('proposal_digest')==pd)
    resumable=bool(exact and r.get('state')=='pending')
    return {'ok':resumable,'state':r.get('state'),'resumable':resumable,'continuity_id':r.get('continuity_id',''),'proposal_id':pid if exact else '','capability_id':r.get('capability_id','') if exact else '','lifecycle_state':r.get('lifecycle_state','') if exact else '','next_governed_step':r.get('next_governed_step','') if exact else '','exact_digest_binding':exact,'raw_content_stored':False,'authority_granted':False,'execution_invoked':False}

def transition_action_follow_up(path:Path|str, *, proposal_id:str, transition:str, now:float|None=None)->dict[str,Any]:
    now=float(time.time() if now is None else now); p=Path(path); data=_load(p); pid=_id(proposal_id)
    if transition not in {'closed','cancelled'}: return {'ok':False,'state':'rejected','reason':'unsupported_transition','authority_granted':False,'execution_invoked':False}
    r=next((x for x in reversed(data['records']) if x.get('proposal_id')==pid),None)
    if not r: return {'ok':False,'state':'missing','authority_granted':False,'execution_invoked':False}
    if r.get('state') in TERMINAL: return {'ok':False,'state':r.get('state'),'duplicate_terminal_transition':True,'authority_granted':False,'execution_invoked':False}
    r['state']=transition; r['terminal_at']=now; r['updated_at']=now; data['revision']=int(data.get('revision',0))+1; _save(p,data)
    return {'ok':True,'state':transition,'continuity_id':r.get('continuity_id',''),'proposal_id':pid,'authority_granted':False,'execution_invoked':False}

def inspect_action_follow_up_continuity(path:Path|str, *, now:float|None=None)->dict[str,Any]:
    now=float(time.time() if now is None else now); data=_load(Path(path)); counts={}
    for r in data['records']: counts[r.get('state','unknown')]=counts.get(r.get('state','unknown'),0)+1
    out={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'revision':int(data.get('revision',0)),'record_count':len(data['records']),'state_counts':counts,'pending_count':counts.get('pending',0),'expired_due_count':sum(1 for r in data['records'] if r.get('state')=='pending' and now>float(r.get('expires_at',0))),'raw_content_exposed':False,'ledger_discovered':False,'authority_granted':False,'execution_invoked':False}
    out['inspection_digest']=_digest(out); return out
